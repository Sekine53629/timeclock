"""
実打刻記録から作業時間を再推定
上限値適応コミットを除外し、実績データから推定ロジックを作成
"""
import json
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple


def load_timeclock_records() -> Dict:
    """実打刻記録を読み込み"""
    with open('json/timeclock_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['accounts']['0053629']['records']


def load_github_commits() -> List[Dict]:
    """GitHubコミット履歴を読み込み（上限値適応を除外）"""
    commits = []

    with open('git_analyzer/github_commits_evidence.csv', 'r', encoding='shift_jis') as f:
        reader = csv.DictReader(f)
        for row in reader:
            estimated_minutes = float(row['推定作業時間（分）'])

            # 480分（上限値）に達しているコミットを除外
            if estimated_minutes >= 480:
                continue

            commits.append({
                'date': row['日付'],
                'repo': row['プロジェクト名'],
                'message': row['作業内容'],
                'files_changed': int(row['変更ファイル数']),
                'lines_added': int(row['追加行数']),
                'lines_deleted': int(row['削除行数']),
                'estimated_minutes': estimated_minutes,
                'is_overtime': row['時間外'] == '○',
                'is_weekend': row['休日'] == '○',
                'is_late_night': row['深夜'] == '○'
            })

    return commits


def match_timeclock_to_commits(timeclock_records: List[Dict], commits: List[Dict]) -> Dict:
    """
    実打刻記録とコミットをマッチング

    Returns:
        date -> {
            'actual_minutes': 実作業時間,
            'commits': マッチしたコミットリスト
        }
    """
    # 打刻記録を日付別に集計
    timeclock_by_date = defaultdict(lambda: {'actual_minutes': 0, 'sessions': []})
    for record in timeclock_records:
        record_date = record['date']
        timeclock_by_date[record_date]['actual_minutes'] += record['total_minutes']
        timeclock_by_date[record_date]['sessions'].append(record)

    # コミットを日付別に集計
    commits_by_date = defaultdict(list)
    for commit in commits:
        commits_by_date[commit['date']].append(commit)

    # マッチング
    matched = {}
    for date_str in timeclock_by_date.keys():
        if date_str in commits_by_date:
            matched[date_str] = {
                'actual_minutes': timeclock_by_date[date_str]['actual_minutes'],
                'commits': commits_by_date[date_str],
                'sessions': timeclock_by_date[date_str]['sessions']
            }

    return matched


def analyze_actual_vs_estimated(matched_data: Dict):
    """実績と推定の比較分析"""
    print("=" * 80)
    print("実打刻記録とGitHub推定値の比較分析")
    print("=" * 80)
    print("\n【上限値480分コミットを除外済み】\n")

    total_actual = 0
    total_estimated = 0

    for date_str in sorted(matched_data.keys()):
        data = matched_data[date_str]
        actual_mins = data['actual_minutes']
        commits = data['commits']

        # その日のコミットの推定時間合計
        estimated_mins = sum(c['estimated_minutes'] for c in commits)

        # 変更量の合計
        total_files = sum(c['files_changed'] for c in commits)
        total_lines_added = sum(c['lines_added'] for c in commits)
        total_lines_deleted = sum(c['lines_deleted'] for c in commits)

        print(f"\n{date_str}")
        print(f"  実作業時間: {actual_mins}分 ({actual_mins/60:.1f}時間)")
        print(f"  推定時間: {estimated_mins:.1f}分 ({estimated_mins/60:.1f}時間)")
        print(f"  差異: {actual_mins - estimated_mins:.1f}分")
        print(f"  精度: {(estimated_mins/actual_mins*100) if actual_mins > 0 else 0:.1f}%")
        print(f"  コミット数: {len(commits)}件")
        print(f"  変更: {total_files}ファイル, +{total_lines_added}/-{total_lines_deleted}行")

        total_actual += actual_mins
        total_estimated += estimated_mins

    print("\n" + "=" * 80)
    print("【総計】")
    print(f"  マッチした日数: {len(matched_data)}日")
    print(f"  実作業時間合計: {total_actual}分 ({total_actual/60:.1f}時間)")
    print(f"  推定時間合計: {total_estimated:.1f}分 ({total_estimated/60:.1f}時間)")
    print(f"  差異: {total_actual - total_estimated:.1f}分")
    print(f"  全体精度: {(total_estimated/total_actual*100) if total_actual > 0 else 0:.1f}%")
    print("=" * 80)

    return total_actual, total_estimated


def create_improved_estimation_model(matched_data: Dict) -> Dict:
    """
    実績データから改善された推定モデルを作成

    Returns:
        補正係数など
    """
    total_actual = 0
    total_estimated = 0

    for date_str, data in matched_data.items():
        actual_mins = data['actual_minutes']
        commits = data['commits']
        estimated_mins = sum(c['estimated_minutes'] for c in commits)

        total_actual += actual_mins
        total_estimated += estimated_mins

    # 補正係数を計算
    if total_estimated > 0:
        correction_factor = total_actual / total_estimated
    else:
        correction_factor = 1.0

    print(f"\n【改善された推定モデル】")
    print(f"  補正係数: {correction_factor:.3f}")
    print(f"  使用方法: 推定時間 × {correction_factor:.3f} = 実作業時間（予測）")

    return {
        'correction_factor': correction_factor,
        'sample_days': len(matched_data),
        'total_actual_minutes': total_actual,
        'total_estimated_minutes': total_estimated
    }


def apply_correction_to_all_commits(commits: List[Dict], correction_factor: float) -> List[Dict]:
    """全コミットに補正係数を適用"""
    corrected_commits = []

    for commit in commits:
        corrected_commit = commit.copy()
        corrected_commit['original_estimated_minutes'] = commit['estimated_minutes']
        corrected_commit['corrected_estimated_minutes'] = commit['estimated_minutes'] * correction_factor
        corrected_commits.append(corrected_commit)

    return corrected_commits


def save_corrected_csv(commits: List[Dict], output_file: str):
    """補正後のCSVを保存"""
    fieldnames = [
        '日付', 'プロジェクト名', '作業内容',
        '変更ファイル数', '追加行数', '削除行数',
        '元推定時間（分）', '補正後推定時間（分）',
        '時間外', '休日', '深夜'
    ]

    with open(output_file, 'w', encoding='shift_jis', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for commit in commits:
            writer.writerow({
                '日付': commit['date'],
                'プロジェクト名': commit['repo'],
                '作業内容': commit['message'][:100],
                '変更ファイル数': commit['files_changed'],
                '追加行数': commit['lines_added'],
                '削除行数': commit['lines_deleted'],
                '元推定時間（分）': f"{commit['original_estimated_minutes']:.1f}",
                '補正後推定時間（分）': f"{commit['corrected_estimated_minutes']:.1f}",
                '時間外': '○' if commit['is_overtime'] else '',
                '休日': '○' if commit['is_weekend'] else '',
                '深夜': '○' if commit['is_late_night'] else ''
            })

    print(f"\n[OK] 補正後CSVを保存: {output_file}")


def main():
    """メイン実行"""
    print("=" * 80)
    print("実打刻記録ベースの作業時間再推定ツール")
    print("=" * 80)

    # 1. データ読み込み
    print("\n[1] データ読み込み中...")
    timeclock_records = load_timeclock_records()
    commits = load_github_commits()

    print(f"  実打刻記録: {len(timeclock_records)}件")
    print(f"  GitHubコミット（上限値除外後）: {len(commits)}件")

    # 2. マッチング
    print("\n[2] 実打刻記録とコミットのマッチング...")
    matched_data = match_timeclock_to_commits(timeclock_records, commits)
    print(f"  マッチした日数: {len(matched_data)}日")

    # 3. 比較分析
    print("\n[3] 実績と推定の比較分析...")
    total_actual, total_estimated = analyze_actual_vs_estimated(matched_data)

    # 4. 改善モデル作成
    print("\n[4] 改善された推定モデルを作成...")
    model = create_improved_estimation_model(matched_data)

    # 5. 全コミットに補正適用
    print("\n[5] 全コミットに補正係数を適用...")

    # 上限値コミットを含む全コミットを再読込
    all_commits = []
    with open('git_analyzer/github_commits_evidence.csv', 'r', encoding='shift_jis') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_commits.append({
                'date': row['日付'],
                'repo': row['プロジェクト名'],
                'message': row['作業内容'],
                'files_changed': int(row['変更ファイル数']),
                'lines_added': int(row['追加行数']),
                'lines_deleted': int(row['削除行数']),
                'estimated_minutes': float(row['推定作業時間（分）']),
                'is_overtime': row['時間外'] == '○',
                'is_weekend': row['休日'] == '○',
                'is_late_night': row['深夜'] == '○'
            })

    print(f"  全コミット数: {len(all_commits)}件")

    corrected_commits = apply_correction_to_all_commits(all_commits, model['correction_factor'])

    # 統計情報
    total_original = sum(c['original_estimated_minutes'] for c in corrected_commits)
    total_corrected = sum(c['corrected_estimated_minutes'] for c in corrected_commits)

    print(f"\n  元推定時間合計: {total_original:.1f}分 ({total_original/60:.1f}時間)")
    print(f"  補正後推定時間合計: {total_corrected:.1f}分 ({total_corrected/60:.1f}時間)")
    print(f"  差異: {total_corrected - total_original:.1f}分 ({(total_corrected - total_original)/60:.1f}時間)")

    # 6. 補正後CSVを保存
    print("\n[6] 補正後データを保存...")
    save_corrected_csv(corrected_commits, 'git_analyzer/github_commits_corrected.csv')

    # モデル情報を保存
    with open('git_analyzer/correction_model.json', 'w', encoding='utf-8') as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    print("\n[OK] 処理完了")


if __name__ == '__main__':
    main()
