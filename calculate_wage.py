"""
時間外労働賃金計算ツール
作業単価から月次・年次・総計の請求額を計算
"""
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict


# 作業単価（円/時間）
HOURLY_RATE = 2637


def calculate_wage_report(monthly_report_file: str = 'monthly_overtime_report.json') -> Dict:
    """
    月次レポートから賃金を計算

    Args:
        monthly_report_file: monthly_overtime_report.json

    Returns:
        賃金計算結果
    """
    # 月次レポートを読み込み
    with open(monthly_report_file, 'r', encoding='utf-8') as f:
        monthly_data = json.load(f)

    # 賃金計算結果
    wage_report = {
        'hourly_rate': HOURLY_RATE,
        'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monthly_details': {},
        'yearly_summary': {},
        'grand_total': {
            'total_work_hours': 0,
            'weighted_work_hours': 0,
            'total_wage': 0
        }
    }

    # 年ごとの集計
    yearly_stats = defaultdict(lambda: {
        'total_work_hours': 0,
        'weighted_work_hours': 0,
        'total_wage': 0,
        'months': []
    })

    # 月次計算
    for period_key, stats in monthly_data.items():
        # 年を抽出
        year = period_key.split('-')[0]

        # 作業時間（時間単位）
        total_work_hours = stats['total_work_hours']
        overtime_work_hours = stats['overtime_work_hours']

        # 賃金計算用の時間を計算
        total_minutes = stats['total_work_minutes']
        overtime_minutes = stats['overtime_work_minutes']
        weekend_minutes = stats['weekend_work_minutes']
        late_night_minutes = stats['late_night_work_minutes']

        # 重複を計算
        weekend_and_late_night_minutes = 0
        # 簡易的に推定（詳細データがない場合）
        # 実際には monthly_overtime_report.py から取得すべき
        # ここでは概算として深夜労働の30%が休日と重複すると仮定
        if weekend_minutes > 0 and late_night_minutes > 0:
            weekend_and_late_night_minutes = min(weekend_minutes, late_night_minutes * 0.3)

        # 純粋な時間を計算
        weekday_minutes = total_minutes - weekend_minutes
        weekend_only_minutes = weekend_minutes - weekend_and_late_night_minutes
        late_night_only_minutes = late_night_minutes - weekend_and_late_night_minutes

        # 倍率適用後の時間（分）
        weighted_minutes = (
            weekday_minutes * 1.25 +
            weekend_only_minutes * 1.5 +
            late_night_only_minutes * 1.35 +
            weekend_and_late_night_minutes * 1.6
        )

        # 時間単位に変換
        weighted_hours = weighted_minutes / 60

        # 賃金計算
        total_wage = weighted_hours * HOURLY_RATE

        # 月次詳細
        wage_report['monthly_details'][period_key] = {
            'period_start': stats.get('period_start'),
            'period_end': stats.get('period_end'),
            'total_commits': stats['total_commits'],
            'total_work_hours': round(total_work_hours, 2),
            'breakdown': {
                'weekday_hours': round(weekday_minutes / 60, 2),
                'weekend_only_hours': round(weekend_only_minutes / 60, 2),
                'late_night_only_hours': round(late_night_only_minutes / 60, 2),
                'weekend_and_late_night_hours': round(weekend_and_late_night_minutes / 60, 2)
            },
            'weighted_work_hours': round(weighted_hours, 2),
            'wage_calculation': {
                'weekday': {
                    'hours': round(weekday_minutes / 60, 2),
                    'rate': 1.25,
                    'weighted_hours': round(weekday_minutes * 1.25 / 60, 2),
                    'amount': round((weekday_minutes * 1.25 / 60) * HOURLY_RATE, 0)
                },
                'weekend_only': {
                    'hours': round(weekend_only_minutes / 60, 2),
                    'rate': 1.5,
                    'weighted_hours': round(weekend_only_minutes * 1.5 / 60, 2),
                    'amount': round((weekend_only_minutes * 1.5 / 60) * HOURLY_RATE, 0)
                },
                'late_night_only': {
                    'hours': round(late_night_only_minutes / 60, 2),
                    'rate': 1.35,
                    'weighted_hours': round(late_night_only_minutes * 1.35 / 60, 2),
                    'amount': round((late_night_only_minutes * 1.35 / 60) * HOURLY_RATE, 0)
                },
                'weekend_and_late_night': {
                    'hours': round(weekend_and_late_night_minutes / 60, 2),
                    'rate': 1.6,
                    'weighted_hours': round(weekend_and_late_night_minutes * 1.6 / 60, 2),
                    'amount': round((weekend_and_late_night_minutes * 1.6 / 60) * HOURLY_RATE, 0)
                }
            },
            'total_wage': round(total_wage, 0),
            'projects': stats.get('projects', [])
        }

        # 年次集計に追加
        yearly_stats[year]['total_work_hours'] += total_work_hours
        yearly_stats[year]['weighted_work_hours'] += weighted_hours
        yearly_stats[year]['total_wage'] += total_wage
        yearly_stats[year]['months'].append(period_key)

        # 総計に追加
        wage_report['grand_total']['total_work_hours'] += total_work_hours
        wage_report['grand_total']['weighted_work_hours'] += weighted_hours
        wage_report['grand_total']['total_wage'] += total_wage

    # 年次サマリー
    for year, stats in sorted(yearly_stats.items()):
        wage_report['yearly_summary'][year] = {
            'total_work_hours': round(stats['total_work_hours'], 2),
            'weighted_work_hours': round(stats['weighted_work_hours'], 2),
            'total_wage': round(stats['total_wage'], 0),
            'months_count': len(stats['months']),
            'months': stats['months']
        }

    # 総計を丸める
    wage_report['grand_total']['total_work_hours'] = round(
        wage_report['grand_total']['total_work_hours'], 2
    )
    wage_report['grand_total']['weighted_work_hours'] = round(
        wage_report['grand_total']['weighted_work_hours'], 2
    )
    wage_report['grand_total']['total_wage'] = round(
        wage_report['grand_total']['total_wage'], 0
    )

    return wage_report


def format_currency(amount: float) -> str:
    """金額をフォーマット"""
    return f"JPY {amount:,.0f}"


def save_wage_report_json(wage_report: Dict, output_file: str = 'wage_calculation_report.json'):
    """賃金計算レポートをJSONで保存"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(wage_report, f, ensure_ascii=False, indent=2)
    print(f"[OK] 賃金計算レポート保存: {output_file}")


def print_wage_report(wage_report: Dict):
    """賃金計算レポートを表示"""
    print("\n" + "=" * 80)
    print("時間外労働賃金計算レポート")
    print("=" * 80)
    print(f"作業単価: {format_currency(wage_report['hourly_rate'])}/時間")
    print(f"計算日時: {wage_report['calculation_date']}")
    print("=" * 80)

    # 月次詳細
    print("\n【月次詳細】")
    for period_key in sorted(wage_report['monthly_details'].keys()):
        details = wage_report['monthly_details'][period_key]

        print(f"\n■ {period_key} 期 ({details['period_start']} ～ {details['period_end']})")
        print(f"  コミット数: {details['total_commits']}件")
        print(f"  実作業時間: {details['total_work_hours']:.2f}時間")
        print(f"  ")
        print(f"  【内訳】")

        calc = details['wage_calculation']
        if calc['weekday']['hours'] > 0:
            print(f"    平日持ち帰り: {calc['weekday']['hours']:.2f}h × {calc['weekday']['rate']} "
                  f"= {calc['weekday']['weighted_hours']:.2f}h → {format_currency(calc['weekday']['amount'])}")

        if calc['weekend_only']['hours'] > 0:
            print(f"    休日労働: {calc['weekend_only']['hours']:.2f}h × {calc['weekend_only']['rate']} "
                  f"= {calc['weekend_only']['weighted_hours']:.2f}h → {format_currency(calc['weekend_only']['amount'])}")

        if calc['late_night_only']['hours'] > 0:
            print(f"    深夜労働: {calc['late_night_only']['hours']:.2f}h × {calc['late_night_only']['rate']} "
                  f"= {calc['late_night_only']['weighted_hours']:.2f}h → {format_currency(calc['late_night_only']['amount'])}")

        if calc['weekend_and_late_night']['hours'] > 0:
            print(f"    休日+深夜: {calc['weekend_and_late_night']['hours']:.2f}h × {calc['weekend_and_late_night']['rate']} "
                  f"= {calc['weekend_and_late_night']['weighted_hours']:.2f}h → {format_currency(calc['weekend_and_late_night']['amount'])}")

        print(f"  ")
        print(f"  賃金計算用時間: {details['weighted_work_hours']:.2f}時間")
        print(f"  【請求額】 {format_currency(details['total_wage'])}")

    # 年次サマリー
    print("\n" + "=" * 80)
    print("【年次サマリー】")
    for year in sorted(wage_report['yearly_summary'].keys()):
        summary = wage_report['yearly_summary'][year]
        print(f"\n■ {year}年")
        print(f"  対象月数: {summary['months_count']}ヶ月")
        print(f"  実作業時間: {summary['total_work_hours']:.2f}時間")
        print(f"  賃金計算用時間: {summary['weighted_work_hours']:.2f}時間")
        print(f"  【年間請求額】 {format_currency(summary['total_wage'])}")

    # 総計
    print("\n" + "=" * 80)
    print("【総計】")
    grand = wage_report['grand_total']
    print(f"  総実作業時間: {grand['total_work_hours']:.2f}時間")
    print(f"  賃金計算用時間: {grand['weighted_work_hours']:.2f}時間")
    print(f"  【総請求額】 {format_currency(grand['total_wage'])}")
    print("=" * 80)


def main():
    """メイン実行"""
    print("=" * 80)
    print("時間外労働賃金計算ツール")
    print("=" * 80)

    # 賃金計算
    wage_report = calculate_wage_report()

    # レポート表示
    print_wage_report(wage_report)

    # JSON保存
    save_wage_report_json(wage_report)

    print("\n[OK] 賃金計算完了")


if __name__ == '__main__':
    main()
