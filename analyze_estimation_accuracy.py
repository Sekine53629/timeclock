"""
作業時間推定の精度分析ツール
GitHubコミット履歴から推定した時間とタイムクロック記録を比較
"""
import json
from datetime import datetime
from collections import defaultdict


def analyze_estimation_accuracy():
    """推定精度を分析"""

    # GitHubコミットデータを読み込み
    with open('git_analyzer/github_commits_evidence.json', 'r', encoding='utf-8') as f:
        github_data = json.load(f)

    # 日付・プロジェクトごとにグループ化
    grouped = defaultdict(lambda: {
        'commits': [],
        'total_estimated_minutes': 0,
        'files_changed': 0,
        'lines_added': 0,
        'lines_deleted': 0
    })

    for commit in github_data:
        date = commit['date']
        project = commit['repo_name']
        key = f"{date}_{project}"

        grouped[key]['commits'].append(commit)
        grouped[key]['total_estimated_minutes'] += commit['estimated_work_minutes']
        grouped[key]['files_changed'] += commit['files_changed']
        grouped[key]['lines_added'] += commit['lines_added']
        grouped[key]['lines_deleted'] += commit['lines_deleted']

    # 統計情報
    print("=" * 80)
    print("作業時間推定精度分析")
    print("=" * 80)

    # 推定時間の分布
    all_estimates = [commit['estimated_work_minutes'] for commit in github_data]

    print(f"\n総コミット数: {len(github_data)}")
    print(f"総推定時間: {sum(all_estimates):.1f}分 ({sum(all_estimates)/60:.1f}時間)")
    print(f"平均推定時間: {sum(all_estimates)/len(all_estimates):.1f}分/コミット")
    print(f"最小推定時間: {min(all_estimates):.1f}分")
    print(f"最大推定時間: {max(all_estimates):.1f}分")

    # 480分（上限）に達したコミット数
    max_limit_commits = [c for c in github_data if c['estimated_work_minutes'] == 480]
    print(f"\n上限480分に達したコミット: {len(max_limit_commits)}件 ({len(max_limit_commits)/len(github_data)*100:.1f}%)")

    if max_limit_commits:
        print("\n【上限到達コミットの詳細】")
        for commit in max_limit_commits[:10]:  # 最初の10件
            print(f"  {commit['date']} - {commit['repo_name']}")
            print(f"    {commit['files_changed']}ファイル, +{commit['lines_added']}/-{commit['lines_deleted']}行")
            print(f"    {commit['message'][:60]}...")

    # 推定時間の範囲別分布
    ranges = {
        '5-30分': 0,
        '30-60分': 0,
        '1-2時間': 0,
        '2-4時間': 0,
        '4-8時間': 0,
        '8時間（上限）': 0
    }

    for est in all_estimates:
        if est <= 30:
            ranges['5-30分'] += 1
        elif est <= 60:
            ranges['30-60分'] += 1
        elif est <= 120:
            ranges['1-2時間'] += 1
        elif est <= 240:
            ranges['2-4時間'] += 1
        elif est < 480:
            ranges['4-8時間'] += 1
        else:
            ranges['8時間（上限）'] += 1

    print("\n【推定時間の分布】")
    for range_name, count in ranges.items():
        percentage = count / len(all_estimates) * 100
        print(f"  {range_name}: {count}件 ({percentage:.1f}%)")

    # コード変更量と推定時間の関係
    print("\n【大規模変更の推定時間】")
    large_changes = sorted(
        github_data,
        key=lambda x: x['lines_added'] + x['lines_deleted'],
        reverse=True
    )[:15]

    for commit in large_changes:
        total_lines = commit['lines_added'] + commit['lines_deleted']
        print(f"\n  {commit['date']} - {commit['repo_name']}")
        print(f"    変更: {commit['files_changed']}ファイル, {total_lines}行")
        print(f"    推定時間: {commit['estimated_work_minutes']:.1f}分 ({commit['estimated_work_minutes']/60:.1f}時間)")

        # 理論的推定（上限なし）
        theoretical = estimate_without_limit(
            commit['lines_added'],
            commit['lines_deleted'],
            commit['files_changed']
        )
        if theoretical != commit['estimated_work_minutes']:
            print(f"    理論値: {theoretical:.1f}分 ({theoretical/60:.1f}時間) → 上限適用で{theoretical - commit['estimated_work_minutes']:.1f}分削減")


def estimate_without_limit(lines_added, lines_deleted, files_changed):
    """上限なしの理論的推定時間"""
    add_time = (lines_added / 10) * 5
    delete_time = (lines_deleted / 10) * 2

    if files_changed > 0:
        file_time = 10 + (files_changed - 1) * 5
    else:
        file_time = 0

    total_time = max(add_time + delete_time + file_time, 5)
    return total_time


def main():
    """メイン実行"""
    analyze_estimation_accuracy()


if __name__ == '__main__':
    main()
