"""
遅延賦課金を含む賃金計算ツール

学習曲線を考慮した遅延賦課金計算:
- 2024年: 学習初期 → 補正係数 0.152 の逆補正 (約6.6倍)
- 2025年前半: 習熟期 → 部分的補正 (約3倍)
- 2025年後半: 習熟完了 → 補正なし (1.0倍)
"""
import json
from datetime import datetime, date
from typing import Dict, List
from collections import defaultdict


HOURLY_RATE = 2637  # 時間単価（円）


def load_monthly_overtime_data() -> Dict:
    """月次時間外労働データを読み込み"""
    # Load from wage calculation report which has weighted hours
    with open('wage_calculation_report.json', 'r', encoding='utf-8') as f:
        wage_data = json.load(f)

    # Also load monthly overtime for additional details
    with open('monthly_overtime_report.json', 'r', encoding='utf-8') as f:
        monthly_data = json.load(f)

    # Merge the data
    merged = {}
    for period_key, wage_info in wage_data.get('monthly_details', {}).items():
        if period_key in monthly_data:
            merged[period_key] = {
                **monthly_data[period_key],
                'wage_hours': wage_info.get('weighted_work_hours', 0),
                'wage_amount_base': wage_info.get('total_wage', 0)
            }

    return merged


def calculate_learning_curve_multiplier(period_key: str) -> float:
    """
    学習曲線に基づく遅延賦課金の乗数を計算

    Args:
        period_key: 期間キー（例: "2024-06"）

    Returns:
        遅延賦課金乗数（1.0 = 賦課金なし）
    """
    year, month = map(int, period_key.split('-'))

    # 2024年: 学習初期段階 → 6.6倍（補正係数の逆数）
    if year == 2024:
        return 6.58  # 1 / 0.152

    # 2025年1月～3月: 習熟期 → 3倍
    elif year == 2025 and month <= 3:
        return 3.0

    # 2025年4月～6月: 習熟後期 → 2倍
    elif year == 2025 and 4 <= month <= 6:
        return 2.0

    # 2025年7月～: 習熟完了 → 1.5倍（慣れの影響は小さい）
    else:
        return 1.5


def calculate_delay_penalty_hours(actual_hours: float, period_key: str) -> Dict:
    """
    遅延賦課金による追加時間を計算

    Args:
        actual_hours: 実作業時間
        period_key: 期間キー

    Returns:
        {
            'multiplier': 乗数,
            'penalty_hours': 賦課金追加時間,
            'total_hours': 合計時間
        }
    """
    multiplier = calculate_learning_curve_multiplier(period_key)
    penalty_hours = actual_hours * (multiplier - 1.0)  # 追加分のみ
    total_hours = actual_hours * multiplier

    return {
        'multiplier': multiplier,
        'penalty_hours': penalty_hours,
        'total_hours': total_hours
    }


def calculate_monthly_wages_with_penalty(monthly_data: Dict) -> Dict:
    """月次賃金計算（遅延賦課金込み）"""
    monthly_results = {}
    yearly_summary = defaultdict(lambda: {
        'months': 0,
        'actual_hours': 0,
        'penalty_hours': 0,
        'total_hours': 0,
        'wage_hours': 0,
        'wage_amount': 0
    })

    grand_total = {
        'actual_hours': 0,
        'penalty_hours': 0,
        'total_hours': 0,
        'wage_hours': 0,
        'wage_amount': 0
    }

    for period_key, data in monthly_data.items():
        if period_key == 'summary':
            continue

        year = period_key[:4]

        # 実作業時間（分 → 時間）
        actual_minutes = data.get('total_work_minutes', 0)
        actual_hours = actual_minutes / 60

        # 遅延賦課金計算
        penalty_info = calculate_delay_penalty_hours(actual_hours, period_key)

        # 賃金計算用時間（倍率適用後）- from wage_calculation_report
        wage_hours = data.get('wage_hours', 0)

        # 遅延賦課金を賃金計算用時間にも適用
        wage_with_penalty = wage_hours * penalty_info['multiplier']

        # 金額計算
        wage_amount = wage_with_penalty * HOURLY_RATE

        monthly_results[period_key] = {
            'period': f"{data.get('period_start', '')} ~ {data.get('period_end', '')}",
            'commits': data.get('total_commits', 0),
            'actual_hours': actual_hours,
            'penalty_multiplier': penalty_info['multiplier'],
            'penalty_hours': penalty_info['penalty_hours'],
            'total_hours_with_penalty': penalty_info['total_hours'],
            'wage_hours_base': wage_hours,
            'wage_hours_with_penalty': wage_with_penalty,
            'wage_amount': int(wage_amount),
            'breakdown': data.get('breakdown', {})
        }

        # 年次集計
        yearly_summary[year]['months'] += 1
        yearly_summary[year]['actual_hours'] += actual_hours
        yearly_summary[year]['penalty_hours'] += penalty_info['penalty_hours']
        yearly_summary[year]['total_hours'] += penalty_info['total_hours']
        yearly_summary[year]['wage_hours'] += wage_with_penalty
        yearly_summary[year]['wage_amount'] += int(wage_amount)

        # 総計
        grand_total['actual_hours'] += actual_hours
        grand_total['penalty_hours'] += penalty_info['penalty_hours']
        grand_total['total_hours'] += penalty_info['total_hours']
        grand_total['wage_hours'] += wage_with_penalty
        grand_total['wage_amount'] += int(wage_amount)

    return {
        'monthly': monthly_results,
        'yearly': dict(yearly_summary),
        'grand_total': grand_total
    }


def format_currency(amount: int) -> str:
    """通貨フォーマット（JPY表記）"""
    return f"JPY {amount:,}"


def generate_report():
    """遅延賦課金込み賃金レポート生成"""
    print("=" * 80)
    print("時間外労働賃金計算ツール（遅延賦課金込み）")
    print("=" * 80)

    # データ読み込み
    monthly_data = load_monthly_overtime_data()

    # 賃金計算
    results = calculate_monthly_wages_with_penalty(monthly_data)

    # レポート出力
    print("\n" + "=" * 80)
    print("時間外労働賃金計算レポート（遅延賦課金込み）")
    print("=" * 80)
    print(f"作業単価: {format_currency(HOURLY_RATE)}/時間")
    print(f"計算日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 月次詳細
    print("\n【月次詳細】\n")
    for period_key in sorted(results['monthly'].keys()):
        data = results['monthly'][period_key]

        print(f"■ {period_key} 月 ({data['period']})")
        print(f"  コミット数: {data['commits']}件")
        print(f"  実作業時間: {data['actual_hours']:.2f}時間")
        print(f"  遅延賦課金乗数: ×{data['penalty_multiplier']:.2f}")
        print(f"  遅延賦課金追加時間: +{data['penalty_hours']:.2f}時間")
        print(f"  合計作業時間: {data['total_hours_with_penalty']:.2f}時間")
        print(f"  ")
        print(f"  【賃金計算】")
        print(f"    基本賃金計算用時間: {data['wage_hours_base']:.2f}時間（倍率適用後）")
        print(f"    遅延賦課金適用後: {data['wage_hours_with_penalty']:.2f}時間")
        print(f"    【月次請求額】 {format_currency(data['wage_amount'])}")
        print()

    # 年次サマリー
    print("\n" + "=" * 80)
    print("【年次サマリー】")
    print("=" * 80 + "\n")

    for year in sorted(results['yearly'].keys()):
        data = results['yearly'][year]
        print(f"■ {year}年")
        print(f"  対象期間: {data['months']}ヶ月")
        print(f"  実作業時間: {data['actual_hours']:.2f}時間")
        print(f"  遅延賦課金追加時間: +{data['penalty_hours']:.2f}時間")
        print(f"  合計作業時間: {data['total_hours']:.2f}時間")
        print(f"  賃金計算用時間: {data['wage_hours']:.2f}時間")
        print(f"  【年間請求額】 {format_currency(data['wage_amount'])}")
        print()

    # 総計
    print("=" * 80)
    print("【総計】")
    print("=" * 80)
    total = results['grand_total']
    print(f"  総実作業時間: {total['actual_hours']:.2f}時間")
    print(f"  遅延賦課金追加時間: +{total['penalty_hours']:.2f}時間")
    print(f"  合計作業時間: {total['total_hours']:.2f}時間")
    print(f"  賃金計算用時間: {total['wage_hours']:.2f}時間（時間外倍率+遅延賦課金適用後）")
    print(f"  ")
    print(f"  【総請求額】 {format_currency(total['wage_amount'])}")
    print("=" * 80)

    # JSON保存
    output_data = {
        'calculation_date': datetime.now().isoformat(),
        'hourly_rate': HOURLY_RATE,
        'methodology': {
            'learning_curve': {
                '2024': 6.58,
                '2025-Q1': 3.0,
                '2025-Q2': 2.0,
                '2025-Q3+': 1.5
            },
            'description': '学習曲線に基づく遅延賦課金: 初期は慣れない分の追加工数を考慮'
        },
        'monthly_details': results['monthly'],
        'yearly_summary': results['yearly'],
        'grand_total': results['grand_total']
    }

    with open('wage_calculation_with_delay_penalty.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n[OK] 詳細レポート保存: wage_calculation_with_delay_penalty.json")

    return results


def main():
    """メイン実行"""
    results = generate_report()
    print("\n[OK] 賃金計算完了")
    return results


if __name__ == '__main__':
    main()
