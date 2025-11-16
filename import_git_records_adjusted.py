#!/usr/bin/env python3
"""
Gitログからタイムクロックデータベースに作業記録をインポート（時間調整版）
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List

def load_missing_records(missing_json_path: str, start_period: str, end_period: str) -> Dict:
    """不足記録から指定期間のデータを読み込み"""
    with open(missing_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 期間フィルタリング
    filtered = {}
    for date_str, info in data['missing_dates'].items():
        if start_period <= date_str <= end_period:
            filtered[date_str] = info

    return filtered

def estimate_work_duration_adjusted(commits: List[dict], date_str: str) -> Dict:
    """コミット情報から作業時間を推定（コミット間隔に基づく休憩時間推定）"""
    if not commits:
        return None

    # 最初と最後のコミット時刻
    times = sorted([c['time'] for c in commits])
    start_time = times[0]
    end_time = times[-1]

    # 開始・終了時刻をdatetimeに変換
    start_dt = datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(f"{date_str} {end_time}", '%Y-%m-%d %H:%M:%S')

    # 作業時間が短すぎる場合は最低2時間とする
    total_span_minutes = (end_dt - start_dt).total_seconds() / 60
    if total_span_minutes < 120:  # 2時間未満
        end_dt = start_dt + timedelta(hours=2)
        total_span_minutes = 120

    # コミット間隔を分析して休憩時間を推定
    commit_times = [datetime.strptime(f"{date_str} {t}", '%Y-%m-%d %H:%M:%S') for t in times]
    breaks = []
    total_break_minutes = 0

    # コミット間隔が2時間以上空いている箇所を休憩とみなす
    for i in range(1, len(commit_times)):
        gap_minutes = (commit_times[i] - commit_times[i-1]).total_seconds() / 60

        if gap_minutes >= 120:  # 2時間以上の空白
            # コミット後30分〜次のコミット30分前を休憩とする
            break_start = commit_times[i-1] + timedelta(minutes=30)
            break_end = commit_times[i] - timedelta(minutes=30)
            break_duration = (break_end - break_start).total_seconds() / 60

            if break_duration > 0:
                breaks.append({
                    'start': break_start.isoformat(),
                    'end': break_end.isoformat()
                })
                total_break_minutes += break_duration

    # 総時間が6時間以上で休憩がない場合は、昼休み1時間を追加
    if total_span_minutes >= 360 and total_break_minutes == 0:
        lunch_start = start_dt + timedelta(hours=3)
        lunch_end = lunch_start + timedelta(hours=1)
        breaks.append({
            'start': lunch_start.isoformat(),
            'end': lunch_end.isoformat()
        })
        total_break_minutes = 60

    # 実働時間を計算
    total_work_minutes = int(total_span_minutes - total_break_minutes)

    return {
        'start_time': start_dt.isoformat(),
        'end_time': end_dt.isoformat(),
        'breaks': breaks,
        'total_minutes': total_work_minutes,
        'total_break_minutes': int(total_break_minutes)
    }

def create_record(date_str: str, info: Dict, account: str) -> Dict:
    """タイムクロック記録を作成"""
    # 主なリポジトリ名を取得
    repos = list(set([c['repo'] for c in info['commits']]))
    project = repos[0] if repos else 'unknown'

    # 作業時間を推定（調整版）
    work_info = estimate_work_duration_adjusted(info['commits'], date_str)

    if not work_info:
        return None

    # 日曜日判定
    is_legal_holiday = info['is_sunday']

    record = {
        'account': account,
        'project': project,
        'date': date_str,
        'start_time': work_info['start_time'],
        'breaks': work_info['breaks'],
        'end_time': work_info['end_time'],
        'status': 'completed',
        'total_minutes': work_info['total_minutes'],
        'total_break_minutes': work_info['total_break_minutes'],
        'comment': f"Git作業記録から自動インポート ({len(info['commits'])}コミット)",
        'is_legal_holiday': is_legal_holiday,
        'submission_status': 'imported'
    }

    return record

def import_records(missing_json_path: str, db_path: str, account: str,
                   start_period: str, end_period: str):
    """記録をインポート（自動実行版）"""

    print("=" * 100)
    print("Gitログから作業記録をインポート（時間調整版）")
    print("=" * 100)
    print(f"対象期間: {start_period} ～ {end_period}")
    print(f"アカウント: {account}")
    print(f"データベース: {db_path}")
    print("=" * 100)

    # 不足記録を読み込み
    missing = load_missing_records(missing_json_path, start_period, end_period)
    print(f"\n不足記録: {len(missing)}日分")

    # 既存のデータベースを読み込み
    with open(db_path, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    if account not in db_data['accounts']:
        db_data['accounts'][account] = {
            'projects': {},
            'records': []
        }

    current_records = db_data['accounts'][account]['records']
    existing_dates = set(r['date'] for r in current_records)

    print(f"既存の記録: {len(existing_dates)}日分")

    # インポート対象の記録を作成
    new_records = []
    skipped = []

    for date_str in sorted(missing.keys()):
        if date_str in existing_dates:
            skipped.append(date_str)
            continue

        info = missing[date_str]
        record = create_record(date_str, info, account)

        if record:
            new_records.append(record)

            # 詳細表示
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]
            sunday_mark = " ★" if info['is_sunday'] else ""

            print(f"\n{date_str} ({weekday}){sunday_mark}")
            print(f"  プロジェクト: {record['project']}")
            print(f"  作業時間: {record['start_time'][11:16]} ～ {record['end_time'][11:16]}")
            print(f"  実働時間: {record['total_minutes']}分 ({record['total_minutes']/60:.1f}時間)")
            print(f"  休憩時間: {record['total_break_minutes']}分")
            print(f"  コミット数: {len(info['commits'])}件")

    if skipped:
        print(f"\n既に存在するためスキップ: {len(skipped)}日分")

    print("\n" + "=" * 100)
    print(f"インポート対象: {len(new_records)}日分")
    print("=" * 100)

    if not new_records:
        print("インポート対象の新しい記録がありません")
        return

    # サマリー
    total_hours = sum(r['total_minutes'] for r in new_records) / 60
    sunday_count = sum(1 for r in new_records if r.get('is_legal_holiday', False))

    print(f"\n【サマリー】")
    print(f"  総日数: {len(new_records)}日")
    print(f"  総時間: {total_hours:.1f}時間")
    print(f"  平均: {total_hours/len(new_records):.1f}時間/日")
    print(f"  日曜日: {sunday_count}日")

    # 実際にインポート
    db_data['accounts'][account]['records'].extend(new_records)

    # 日付順にソート
    db_data['accounts'][account]['records'].sort(key=lambda x: x['date'])

    # バックアップを作成
    backup_path = db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)
    print(f"\nバックアップ作成: {backup_path}")

    # データベースを更新
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(new_records)}件の記録をインポートしました")
    print(f"✓ データベース更新: {db_path}")

def main():
    # 設定
    MISSING_JSON = 'missing_work_records.json'
    DB_PATH = 'json/timeclock_data.json'
    ACCOUNT = '0053629'

    # 対象期間（2025-10月期〜11月期）
    START_PERIOD = '2025-09-16'
    END_PERIOD = '2025-11-15'

    import_records(MISSING_JSON, DB_PATH, ACCOUNT, START_PERIOD, END_PERIOD)

if __name__ == '__main__':
    main()
