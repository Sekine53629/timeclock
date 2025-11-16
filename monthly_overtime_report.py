"""
月次時間外労働レポート生成ツール
16日～翌月15日の期間で集計
"""
import json
from datetime import datetime, date
from collections import defaultdict
from typing import Dict, List


def get_billing_period(target_date: date) -> tuple:
    """
    指定日が属する締め期間を取得（16日～翌月15日）

    Args:
        target_date: 対象日

    Returns:
        (period_key, start_date, end_date) のタプル
        period_key: "YYYY-MM" 形式（開始月）
    """
    if target_date.day >= 16:
        # 16日以降 → 当月16日～翌月15日
        period_key = target_date.strftime('%Y-%m')
        start_date = date(target_date.year, target_date.month, 16)

        # 翌月の15日を計算
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 15)
        else:
            end_date = date(target_date.year, target_date.month + 1, 15)
    else:
        # 15日以前 → 前月16日～当月15日
        if target_date.month == 1:
            period_key = f"{target_date.year - 1}-12"
            start_date = date(target_date.year - 1, 12, 16)
        else:
            prev_month = target_date.month - 1
            period_key = f"{target_date.year}-{prev_month:02d}"
            start_date = date(target_date.year, prev_month, 16)

        end_date = date(target_date.year, target_date.month, 15)

    return period_key, start_date, end_date


def analyze_monthly_overtime(csv_file: str, exclude_patterns: List[str] = None) -> Dict:
    """
    CSVファイルから月次時間外労働時間を集計

    Args:
        csv_file: github_commits_evidence.csv
        exclude_patterns: 除外するプロジェクト名のパターンリスト

    Returns:
        月次集計データ
    """
    import csv

    if exclude_patterns is None:
        exclude_patterns = []

    monthly_stats = defaultdict(lambda: {
        'total_commits': 0,
        'overtime_commits': 0,
        'weekend_commits': 0,
        'late_night_commits': 0,
        'total_work_minutes': 0,
        'overtime_work_minutes': 0,
        'weekend_work_minutes': 0,
        'late_night_work_minutes': 0,
        'weekend_and_late_night_minutes': 0,  # 休日かつ深夜（重複）
        'weighted_work_minutes': 0,  # 賃金計算用（倍率適用後）
        'projects': set(),
        'excluded_commits': 0,
        'period_start': None,
        'period_end': None
    })

    excluded_total = 0

    try:
        with open(csv_file, 'r', encoding='shift_jis') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    commit_date = datetime.strptime(row['日付'], '%Y-%m-%d').date()
                    work_minutes = float(row['推定作業時間（分）']) if row['推定作業時間（分）'] else 0
                    is_overtime = row['時間外'] == '○'
                    is_weekend = row['休日'] == '○'
                    is_late_night = row['深夜'] == '○'
                    project = row['プロジェクト名']

                    # 除外パターンチェック
                    should_exclude = any(pattern.lower() in project.lower() for pattern in exclude_patterns)
                    if should_exclude:
                        excluded_total += 1
                        # 締め期間を取得して除外カウントのみ記録
                        period_key, start_date, end_date = get_billing_period(commit_date)
                        monthly_stats[period_key]['excluded_commits'] += 1
                        continue

                    # 締め期間を取得
                    period_key, start_date, end_date = get_billing_period(commit_date)

                    # 統計を更新
                    stats = monthly_stats[period_key]
                    stats['total_commits'] += 1
                    stats['total_work_minutes'] += work_minutes
                    stats['projects'].add(project)
                    stats['period_start'] = start_date
                    stats['period_end'] = end_date

                    # 持ち帰り労働なので、全ての作業時間が時間外労働
                    stats['overtime_commits'] += 1
                    stats['overtime_work_minutes'] += work_minutes

                    # 賃金計算用の倍率計算（重複を考慮）
                    # 基本: 時間外 1.25倍
                    multiplier = 1.25

                    if is_weekend:
                        stats['weekend_commits'] += 1
                        stats['weekend_work_minutes'] += work_minutes
                        multiplier += 0.25  # 休日加算

                    if is_late_night:
                        stats['late_night_commits'] += 1
                        stats['late_night_work_minutes'] += work_minutes
                        multiplier += 0.1  # 深夜加算

                    # 休日かつ深夜の重複をカウント
                    if is_weekend and is_late_night:
                        stats['weekend_and_late_night_minutes'] += work_minutes

                    # 倍率適用後の時間を計算
                    stats['weighted_work_minutes'] += work_minutes * multiplier

                except Exception as e:
                    print(f"行の解析エラー: {e}")
                    continue

    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")
        raise

    # set を list に変換
    for period_key in monthly_stats:
        monthly_stats[period_key]['projects'] = list(monthly_stats[period_key]['projects'])

    return dict(monthly_stats)


def format_hours(minutes: float) -> str:
    """分を時間形式に変換"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}時間{mins:02d}分"


def print_monthly_report(monthly_stats: Dict, exclude_patterns: List[str] = None):
    """月次レポートを表示"""
    print("\n" + "=" * 80)
    print("月次時間外労働レポート（16日～翌月15日締め）")
    if exclude_patterns:
        print(f"除外パターン: {', '.join(exclude_patterns)}")
    print("=" * 80)

    # 期間でソート
    sorted_periods = sorted(monthly_stats.keys())

    total_overtime_minutes = 0
    total_commits = 0

    for period_key in sorted_periods:
        stats = monthly_stats[period_key]

        print(f"\n【{period_key} 期】")
        # 純粋な平日・休日・深夜の時間を計算（重複除外）
        weekday_only_minutes = stats['total_work_minutes'] - stats['weekend_work_minutes']
        weekend_only_minutes = stats['weekend_work_minutes'] - stats['weekend_and_late_night_minutes']
        late_night_only_minutes = stats['late_night_work_minutes'] - stats['weekend_and_late_night_minutes']
        both_minutes = stats['weekend_and_late_night_minutes']

        print(f"  期間: {stats['period_start']} ～ {stats['period_end']}")
        print(f"  総コミット数: {stats['total_commits']}件")
        print(f"  総作業時間: {format_hours(stats['total_work_minutes'])}")
        print(f"  ")
        print(f"  【時間外労働内訳】")
        print(f"    └ 平日持ち帰り: {stats['overtime_commits'] - stats['weekend_commits']}件 ({format_hours(weekday_only_minutes)}) [×1.25]")
        print(f"    └ 休日労働: {stats['weekend_commits']}件 ({format_hours(stats['weekend_work_minutes'])}) [×1.5] ★")
        if both_minutes > 0:
            print(f"       ├ 休日のみ: {format_hours(weekend_only_minutes)}")
            print(f"       └ 休日+深夜: {format_hours(both_minutes)} [×1.6]")
        print(f"    └ 深夜労働: {stats['late_night_commits']}件 ({format_hours(stats['late_night_work_minutes'])}) [×1.35] ★")
        if both_minutes > 0:
            print(f"       ├ 深夜のみ: {format_hours(late_night_only_minutes)}")
            print(f"       └ 休日+深夜: {format_hours(both_minutes)} (上記)")
        print(f"  ")
        print(f"  【賃金計算用時間】 {format_hours(stats['weighted_work_minutes'])} (倍率適用後)")
        print(f"  プロジェクト数: {len(stats['projects'])}個")
        if stats['excluded_commits'] > 0:
            print(f"  除外コミット数: {stats['excluded_commits']}件")

        total_overtime_minutes += stats['overtime_work_minutes']
        total_commits += stats['total_commits']

    # 総計の計算
    total_weekend_minutes = sum(stats['weekend_work_minutes'] for stats in monthly_stats.values())
    total_late_night_minutes = sum(stats['late_night_work_minutes'] for stats in monthly_stats.values())
    total_weekend_commits = sum(stats['weekend_commits'] for stats in monthly_stats.values())
    total_late_night_commits = sum(stats['late_night_commits'] for stats in monthly_stats.values())
    total_weighted_minutes = sum(stats['weighted_work_minutes'] for stats in monthly_stats.values())
    total_both_minutes = sum(stats['weekend_and_late_night_minutes'] for stats in monthly_stats.values())

    # 純粋な平日・休日・深夜の時間
    total_weekday_minutes = total_overtime_minutes - total_weekend_minutes
    total_weekend_only_minutes = total_weekend_minutes - total_both_minutes
    total_late_night_only_minutes = total_late_night_minutes - total_both_minutes

    print("\n" + "=" * 80)
    print("【総計】")
    print(f"  総コミット数: {total_commits}件")
    print(f"  総作業時間: {format_hours(total_overtime_minutes)}")
    print(f"")
    print(f"  【時間外労働内訳】")
    print(f"    └ 平日持ち帰り: {total_commits - total_weekend_commits}件")
    print(f"       {format_hours(total_weekday_minutes)} × 1.25 = {format_hours(total_weekday_minutes * 1.25)}")
    print(f"    └ 休日労働: {total_weekend_commits}件")
    print(f"       休日のみ: {format_hours(total_weekend_only_minutes)} × 1.5 = {format_hours(total_weekend_only_minutes * 1.5)}")
    print(f"       休日+深夜: {format_hours(total_both_minutes)} × 1.6 = {format_hours(total_both_minutes * 1.6)}")
    print(f"    └ 深夜労働: {total_late_night_commits}件")
    print(f"       深夜のみ: {format_hours(total_late_night_only_minutes)} × 1.35 = {format_hours(total_late_night_only_minutes * 1.35)}")
    print(f"       休日+深夜: {format_hours(total_both_minutes)} (上記に含む)")
    print(f"")
    print(f"  【賃金計算用時間（倍率適用後）】")
    print(f"    合計: {format_hours(total_weighted_minutes)}")
    print(f"")
    print(f"  ★ 時間外 1.25倍、休日 1.5倍、深夜 1.35倍、休日+深夜 1.6倍")
    print("=" * 80)


def save_monthly_report(monthly_stats: Dict, output_file: str = 'monthly_overtime_report.json'):
    """月次レポートをJSONで保存"""

    # date オブジェクトを文字列に変換
    serializable_stats = {}
    for period_key, stats in monthly_stats.items():
        serializable_stats[period_key] = {
            'period_start': stats['period_start'].isoformat() if stats['period_start'] else None,
            'period_end': stats['period_end'].isoformat() if stats['period_end'] else None,
            'total_commits': stats['total_commits'],
            'overtime_commits': stats['overtime_commits'],
            'weekend_commits': stats['weekend_commits'],
            'late_night_commits': stats['late_night_commits'],
            'total_work_minutes': stats['total_work_minutes'],
            'overtime_work_minutes': stats['overtime_work_minutes'],
            'weekend_work_minutes': stats['weekend_work_minutes'],
            'late_night_work_minutes': stats['late_night_work_minutes'],
            'total_work_hours': round(stats['total_work_minutes'] / 60, 2),
            'overtime_work_hours': round(stats['overtime_work_minutes'] / 60, 2),
            'projects': stats['projects']
        }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_stats, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] レポート保存: {output_file}")


def main():
    """メイン実行"""
    import sys

    csv_file = 'git_analyzer/github_commits_evidence.csv'

    # 除外パターン（practice, kadaiを除外）
    exclude_patterns = ['practice', 'kadai']

    # コマンドライン引数で除外なしを指定可能
    if '--no-exclude' in sys.argv:
        exclude_patterns = []

    print("=" * 80)
    print("月次時間外労働レポート生成ツール")
    print("=" * 80)
    print(f"\nCSVファイル: {csv_file}")
    if exclude_patterns:
        print(f"除外パターン: {', '.join(exclude_patterns)}")
        print("  (除外なしで実行する場合: --no-exclude オプションを使用)")

    # 月次集計を実行
    monthly_stats = analyze_monthly_overtime(csv_file, exclude_patterns)

    # レポート表示
    print_monthly_report(monthly_stats, exclude_patterns)

    # JSON保存
    save_monthly_report(monthly_stats)

    print("\n[OK] レポート生成完了")


if __name__ == '__main__':
    main()
