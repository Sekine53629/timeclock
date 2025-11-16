"""
Git コミット履歴インポートモジュール
Git作業時間推定データをタイムクロックシステムにインポート
"""
import json
import csv
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from storage import Storage


class GitCommitImporter:
    """Gitコミット履歴から打刻データを生成してインポート"""

    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage if storage else Storage()
        self.imported_commits = []
        self.statistics = {
            'total_imported': 0,
            'total_work_minutes': 0,
            'skipped_duplicates': 0,
            'errors': 0
        }

    def load_git_commits_csv(self, csv_file: str) -> List[Dict]:
        """
        Git作業時間推定CSVを読み込み

        Args:
            csv_file: git_work_time_estimator.pyで生成されたCSVファイル

        Returns:
            コミットデータのリスト
        """
        commits = []

        try:
            # Shift-JIS（日本語Excel用）で読み込み
            with open(csv_file, 'r', encoding='shift_jis') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # 日付と時刻をパース
                        commit_date = datetime.strptime(row['日付'], '%Y-%m-%d').date()
                        commit_time = datetime.strptime(row['時刻'], '%H:%M:%S').time()
                        commit_datetime = datetime.combine(commit_date, commit_time)

                        commit_data = {
                            'date': commit_date,
                            'time': commit_time,
                            'datetime': commit_datetime,
                            'weekday': row['曜日'],
                            'project': row['プロジェクト名'],
                            'commit_id': row['コミットID'],
                            'message': row['作業内容'],
                            'files_changed': int(row['変更ファイル数']) if row['変更ファイル数'] else 0,
                            'lines_added': int(row['追加行数']) if row['追加行数'] else 0,
                            'lines_deleted': int(row['削除行数']) if row['削除行数'] else 0,
                            'estimated_minutes': float(row['推定作業時間（分）']) if row['推定作業時間（分）'] else 0,
                            'is_overtime': row['時間外'] == '○',
                            'is_weekend': row['休日'] == '○',
                            'is_late_night': row['深夜'] == '○',
                            'author': row['作業者名']
                        }

                        commits.append(commit_data)

                    except Exception as e:
                        print(f"行の解析エラー: {e}")
                        self.statistics['errors'] += 1
                        continue

        except Exception as e:
            print(f"CSVファイル読み込みエラー: {e}")
            raise

        print(f"[OK] {len(commits)} 件のコミットデータを読み込みました")
        return commits

    def group_commits_by_session(self, commits: List[Dict], max_gap_minutes: int = 120) -> List[Dict]:
        """
        コミットを作業セッションにグループ化

        同じ日に2時間以内の間隔で行われたコミットは同じ作業セッションとみなす

        Args:
            commits: コミットデータのリスト（時系列順にソート済み）
            max_gap_minutes: セッションを分割する最大間隔（分）

        Returns:
            作業セッションのリスト
        """
        if not commits:
            return []

        sessions = []
        current_session = None

        for commit in commits:
            # 新しいセッションを開始すべきか判定
            should_start_new = (
                current_session is None or
                commit['date'] != current_session['date'] or
                (commit['datetime'] - current_session['last_commit_time']).total_seconds() > max_gap_minutes * 60
            )

            if should_start_new:
                # 前のセッションを保存
                if current_session:
                    sessions.append(current_session)

                # 新しいセッションを開始
                current_session = {
                    'date': commit['date'],
                    'project': commit['project'],
                    'start_time': commit['datetime'],
                    'last_commit_time': commit['datetime'],
                    'commits': [commit],
                    'total_minutes': commit['estimated_minutes'],
                    'is_overtime': commit['is_overtime'],
                    'is_weekend': commit['is_weekend'],
                    'is_late_night': commit['is_late_night']
                }
            else:
                # 既存のセッションに追加
                current_session['commits'].append(commit)
                current_session['last_commit_time'] = commit['datetime']
                current_session['total_minutes'] += commit['estimated_minutes']

                # セッション全体の属性を更新
                current_session['is_overtime'] = current_session['is_overtime'] or commit['is_overtime']
                current_session['is_weekend'] = current_session['is_weekend'] or commit['is_weekend']
                current_session['is_late_night'] = current_session['is_late_night'] or commit['is_late_night']

        # 最後のセッションを保存
        if current_session:
            sessions.append(current_session)

        return sessions

    def convert_session_to_timerecord(self, session: Dict, account: str) -> Dict:
        """
        作業セッションをタイムレコード形式に変換

        Args:
            session: 作業セッション
            account: 社員番号

        Returns:
            タイムレコード形式のデータ
        """
        # 終了時刻を推定（最後のコミット時刻 + 推定作業時間）
        last_commit = session['commits'][-1]
        end_time = last_commit['datetime'] + timedelta(minutes=last_commit['estimated_minutes'])

        # コミットメッセージを結合
        commit_messages = []
        for commit in session['commits']:
            msg = f"[{commit['commit_id']}] {commit['message']}"
            if len(msg) > 100:
                msg = msg[:97] + "..."
            commit_messages.append(msg)

        comment = "【Gitインポート】\n" + "\n".join(commit_messages)

        # 統計情報を追加
        total_files = sum(c['files_changed'] for c in session['commits'])
        total_lines_added = sum(c['lines_added'] for c in session['commits'])
        total_lines_deleted = sum(c['lines_deleted'] for c in session['commits'])

        comment += f"\n\n統計: {len(session['commits'])}コミット, "
        comment += f"{total_files}ファイル, +{total_lines_added}/-{total_lines_deleted}行"

        if session['is_overtime']:
            comment += " [時間外]"
        if session['is_weekend']:
            comment += " [休日]"
        if session['is_late_night']:
            comment += " [深夜]"

        record = {
            'account': account,
            'project': session['project'],
            'date': session['date'].strftime('%Y-%m-%d'),
            'start_time': session['start_time'].isoformat(),
            'breaks': [],  # Gitデータには休憩情報がない
            'end_time': end_time.isoformat(),
            'status': 'completed',
            'total_minutes': int(session['total_minutes']),
            'total_break_minutes': 0,
            'comment': comment,
            'submission_status': 'draft',  # インポートデータは下書き扱い
            'source': 'git_import',  # インポート元を識別
            'git_commits': len(session['commits']),
            'git_files_changed': total_files,
            'git_lines_added': total_lines_added,
            'git_lines_deleted': total_lines_deleted
        }

        return record

    def import_commits_to_account(self, csv_file: str, account: str,
                                  max_gap_minutes: int = 120,
                                  skip_existing: bool = True) -> Dict:
        """
        Gitコミットデータをアカウントにインポート

        Args:
            csv_file: CSVファイルパス
            account: 社員番号
            max_gap_minutes: セッション分割の最大間隔（分）
            skip_existing: 既存の日付をスキップするか

        Returns:
            インポート結果の統計
        """
        print(f"\n{'='*60}")
        print(f"Gitコミットデータインポート - {account}")
        print(f"{'='*60}\n")

        # CSVを読み込み
        commits = self.load_git_commits_csv(csv_file)

        if not commits:
            print("インポートするデータがありません")
            return self.statistics

        # 時系列順にソート
        commits = sorted(commits, key=lambda x: x['datetime'])

        # セッションにグループ化
        print(f"\n作業セッションにグループ化中（最大間隔: {max_gap_minutes}分）...")
        sessions = self.group_commits_by_session(commits, max_gap_minutes)
        print(f"[OK] {len(sessions)} 個の作業セッションを検出")

        # 既存データを読み込み
        data = self.storage.load_data()

        if account not in data['accounts']:
            data['accounts'][account] = {'projects': {}, 'records': []}

        existing_records = data['accounts'][account]['records']

        # 既存の日付をチェック
        existing_dates = set()
        for record in existing_records:
            if record.get('source') != 'git_import':  # 手動入力データのみ考慮
                existing_dates.add(record['date'])

        # セッションをインポート
        imported_count = 0
        skipped_count = 0

        for session in sessions:
            date_str = session['date'].strftime('%Y-%m-%d')

            # 既存データをスキップ
            if skip_existing and date_str in existing_dates:
                print(f"  スキップ: {date_str} (既存データあり)")
                skipped_count += 1
                continue

            # タイムレコードに変換
            record = self.convert_session_to_timerecord(session, account)

            # 追加
            existing_records.append(record)
            imported_count += 1

            print(f"  インポート: {date_str} {session['project']} "
                  f"({session['total_minutes']}分, {len(session['commits'])}コミット)")

        # ソート（日付降順）
        existing_records.sort(key=lambda x: x['start_time'], reverse=True)

        # 保存
        self.storage.save_data(data)

        # 統計を更新
        self.statistics['total_imported'] = imported_count
        self.statistics['skipped_duplicates'] = skipped_count
        self.statistics['total_work_minutes'] = sum(
            s['total_minutes'] for s in sessions[:imported_count]
        )

        print(f"\n{'='*60}")
        print(f"インポート完了")
        print(f"{'='*60}")
        print(f"  インポート件数: {imported_count}")
        print(f"  スキップ件数: {skipped_count}")
        print(f"  総作業時間: {self.statistics['total_work_minutes']} 分 "
              f"({self.statistics['total_work_minutes']/60:.1f} 時間)")
        print(f"{'='*60}\n")

        return self.statistics

    def preview_import(self, csv_file: str, max_gap_minutes: int = 120) -> List[Dict]:
        """
        インポートのプレビュー（実際にはインポートしない）

        Args:
            csv_file: CSVファイルパス
            max_gap_minutes: セッション分割の最大間隔

        Returns:
            セッションのリスト
        """
        commits = self.load_git_commits_csv(csv_file)
        commits = sorted(commits, key=lambda x: x['datetime'])
        sessions = self.group_commits_by_session(commits, max_gap_minutes)

        print(f"\n{'='*60}")
        print("インポートプレビュー")
        print(f"{'='*60}\n")

        for i, session in enumerate(sessions, 1):
            print(f"{i}. {session['date']} {session['project']}")
            print(f"   時刻: {session['start_time'].strftime('%H:%M')} - "
                  f"{session['last_commit_time'].strftime('%H:%M')}")
            print(f"   作業時間: {session['total_minutes']}分")
            print(f"   コミット数: {len(session['commits'])}")

            for commit in session['commits']:
                print(f"     [{commit['commit_id']}] {commit['message'][:50]}")

            flags = []
            if session['is_overtime']:
                flags.append('時間外')
            if session['is_weekend']:
                flags.append('休日')
            if session['is_late_night']:
                flags.append('深夜')
            if flags:
                print(f"   フラグ: {', '.join(flags)}")

            print()

        total_minutes = sum(s['total_minutes'] for s in sessions)
        print(f"{'='*60}")
        print(f"合計: {len(sessions)} セッション, {total_minutes} 分 ({total_minutes/60:.1f} 時間)")
        print(f"{'='*60}\n")

        return sessions

    def export_statistics(self, output_file: str = 'git_import_statistics.json'):
        """インポート統計をJSONで出力"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.statistics, f, ensure_ascii=False, indent=2)
        print(f"[OK] 統計情報を保存: {output_file}")


def main():
    """メイン実行"""
    import sys

    print("\n" + "="*60)
    print("Git Commit Importer - Gitコミット履歴インポートツール")
    print("="*60 + "\n")

    # コマンドライン引数から設定を読み込み
    if len(sys.argv) < 3:
        print("使い方:")
        print("  python git_import.py <CSVファイル> <社員番号> [オプション]")
        print("\nオプション:")
        print("  --preview : インポートせずにプレビューのみ")
        print("  --gap <分> : セッション分割の最大間隔（デフォルト: 120分）")
        print("  --force : 既存データを上書き")
        print("\n例:")
        print("  python git_import.py git_work_time_evidence.csv 0053629")
        print("  python git_import.py git_work_time_evidence.csv 0053629 --preview")
        print("  python git_import.py git_work_time_evidence.csv 0053629 --gap 90")
        return

    csv_file = sys.argv[1]
    account = sys.argv[2]

    # オプション解析
    preview_mode = '--preview' in sys.argv
    force_overwrite = '--force' in sys.argv
    max_gap_minutes = 120

    if '--gap' in sys.argv:
        gap_index = sys.argv.index('--gap')
        if gap_index + 1 < len(sys.argv):
            max_gap_minutes = int(sys.argv[gap_index + 1])

    # インポーター初期化
    importer = GitCommitImporter()

    if preview_mode:
        # プレビューのみ
        importer.preview_import(csv_file, max_gap_minutes)
    else:
        # 実際にインポート
        importer.import_commits_to_account(
            csv_file,
            account,
            max_gap_minutes=max_gap_minutes,
            skip_existing=not force_overwrite
        )
        importer.export_statistics()

        print("\n[OK] インポート完了！")
        print("  GUIアプリケーションを起動してデータを確認してください。")


if __name__ == '__main__':
    main()
