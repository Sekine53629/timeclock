#!/usr/bin/env python3
"""
Gitコミット履歴からTsuruha業務関連の作業記録をJSON形式で抽出
"""
import subprocess
import json
from datetime import datetime
import re

def get_git_log():
    """Git履歴を取得"""
    cmd = [
        'git', 'log', '--all',
        '--pretty=format:%H|%an|%ae|%ad|%s',
        '--date=iso',
        '--numstat'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def get_commit_details(commit_hash):
    """特定のコミットの詳細情報を取得"""
    # コミットメッセージ
    cmd_msg = ['git', 'log', '-1', '--pretty=format:%B', commit_hash]
    msg_result = subprocess.run(cmd_msg, capture_output=True, text=True)

    # 変更されたファイル
    cmd_files = ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash]
    files_result = subprocess.run(cmd_files, capture_output=True, text=True)

    # ファイルの統計
    cmd_stats = ['git', 'show', '--stat', '--pretty=format:', commit_hash]
    stats_result = subprocess.run(cmd_stats, capture_output=True, text=True)

    return {
        'message_body': msg_result.stdout.strip(),
        'files_changed': [f for f in files_result.stdout.strip().split('\n') if f],
        'stats': stats_result.stdout.strip()
    }

def parse_git_log(log_text):
    """Git履歴を解析してJSON構造に変換"""
    commits = []
    lines = log_text.split('\n')

    current_commit = None

    for line in lines:
        if '|' in line and len(line.split('|')) == 5:
            # 新しいコミット行
            if current_commit:
                commits.append(current_commit)

            parts = line.split('|')
            commit_hash = parts[0]
            author = parts[1]
            email = parts[2]
            date = parts[3]
            subject = parts[4]

            # コミット詳細を取得
            details = get_commit_details(commit_hash)

            current_commit = {
                'commit_hash': commit_hash,
                'author': author,
                'email': email,
                'date': date,
                'subject': subject,
                'message': details['message_body'],
                'files_changed': details['files_changed'],
                'stats': details['stats']
            }

    if current_commit:
        commits.append(current_commit)

    return commits

def filter_tsuruha_commits(commits):
    """Tsuruha関連のコミットをフィルタリング"""
    tsuruha_commits = []

    for commit in commits:
        # Tsuruhaメールアドレス、または作業時間関連のキーワードを含むコミット
        is_tsuruha = (
            'tsuruha.co.jp' in commit['email'].lower() or
            '打刻' in commit['subject'] or
            '勤怠' in commit['subject'] or
            'timeclock' in commit['subject'].lower()
        )

        if is_tsuruha:
            tsuruha_commits.append(commit)

    return tsuruha_commits

def estimate_work_hours(commits):
    """コミット履歴から作業時間を推定"""
    work_sessions = []

    # コミットを日付でグループ化
    commits_by_date = {}
    for commit in commits:
        date_str = commit['date'][:10]  # YYYY-MM-DD
        if date_str not in commits_by_date:
            commits_by_date[date_str] = []
        commits_by_date[date_str].append(commit)

    # 各日付の作業セッションを推定
    for date, day_commits in sorted(commits_by_date.items()):
        # コミット時間を抽出
        times = []
        for commit in day_commits:
            time_str = commit['date'][11:19]  # HH:MM:SS
            times.append(time_str)

        # 最初と最後のコミット時間から作業時間を推定
        if times:
            start_time = min(times)
            end_time = max(times)

            # 時間差を計算
            start_h, start_m = map(int, start_time.split(':')[:2])
            end_h, end_m = map(int, end_time.split(':')[:2])

            hours = end_h - start_h + (end_m - start_m) / 60

            # 最低30分、最大8時間と仮定
            if hours < 0.5:
                hours = 0.5
            elif hours > 8:
                hours = 8

            work_sessions.append({
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'estimated_hours': round(hours, 2),
                'commits_count': len(day_commits),
                'commits': day_commits
            })

    return work_sessions

def main():
    print("Gitコミット履歴を取得中...")
    log_text = get_git_log()

    print("コミット履歴を解析中...")
    all_commits = parse_git_log(log_text)

    print(f"全コミット数: {len(all_commits)}")

    print("Tsuruha関連のコミットをフィルタリング中...")
    tsuruha_commits = filter_tsuruha_commits(all_commits)

    print(f"Tsuruha関連コミット数: {len(tsuruha_commits)}")

    print("作業時間を推定中...")
    work_sessions = estimate_work_hours(tsuruha_commits)

    # 総作業時間を計算
    total_hours = sum(session['estimated_hours'] for session in work_sessions)

    # JSON出力用のデータ構造を作成
    output = {
        'project': 'timeclock - 打刻システム開発',
        'company': 'Tsuruha',
        'extraction_date': datetime.now().isoformat(),
        'summary': {
            'total_commits': len(tsuruha_commits),
            'total_work_sessions': len(work_sessions),
            'estimated_total_hours': round(total_hours, 2),
            'period_start': work_sessions[0]['date'] if work_sessions else None,
            'period_end': work_sessions[-1]['date'] if work_sessions else None
        },
        'work_sessions': work_sessions,
        'all_tsuruha_commits': tsuruha_commits
    }

    # JSONファイルに保存
    output_file = 'tsuruha_git_work_history.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 作業履歴をJSONファイルに保存しました: {output_file}")
    print(f"   総作業セッション数: {len(work_sessions)}")
    print(f"   推定総作業時間: {round(total_hours, 2)} 時間")
    print(f"   期間: {work_sessions[0]['date']} ~ {work_sessions[-1]['date']}" if work_sessions else "")

if __name__ == '__main__':
    main()
