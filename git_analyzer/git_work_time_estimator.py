"""
Git Commit Work Time Estimator
コミット履歴とコード変更量から実際の作業時間を推定するツール
Excel/VBAのGUIシステムへのインポート用データを生成
"""

import os
import json
import csv
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re


class GitWorkTimeEstimator:
    """Gitコミット履歴から作業時間を推定"""

    def __init__(self, repo_paths: List[str], author_names: List[str]):
        """
        Args:
            repo_paths: 分析対象のGitリポジトリのパスリスト
            author_names: 作業者の名前リスト（Git設定の名前）
        """
        self.repo_paths = repo_paths
        self.author_names = author_names
        self.all_commits = []

    def estimate_work_time_from_changes(self, lines_added: int, lines_deleted: int,
                                       files_changed: int) -> float:
        """
        コード変更量から作業時間を推定（分単位）

        推定ロジック:
        - 新規追加: 10行 = 約5分
        - 削除: 10行 = 約2分（削除は追加より速い）
        - ファイル変更数: 1ファイル = 最低10分（切り替えコスト）
        - 複数ファイル変更: 追加で1ファイルあたり5分

        Args:
            lines_added: 追加行数
            lines_deleted: 削除行数
            files_changed: 変更ファイル数

        Returns:
            推定作業時間（分）
        """
        # 基本時間: 行数ベース
        add_time = (lines_added / 10) * 5  # 10行で5分
        delete_time = (lines_deleted / 10) * 2  # 10行で2分

        # ファイル変更による追加時間
        if files_changed > 0:
            file_time = 10 + (files_changed - 1) * 5  # 最初のファイル10分 + 追加ファイルごとに5分
        else:
            file_time = 0

        # 合計時間（最低5分）
        total_time = max(add_time + delete_time + file_time, 5)

        # 非常に大きな変更の場合は上限を設ける（1コミット最大480分=8時間）
        total_time = min(total_time, 480)

        return round(total_time, 1)

    def get_commit_stats(self, repo_path: str, commit_hash: str) -> Dict:
        """特定のコミットの変更統計を取得"""
        try:
            # git show で変更内容を取得
            cmd = ['git', '-C', repo_path, 'show', '--stat', '--format=%H', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

            if result.returncode != 0:
                return {'files_changed': 0, 'lines_added': 0, 'lines_deleted': 0}

            output = result.stdout

            # 統計行を解析（例: "3 files changed, 150 insertions(+), 20 deletions(-)"）
            stats_pattern = r'(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?'
            match = re.search(stats_pattern, output)

            if match:
                files_changed = int(match.group(1))
                lines_added = int(match.group(2) or 0)
                lines_deleted = int(match.group(3) or 0)
            else:
                # マッチしない場合はdiffstatから推定
                files_changed = output.count('|')
                lines_added = output.count('+')
                lines_deleted = output.count('-')

            return {
                'files_changed': files_changed,
                'lines_added': lines_added,
                'lines_deleted': lines_deleted
            }

        except Exception as e:
            print(f"Error getting commit stats: {e}")
            return {'files_changed': 0, 'lines_added': 0, 'lines_deleted': 0}

    def collect_commits_from_repo(self, repo_path: str) -> List[Dict]:
        """1つのリポジトリからコミット履歴を収集"""
        commits = []
        repo_name = os.path.basename(repo_path)

        print(f"\n分析中: {repo_name}")

        try:
            # 全著者のコミットを取得
            for author in self.author_names:
                cmd = [
                    'git', '-C', repo_path, 'log',
                    f'--author={author}',
                    '--all',
                    '--no-merges',
                    '--format=%H|%aI|%an|%ae|%s'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

                if result.returncode != 0:
                    print(f"  エラー: {author} のログ取得失敗")
                    continue

                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue

                    parts = line.split('|')
                    if len(parts) < 5:
                        continue

                    commit_hash = parts[0]
                    timestamp_str = parts[1]
                    author_name = parts[2]
                    author_email = parts[3]
                    message = parts[4]

                    # タイムスタンプをパース
                    timestamp = datetime.fromisoformat(timestamp_str.replace('+09:00', ''))
                    jst_timestamp = timestamp + timedelta(hours=9)

                    # コミットの変更統計を取得
                    stats = self.get_commit_stats(repo_path, commit_hash)

                    # 作業時間を推定
                    estimated_minutes = self.estimate_work_time_from_changes(
                        stats['lines_added'],
                        stats['lines_deleted'],
                        stats['files_changed']
                    )

                    commit_data = {
                        'repo_path': repo_path,
                        'repo_name': repo_name,
                        'commit_hash': commit_hash[:8],
                        'commit_hash_full': commit_hash,
                        'author_name': author_name,
                        'author_email': author_email,
                        'message': message[:200],  # 最初の200文字
                        'timestamp': timestamp,
                        'timestamp_jst': jst_timestamp,
                        'date': jst_timestamp.date(),
                        'time': jst_timestamp.time(),
                        'hour': jst_timestamp.hour,
                        'minute': jst_timestamp.minute,
                        'weekday': jst_timestamp.strftime('%A'),
                        'weekday_jp': self.get_japanese_weekday(jst_timestamp.weekday()),
                        'is_weekend': jst_timestamp.weekday() >= 5,
                        'is_overtime': jst_timestamp.hour >= 18 or jst_timestamp.hour < 9,
                        'is_late_night': jst_timestamp.hour >= 22 or jst_timestamp.hour < 5,
                        'files_changed': stats['files_changed'],
                        'lines_added': stats['lines_added'],
                        'lines_deleted': stats['lines_deleted'],
                        'estimated_work_minutes': estimated_minutes,
                        'estimated_work_hours': round(estimated_minutes / 60, 2)
                    }

                    commits.append(commit_data)

            print(f"  収集完了: {len(commits)} コミット")

        except Exception as e:
            print(f"  エラー: {e}")

        return commits

    def collect_all_commits(self) -> List[Dict]:
        """全リポジトリからコミットを収集"""
        print("\n" + "="*60)
        print("Git Work Time Estimation - 開始")
        print("="*60)

        for repo_path in self.repo_paths:
            if not os.path.exists(repo_path):
                print(f"\n警告: {repo_path} が見つかりません")
                continue

            if not os.path.exists(os.path.join(repo_path, '.git')):
                print(f"\n警告: {repo_path} はGitリポジトリではありません")
                continue

            commits = self.collect_commits_from_repo(repo_path)
            self.all_commits.extend(commits)

        # 時系列でソート
        self.all_commits = sorted(self.all_commits, key=lambda x: x['timestamp_jst'])

        print(f"\n総コミット数: {len(self.all_commits)}")
        return self.all_commits

    @staticmethod
    def get_japanese_weekday(weekday: int) -> str:
        """曜日を日本語に変換"""
        days = ['月', '火', '水', '木', '金', '土', '日']
        return days[weekday]

    def calculate_overtime_summary(self) -> Dict:
        """残業時間のサマリーを計算"""
        if not self.all_commits:
            return {}

        total_minutes = sum(c['estimated_work_minutes'] for c in self.all_commits)
        overtime_commits = [c for c in self.all_commits if c['is_overtime']]
        weekend_commits = [c for c in self.all_commits if c['is_weekend']]
        late_night_commits = [c for c in self.all_commits if c['is_late_night']]

        overtime_minutes = sum(c['estimated_work_minutes'] for c in overtime_commits)
        weekend_minutes = sum(c['estimated_work_minutes'] for c in weekend_commits)
        late_night_minutes = sum(c['estimated_work_minutes'] for c in late_night_commits)

        # 月別集計
        monthly_stats = {}
        for commit in self.all_commits:
            month_key = commit['timestamp_jst'].strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'total_commits': 0,
                    'total_minutes': 0,
                    'overtime_commits': 0,
                    'overtime_minutes': 0,
                    'weekend_commits': 0,
                    'weekend_minutes': 0,
                    'late_night_commits': 0,
                    'late_night_minutes': 0,
                    'projects': set()
                }

            stats = monthly_stats[month_key]
            stats['total_commits'] += 1
            stats['total_minutes'] += commit['estimated_work_minutes']
            stats['projects'].add(commit['repo_name'])

            if commit['is_overtime']:
                stats['overtime_commits'] += 1
                stats['overtime_minutes'] += commit['estimated_work_minutes']
            if commit['is_weekend']:
                stats['weekend_commits'] += 1
                stats['weekend_minutes'] += commit['estimated_work_minutes']
            if commit['is_late_night']:
                stats['late_night_commits'] += 1
                stats['late_night_minutes'] += commit['estimated_work_minutes']

        # プロジェクト別集計
        project_stats = {}
        for commit in self.all_commits:
            project = commit['repo_name']
            if project not in project_stats:
                project_stats[project] = {
                    'commits': 0,
                    'minutes': 0,
                    'hours': 0
                }
            project_stats[project]['commits'] += 1
            project_stats[project]['minutes'] += commit['estimated_work_minutes']
            project_stats[project]['hours'] = round(project_stats[project]['minutes'] / 60, 2)

        summary = {
            'period': {
                'start': str(self.all_commits[0]['date']) if self.all_commits else None,
                'end': str(self.all_commits[-1]['date']) if self.all_commits else None
            },
            'total': {
                'commits': len(self.all_commits),
                'minutes': total_minutes,
                'hours': round(total_minutes / 60, 2),
                'days': round(total_minutes / 60 / 8, 2)
            },
            'overtime': {
                'commits': len(overtime_commits),
                'minutes': overtime_minutes,
                'hours': round(overtime_minutes / 60, 2),
                'percentage': round(overtime_minutes / total_minutes * 100, 1) if total_minutes > 0 else 0
            },
            'weekend': {
                'commits': len(weekend_commits),
                'minutes': weekend_minutes,
                'hours': round(weekend_minutes / 60, 2)
            },
            'late_night': {
                'commits': len(late_night_commits),
                'minutes': late_night_minutes,
                'hours': round(late_night_minutes / 60, 2)
            },
            'monthly': {k: {**v, 'projects': len(v['projects']), 'hours': round(v['total_minutes']/60, 2)}
                       for k, v in monthly_stats.items()},
            'by_project': project_stats
        }

        return summary

    def save_to_excel_csv(self, filename: str = 'git_work_time_evidence.csv'):
        """Excel/VBAインポート用のCSVを生成"""
        if not self.all_commits:
            print("保存するデータがありません")
            return

        # Excel/VBAで読み込みやすい形式
        with open(filename, 'w', newline='', encoding='shift_jis', errors='ignore') as f:
            writer = csv.writer(f)

            # ヘッダー（日本語）
            writer.writerow([
                '日付', '時刻', '曜日', 'プロジェクト名', 'コミットID',
                '作業内容', '変更ファイル数', '追加行数', '削除行数',
                '推定作業時間（分）', '推定作業時間（時間）',
                '時間外', '休日', '深夜', '作業者名'
            ])

            # データ行
            for commit in self.all_commits:
                writer.writerow([
                    commit['date'],
                    commit['time'],
                    commit['weekday_jp'],
                    commit['repo_name'],
                    commit['commit_hash'],
                    commit['message'],
                    commit['files_changed'],
                    commit['lines_added'],
                    commit['lines_deleted'],
                    commit['estimated_work_minutes'],
                    commit['estimated_work_hours'],
                    '○' if commit['is_overtime'] else '',
                    '○' if commit['is_weekend'] else '',
                    '○' if commit['is_late_night'] else '',
                    commit['author_name']
                ])

        print(f"✓ Excel用CSVを保存: {filename}")

    def save_summary_report(self, filename: str = 'work_time_summary.txt'):
        """サマリーレポートをテキストで保存"""
        summary = self.calculate_overtime_summary()

        lines = []
        lines.append("="*70)
        lines.append("Git作業時間推定レポート - 残業代請求用証拠資料")
        lines.append("="*70)
        lines.append(f"\n作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        lines.append(f"\n【分析期間】")
        lines.append(f"  開始日: {summary['period']['start']}")
        lines.append(f"  終了日: {summary['period']['end']}")

        lines.append(f"\n【総作業時間】")
        lines.append(f"  総コミット数: {summary['total']['commits']:,} 件")
        lines.append(f"  推定総作業時間: {summary['total']['hours']:,.1f} 時間 ({summary['total']['days']:.1f} 日分)")
        lines.append(f"  推定総作業時間: {summary['total']['minutes']:,.0f} 分")

        lines.append(f"\n【時間外労働】")
        lines.append(f"  時間外コミット数: {summary['overtime']['commits']:,} 件")
        lines.append(f"  推定時間外労働: {summary['overtime']['hours']:,.1f} 時間")
        lines.append(f"  全体に占める割合: {summary['overtime']['percentage']}%")

        lines.append(f"\n【休日労働】")
        lines.append(f"  休日コミット数: {summary['weekend']['commits']:,} 件")
        lines.append(f"  推定休日労働: {summary['weekend']['hours']:,.1f} 時間")

        lines.append(f"\n【深夜労働（22時〜5時）】")
        lines.append(f"  深夜コミット数: {summary['late_night']['commits']:,} 件")
        lines.append(f"  推定深夜労働: {summary['late_night']['hours']:,.1f} 時間")

        lines.append(f"\n【月別サマリー】")
        lines.append(f"{'年月':<12} {'コミット':>8} {'総時間':>10} {'時間外':>10} {'休日':>8} {'深夜':>8}")
        lines.append("-" * 70)
        for month, stats in sorted(summary['monthly'].items()):
            lines.append(
                f"{month:<12} {stats['total_commits']:>8} "
                f"{stats['hours']:>9.1f}h {stats['overtime_minutes']/60:>9.1f}h "
                f"{stats['weekend_minutes']/60:>7.1f}h {stats['late_night_minutes']/60:>7.1f}h"
            )

        lines.append(f"\n【プロジェクト別作業時間】")
        lines.append(f"{'プロジェクト名':<30} {'コミット数':>10} {'作業時間':>10}")
        lines.append("-" * 70)
        for project, stats in sorted(summary['by_project'].items(), key=lambda x: x[1]['hours'], reverse=True):
            lines.append(f"{project:<30} {stats['commits']:>10} {stats['hours']:>9.1f}h")

        lines.append("\n" + "="*70)
        lines.append("【推定ロジック】")
        lines.append("  - コード追加: 10行 = 約5分")
        lines.append("  - コード削除: 10行 = 約2分")
        lines.append("  - ファイル変更: 1ファイル = 最低10分")
        lines.append("  - 時間外: 18時以降または9時以前のコミット")
        lines.append("  - 深夜: 22時以降または5時以前のコミット")
        lines.append("  - 休日: 土曜日・日曜日のコミット")
        lines.append("="*70)

        report_text = '\n'.join(lines)

        # ファイルに保存
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)

        # コンソールにも表示
        print(report_text)
        print(f"\n✓ サマリーレポートを保存: {filename}")

    def save_to_json(self, filename: str = 'git_work_time_data.json'):
        """JSON形式で保存"""
        if not self.all_commits:
            return

        # datetimeをシリアライズ可能に変換
        commits_data = []
        for commit in self.all_commits:
            commit_copy = commit.copy()
            commit_copy['timestamp'] = commit['timestamp'].isoformat()
            commit_copy['timestamp_jst'] = commit['timestamp_jst'].isoformat()
            commit_copy['date'] = str(commit['date'])
            commit_copy['time'] = str(commit['time'])
            commits_data.append(commit_copy)

        summary = self.calculate_overtime_summary()

        output = {
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'commits': commits_data
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✓ JSON形式で保存: {filename}")


def load_config(config_file: str = 'git_repos_config.json') -> Dict:
    """設定ファイルを読み込み"""
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def create_sample_config():
    """サンプル設定ファイルを作成"""
    sample_config = {
        "repo_paths": [
            "C:/Users/username/Documents/GitHub/project1",
            "C:/Users/username/Documents/GitHub/project2",
            "C:/Users/username/Documents/GitHub/project3"
        ],
        "author_names": [
            "Your Name",
            "Another Name"
        ],
        "hourly_rate": 2000,
        "overtime_rate": 1.25,
        "weekend_rate": 1.35,
        "late_night_rate": 1.5
    }

    with open('git_repos_config.json', 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, ensure_ascii=False, indent=2)

    print("サンプル設定ファイル作成: git_repos_config.json")
    print("このファイルを編集して実際の値を設定してください")


def main():
    """メイン実行"""
    print("\n" + "="*70)
    print("Git Work Time Estimator - 作業時間推定ツール")
    print("="*70)

    # 設定ファイル読み込み
    config = load_config()

    if not config:
        print("\n設定ファイルが見つかりません。サンプルを作成します...")
        create_sample_config()
        print("\ngit_repos_config.json を編集してから再実行してください")
        return

    repo_paths = config.get('repo_paths', [])
    author_names = config.get('author_names', [])

    if not repo_paths or not author_names:
        print("エラー: repo_paths または author_names が設定されていません")
        return

    print(f"\n分析対象リポジトリ数: {len(repo_paths)}")
    print(f"分析対象作業者: {', '.join(author_names)}")

    # 推定実行
    estimator = GitWorkTimeEstimator(repo_paths, author_names)
    estimator.collect_all_commits()

    # レポート生成
    estimator.save_summary_report()
    estimator.save_to_excel_csv()
    estimator.save_to_json()

    print("\n" + "="*70)
    print("✓ 分析完了！")
    print("="*70)
    print("\n生成されたファイル:")
    print("  1. work_time_summary.txt - サマリーレポート（印刷用）")
    print("  2. git_work_time_evidence.csv - Excel/VBAインポート用")
    print("  3. git_work_time_data.json - 詳細データ（プログラム用）")
    print("\nCSVファイルをExcel/VBAシステムでインポートしてください")


if __name__ == '__main__':
    main()
