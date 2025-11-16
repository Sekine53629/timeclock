#!/usr/bin/env python3
"""
Gitログから不足している打刻実績を抽出するスクリプト
"""
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set

def load_current_records(data_path: str) -> Set[str]:
    """現在の打刻実績から日付一覧を取得"""
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    dates = set()
    if '0053629' in data.get('accounts', {}):
        records = data['accounts']['0053629'].get('records', [])
        for record in records:
            date = record.get('date')
            if date:
                dates.add(date)

    return dates

def load_git_commits(gitlog_path: str) -> Dict[str, List[dict]]:
    """Gitログからコミット履歴を日付ごとに集計"""
    with open(gitlog_path, 'r', encoding='utf-8') as f:
        commits = json.load(f)

    daily_commits = defaultdict(list)

    for commit in commits:
        # author_dateをパース (例: "2025-09-03 13:18:22 +0900")
        author_date = commit['author_date']
        # +0900の部分を除去してパース
        date_str = author_date.rsplit(' ', 1)[0]
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        date = dt.strftime('%Y-%m-%d')

        daily_commits[date].append({
            'time': dt.strftime('%H:%M:%S'),
            'repo': commit['repo_path'].split('/')[-1],
            'subject': commit['subject'],
            'hash': commit['commit_hash'][:7]
        })

    return dict(daily_commits)

def find_missing_dates(current_dates: Set[str], git_dates: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """不足している日付を特定"""
    missing = {}

    for date, commits in sorted(git_dates.items()):
        if date not in current_dates:
            missing[date] = commits

    return missing

def main():
    # ファイルパス
    timeclock_data_path = 'json/timeclock_data.json'
    gitlog_path = '/Users/yoshipc/Desktop/gitlogs_out/combined_gitlog.json'

    print("=" * 80)
    print("不足している打刻実績の抽出")
    print("=" * 80)

    # 現在の打刻実績を読み込み
    current_dates = load_current_records(timeclock_data_path)
    print(f"\n現在の打刻実績: {len(current_dates)}日分")
    print(f"日付範囲: {min(current_dates) if current_dates else 'なし'} ～ {max(current_dates) if current_dates else 'なし'}")

    # Gitログを読み込み
    git_commits = load_git_commits(gitlog_path)
    print(f"\nGitログ: {len(git_commits)}日分")
    print(f"日付範囲: {min(git_commits.keys())} ～ {max(git_commits.keys())}")

    # 不足している日付を特定
    missing = find_missing_dates(current_dates, git_commits)

    if missing:
        print(f"\n【不足している日付: {len(missing)}日】")
        print("=" * 80)

        for date in sorted(missing.keys()):
            commits = missing[date]
            dt = datetime.strptime(date, '%Y-%m-%d')
            weekday = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]
            is_sunday = (dt.weekday() == 6)

            print(f"\n{date} ({weekday}){' ★日曜日' if is_sunday else ''}")
            print(f"  コミット数: {len(commits)}")

            # 最初と最後のコミット時刻を表示
            times = [c['time'] for c in commits]
            print(f"  作業時間帯: {min(times)} ～ {max(times)}")

            # リポジトリ別に集計
            repos = defaultdict(int)
            for c in commits:
                repos[c['repo']] += 1

            print(f"  主なリポジトリ:")
            for repo, count in sorted(repos.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"    - {repo}: {count}件")

            # 主なコミットメッセージ
            print(f"  主なコミット:")
            for c in commits[:5]:
                print(f"    {c['time']} [{c['repo']}] {c['subject'][:50]}")

            if len(commits) > 5:
                print(f"    ... 他 {len(commits) - 5} 件")

        # サマリー出力（確認用）
        print("\n" + "=" * 80)
        print("【インポート候補サマリー】")
        print("=" * 80)

        # 月別に集計
        monthly = defaultdict(list)
        for date in sorted(missing.keys()):
            month = date[:7]
            dt = datetime.strptime(date, '%Y-%m-%d')
            is_sunday = (dt.weekday() == 6)
            monthly[month].append({
                'date': date,
                'is_sunday': is_sunday,
                'commits': len(missing[date])
            })

        for month in sorted(monthly.keys()):
            days = monthly[month]
            total_days = len(days)
            sunday_days = sum(1 for d in days if d['is_sunday'])
            total_commits = sum(d['commits'] for d in days)

            print(f"\n{month}月期:")
            print(f"  不足日数: {total_days}日 (うち日曜日: {sunday_days}日)")
            print(f"  総コミット数: {total_commits}件")
            print(f"  日付一覧: {', '.join([d['date'] for d in days])}")

        # JSONとして出力
        output_path = 'missing_work_records.json'
        output_data = {
            'summary': {
                'total_missing_days': len(missing),
                'current_record_days': len(current_dates),
                'git_commit_days': len(git_commits)
            },
            'missing_dates': {}
        }

        for date, commits in sorted(missing.items()):
            dt = datetime.strptime(date, '%Y-%m-%d')
            output_data['missing_dates'][date] = {
                'weekday': dt.weekday(),
                'is_sunday': (dt.weekday() == 6),
                'commit_count': len(commits),
                'start_time': min(c['time'] for c in commits),
                'end_time': max(c['time'] for c in commits),
                'commits': commits
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n詳細データを {output_path} に出力しました")

    else:
        print("\n不足している日付はありません")

if __name__ == '__main__':
    main()
