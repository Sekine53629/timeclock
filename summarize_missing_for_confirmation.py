#!/usr/bin/env python3
"""
不足している打刻実績を期間別にサマライズして確認用に出力
"""
import json
from datetime import datetime
from collections import defaultdict

def main():
    with open('missing_work_records.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing = data['missing_dates']

    # 期間を15日締めで区切る
    def get_period(date_str):
        """日付から期間を計算（YYYY-MM形式で返す）"""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if dt.day >= 16:
            # 16日以降なら翌月期
            if dt.month == 12:
                return f"{dt.year + 1}-01"
            else:
                return f"{dt.year}-{dt.month + 1:02d}"
        else:
            # 15日以前なら当月期
            return f"{dt.year}-{dt.month:02d}"

    # 期間ごとに集計
    periods = defaultdict(list)
    for date_str, info in sorted(missing.items()):
        period = get_period(date_str)
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_name = ['月', '火', '水', '木', '金', '土', '日'][info['weekday']]

        periods[period].append({
            'date': date_str,
            'weekday': weekday_name,
            'is_sunday': info['is_sunday'],
            'commit_count': info['commit_count'],
            'start_time': info['start_time'],
            'end_time': info['end_time'],
            'repos': list(set([c['repo'] for c in info['commits']]))
        })

    # 最近の期間（2025-10, 2025-11）を抽出
    recent_periods = ['2025-10', '2025-11', '2025-12']

    print("=" * 100)
    print("不足している打刻実績（確認用サマリー）")
    print("=" * 100)

    total_missing = 0
    for period in sorted(periods.keys(), reverse=True):
        days = periods[period]
        if period not in recent_periods:
            continue

        total_missing += len(days)
        sunday_count = sum(1 for d in days if d['is_sunday'])

        print(f"\n【{period}月期】({len(days)}日分) ※日曜日: {sunday_count}日")
        print("-" * 100)

        for d in sorted(days, key=lambda x: x['date']):
            sunday_mark = " ★日曜日" if d['is_sunday'] else ""
            repos_str = ", ".join(d['repos'][:3])
            if len(d['repos']) > 3:
                repos_str += f" 他{len(d['repos'])-3}件"

            print(f"{d['date']} ({d['weekday']}){sunday_mark:10s}  {d['start_time']} ～ {d['end_time']}  "
                  f"{d['commit_count']:2d}commits  [{repos_str}]")

    print("\n" + "=" * 100)
    print(f"最近3ヶ月の不足日数: {total_missing}日")
    print("=" * 100)

    # 全期間のサマリー
    print("\n【全期間サマリー】")
    print("-" * 100)
    for period in sorted(periods.keys(), reverse=True):
        days = periods[period]
        sunday_count = sum(1 for d in days if d['is_sunday'])
        total_commits = sum(d['commit_count'] for d in days)
        print(f"{period}月期: {len(days):3d}日 (日曜{sunday_count:2d}日)  総コミット数: {total_commits:4d}件")

    print(f"\n総不足日数: {data['summary']['total_missing_days']}日")
    print(f"現在の打刻実績: {data['summary']['current_record_days']}日")

if __name__ == '__main__':
    main()
