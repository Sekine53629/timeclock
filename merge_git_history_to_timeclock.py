#!/usr/bin/env python3
"""
Git作業履歴を通常の打刻実績にマージするスクリプト

- complete_github_work_history_with_estimation.json からTsuruha関連のwork_daysを取得
- timeclock_data.json の該当アカウントにマージ
- 同じ日付のレコードがある場合はスキップ（既存データを尊重）
- ない場合は新しいレコードとして追加
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from config_manager import ConfigManager


def load_git_work_history(json_path: str) -> Dict:
    """Git作業履歴JSONファイルを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_timeclock_data(db_path: str) -> Dict:
    """打刻データJSONファイルを読み込む"""
    timeclock_file = Path(db_path) / 'timeclock_data.json'
    if not timeclock_file.exists():
        return {"accounts": {}}

    with open(timeclock_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_timeclock_data(db_path: str, data: Dict):
    """打刻データを保存"""
    timeclock_file = Path(db_path) / 'timeclock_data.json'
    with open(timeclock_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def convert_work_day_to_record(work_day: Dict, project_name: str, account: str) -> Dict:
    """
    Git作業履歴のwork_dayを打刻レコード形式に変換

    Args:
        work_day: {
            'date': '2025-10-19',
            'start_time': '10:58:00',
            'end_time': '21:31:00',
            'estimated_hours': 8.0,
            'commits_count': 5
        }
        project_name: プロジェクト名
        account: アカウント名

    Returns:
        打刻レコード形式の辞書
    """
    date = work_day['date']
    start_time = work_day['start_time']
    end_time = work_day['end_time']
    estimated_hours = work_day['estimated_hours']
    commits_count = work_day['commits_count']

    # ISO 8601形式のタイムスタンプを作成
    start_datetime = f"{date}T{start_time}"
    end_datetime = f"{date}T{end_time}"

    # 作業時間を分に変換
    total_minutes = int(estimated_hours * 60)

    # コメントを生成
    comment = f"[Git] {project_name} ({commits_count}コミット)"

    return {
        "account": account,
        "project": "tsuruha",
        "date": date,
        "start_time": start_datetime,
        "breaks": [],
        "end_time": end_datetime,
        "status": "completed",
        "total_minutes": total_minutes,
        "comment": comment,
        "total_break_minutes": 0,
        "submission_status": "pending",
        "source": "git_import"  # Git由来であることを示すマーカー
    }


def get_existing_dates(account_records: List[Dict]) -> set:
    """既存のレコードの日付セットを取得"""
    return {record['date'] for record in account_records}


def merge_git_history(
    git_history: Dict,
    timeclock_data: Dict,
    target_account: str,
    dry_run: bool = False
) -> Dict:
    """
    Git作業履歴を打刻データにマージ

    Args:
        git_history: Git作業履歴データ
        timeclock_data: 打刻データ
        target_account: 対象アカウント名
        dry_run: Trueの場合は実際の変更は行わず、変更内容を表示のみ

    Returns:
        マージ結果の統計情報
    """
    # Tsuruha関連プロジェクトのみ抽出
    tsuruha_projects = [
        p for p in git_history['all_projects']
        if p.get('has_tsuruha_email', False)
    ]

    # アカウントが存在しない場合は初期化
    if target_account not in timeclock_data['accounts']:
        timeclock_data['accounts'][target_account] = {
            'projects': {},
            'records': []
        }

    account_data = timeclock_data['accounts'][target_account]
    existing_dates = get_existing_dates(account_data['records'])

    # 統計情報
    stats = {
        'total_projects': len(tsuruha_projects),
        'total_work_days': 0,
        'existing_dates': 0,
        'new_records': 0,
        'new_records_list': []
    }

    # 各プロジェクトのwork_daysをマージ
    for project in tsuruha_projects:
        project_name = project['project_name']
        work_days = project.get('work_days', [])

        stats['total_work_days'] += len(work_days)

        for work_day in work_days:
            date = work_day['date']

            # 既に同じ日付のレコードがある場合はスキップ
            if date in existing_dates:
                stats['existing_dates'] += 1
                continue

            # 新しいレコードを作成
            new_record = convert_work_day_to_record(work_day, project_name, target_account)
            stats['new_records'] += 1
            stats['new_records_list'].append({
                'date': date,
                'project': project_name,
                'hours': work_day['estimated_hours'],
                'commits': work_day['commits_count']
            })

            if not dry_run:
                account_data['records'].append(new_record)
                existing_dates.add(date)

    # レコードを日付順にソート
    if not dry_run:
        account_data['records'].sort(key=lambda x: x['date'])

    return stats


def print_stats(stats: Dict):
    """統計情報を表示"""
    print("=" * 80)
    print("📊 マージ結果")
    print("=" * 80)
    print(f"対象プロジェクト数: {stats['total_projects']}")
    print(f"総作業日数: {stats['total_work_days']}")
    print(f"既存レコード（スキップ）: {stats['existing_dates']}")
    print(f"新規追加レコード: {stats['new_records']}")
    print()

    if stats['new_records_list']:
        print("=" * 80)
        print("📋 新規追加されるレコード")
        print("=" * 80)

        # 日付順にソート
        sorted_records = sorted(stats['new_records_list'], key=lambda x: x['date'])

        total_hours = 0
        for record in sorted_records:
            print(f"📅 {record['date']}")
            print(f"   プロジェクト: {record['project']}")
            print(f"   推定作業時間: {record['hours']:.2f}時間")
            print(f"   コミット数: {record['commits']}")
            print()
            total_hours += record['hours']

        print(f"合計追加作業時間: {total_hours:.2f}時間")
        print()


def main():
    print("=" * 80)
    print("🔄 Git作業履歴を打刻データにマージ")
    print("=" * 80)
    print()

    # 設定を読み込み
    config_manager = ConfigManager()
    db_path = config_manager.get_db_path()
    default_account = config_manager.get_default_account()

    print(f"データベースパス: {db_path}")
    print(f"デフォルトアカウント: {default_account}")
    print()

    # 対象アカウントを確認
    if not default_account:
        print("⚠️  デフォルトアカウントが設定されていません。")
        account = input("対象アカウント名を入力してください: ").strip()
        if not account:
            print("❌ アカウント名が入力されませんでした。")
            sys.exit(1)
    else:
        account = default_account
        confirm = input(f"アカウント「{account}」にマージしますか？ (y/n): ").strip().lower()
        if confirm != 'y':
            account = input("対象アカウント名を入力してください: ").strip()
            if not account:
                print("❌ アカウント名が入力されませんでした。")
                sys.exit(1)

    print(f"✓ 対象アカウント: {account}")
    print()

    # Git作業履歴を読み込み
    git_history_file = 'complete_github_work_history_with_estimation.json'
    if not Path(git_history_file).exists():
        print(f"❌ Git作業履歴ファイルが見つかりません: {git_history_file}")
        sys.exit(1)

    print(f"📖 Git作業履歴を読み込み中: {git_history_file}")
    git_history = load_git_work_history(git_history_file)
    print(f"✓ {len(git_history['all_projects'])}プロジェクトを読み込みました")
    print()

    # 打刻データを読み込み
    print(f"📖 打刻データを読み込み中: {db_path}/timeclock_data.json")
    timeclock_data = load_timeclock_data(db_path)

    if account in timeclock_data['accounts']:
        existing_count = len(timeclock_data['accounts'][account].get('records', []))
        print(f"✓ 既存レコード数: {existing_count}")
    else:
        print("✓ 新規アカウント")
    print()

    # ドライラン実行
    print("🔍 ドライラン実行中（変更は行いません）...")
    print()
    stats = merge_git_history(git_history, timeclock_data.copy(), account, dry_run=True)
    print_stats(stats)

    # 確認
    if stats['new_records'] == 0:
        print("✓ マージするレコードがありません。")
        return

    print("=" * 80)
    confirm = input("上記の内容で打刻データにマージしますか？ (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ マージをキャンセルしました。")
        sys.exit(0)

    # 実際にマージ実行
    print()
    print("🚀 マージを実行中...")
    merge_git_history(git_history, timeclock_data, account, dry_run=False)

    # バックアップを作成
    backup_file = Path(db_path) / f"timeclock_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"💾 バックアップを作成中: {backup_file}")
    save_timeclock_data(backup_file.parent, timeclock_data)

    # 保存
    print(f"💾 打刻データを保存中: {db_path}/timeclock_data.json")
    save_timeclock_data(db_path, timeclock_data)

    print()
    print("=" * 80)
    print("✅ マージが完了しました！")
    print("=" * 80)
    print(f"新規追加レコード数: {stats['new_records']}")
    print(f"バックアップファイル: {backup_file}")
    print()


if __name__ == '__main__':
    main()
