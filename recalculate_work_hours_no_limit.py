#!/usr/bin/env python3
"""
最大値制限を撤廃して作業時間を再計算
"""
import json
from collections import defaultdict

def recalculate_work_hours(input_file, output_file):
    """作業時間を最大値制限なしで再計算"""

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("⏱️  作業時間の再計算（最大値制限なし）")
    print("=" * 80)
    print()

    total_hours_old = 0
    total_hours_new = 0
    tsuruha_hours_old = 0
    tsuruha_hours_new = 0

    changes_summary = []

    # 全プロジェクトを再計算
    for project in data['all_projects']:
        project_name = project['project_name']
        old_total = project['estimated_total_hours']

        new_work_days = []

        for work_day in project.get('work_days', []):
            date = work_day['date']
            start_time = work_day['start_time']
            end_time = work_day['end_time']
            commits_count = work_day['commits_count']

            # 時間差を再計算（最大値制限なし）
            start_h, start_m = map(int, start_time.split(':')[:2])
            end_h, end_m = map(int, end_time.split(':')[:2])

            hours = end_h - start_h + (end_m - start_m) / 60

            # 最低値0.5時間のみ適用
            if hours < 0.5:
                hours = 0.5

            new_work_days.append({
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'estimated_hours': round(hours, 2),
                'commits_count': commits_count
            })

        # 新しい合計時間
        new_total = sum(day['estimated_hours'] for day in new_work_days)

        # プロジェクトデータを更新
        project['work_days'] = new_work_days
        project['estimated_total_hours'] = round(new_total, 2)

        total_hours_old += old_total
        total_hours_new += new_total

        # 変更があったプロジェクトを記録
        if abs(new_total - old_total) > 0.01:
            change = new_total - old_total
            changes_summary.append({
                'project_name': project_name,
                'old_hours': old_total,
                'new_hours': new_total,
                'change': change,
                'is_tsuruha': project.get('has_tsuruha_email', False)
            })

            if project.get('has_tsuruha_email', False):
                tsuruha_hours_old += old_total
                tsuruha_hours_new += new_total

    # Tsuruha関連プロジェクトの合計も更新
    data['tsuruha_projects'] = [p for p in data['all_projects'] if p.get('has_tsuruha_email', False)]

    # サマリーを更新
    data['summary']['total_estimated_hours'] = round(total_hours_new, 2)
    data['summary']['tsuruha_estimated_hours'] = round(sum(p['estimated_total_hours'] for p in data['tsuruha_projects']), 2)

    # 結果を保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # レポート表示
    print(f"✅ 再計算完了")
    print()
    print("=" * 80)
    print("📊 変更サマリー")
    print("=" * 80)
    print(f"総推定作業時間（旧）: {total_hours_old:.2f}時間")
    print(f"総推定作業時間（新）: {total_hours_new:.2f}時間")
    print(f"差分: +{total_hours_new - total_hours_old:.2f}時間")
    print()
    print(f"🏢 Tsuruha関連（旧）: {tsuruha_hours_old:.2f}時間")
    print(f"🏢 Tsuruha関連（新）: {tsuruha_hours_new:.2f}時間")
    print(f"差分: +{tsuruha_hours_new - tsuruha_hours_old:.2f}時間")
    print()

    # 変更があったプロジェクトを表示
    if changes_summary:
        print("=" * 80)
        print("📋 作業時間が変更されたプロジェクト")
        print("=" * 80)

        # 変更が大きい順にソート
        changes_summary.sort(key=lambda x: x['change'], reverse=True)

        for item in changes_summary:
            mark = "🏢" if item['is_tsuruha'] else "  "
            print(f"\n{mark} {item['project_name']}")
            print(f"   旧: {item['old_hours']:.2f}時間 → 新: {item['new_hours']:.2f}時間")
            print(f"   差分: +{item['change']:.2f}時間")

    print("\n" + "=" * 80)
    print(f"✅ 結果を保存しました: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    input_file = 'complete_github_work_history.json'
    output_file = 'complete_github_work_history_unlimited.json'

    recalculate_work_hours(input_file, output_file)
