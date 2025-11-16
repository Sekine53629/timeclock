#!/usr/bin/env python3
"""
すべてのプロジェクトのGit履歴からTsuruha業務関連の作業記録を抽出
"""
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

# プロジェクトディレクトリのルート
PROJECTS_ROOT = Path.home() / 'Documents' / 'GitHub' / 'GitHub_Sekine53629'

def is_git_repo(path):
    """Gitリポジトリかどうか確認"""
    return (path / '.git').exists()

def get_git_log_for_project(project_path):
    """プロジェクトのGit履歴を取得"""
    cmd = [
        'git', '-C', str(project_path),
        'log', '--all',
        '--pretty=format:%H|%an|%ae|%ad|%s',
        '--date=iso'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        print(f"  ⚠️  エラー: {e}")
        return None

def get_commit_details(project_path, commit_hash):
    """コミットの詳細情報を取得"""
    try:
        # コミットメッセージ
        cmd_msg = ['git', '-C', str(project_path), 'log', '-1', '--pretty=format:%B', commit_hash]
        msg_result = subprocess.run(cmd_msg, capture_output=True, text=True, timeout=10)

        # 変更されたファイル
        cmd_files = ['git', '-C', str(project_path), 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash]
        files_result = subprocess.run(cmd_files, capture_output=True, text=True, timeout=10)

        # ファイルの統計
        cmd_stats = ['git', '-C', str(project_path), 'show', '--stat', '--pretty=format:', commit_hash]
        stats_result = subprocess.run(cmd_stats, capture_output=True, text=True, timeout=10)

        return {
            'message_body': msg_result.stdout.strip(),
            'files_changed': [f for f in files_result.stdout.strip().split('\n') if f],
            'stats': stats_result.stdout.strip()
        }
    except Exception as e:
        return {
            'message_body': '',
            'files_changed': [],
            'stats': ''
        }

def parse_git_log(project_path, log_text):
    """Git履歴を解析"""
    commits = []
    if not log_text:
        return commits

    lines = log_text.split('\n')
    for line in lines:
        if '|' in line and len(line.split('|')) == 5:
            parts = line.split('|')
            commit_hash = parts[0]
            author = parts[1]
            email = parts[2]
            date = parts[3]
            subject = parts[4]

            details = get_commit_details(project_path, commit_hash)

            commits.append({
                'commit_hash': commit_hash,
                'author': author,
                'email': email,
                'date': date,
                'subject': subject,
                'message': details['message_body'],
                'files_changed': details['files_changed'],
                'stats': details['stats']
            })

    return commits

def filter_tsuruha_commits(commits):
    """Tsuruha関連のコミットをフィルタリング"""
    tsuruha_commits = []

    for commit in commits:
        # Tsuruhaメールアドレスを含むコミット
        is_tsuruha = 'tsuruha.co.jp' in commit['email'].lower()

        if is_tsuruha:
            tsuruha_commits.append(commit)

    return tsuruha_commits

def estimate_work_hours(commits):
    """コミット履歴から作業時間を推定"""
    if not commits:
        return []

    work_sessions = []
    commits_by_date = {}

    for commit in commits:
        date_str = commit['date'][:10]
        if date_str not in commits_by_date:
            commits_by_date[date_str] = []
        commits_by_date[date_str].append(commit)

    for date, day_commits in sorted(commits_by_date.items()):
        times = []
        for commit in day_commits:
            time_str = commit['date'][11:19]
            times.append(time_str)

        if times:
            start_time = min(times)
            end_time = max(times)

            start_h, start_m = map(int, start_time.split(':')[:2])
            end_h, end_m = map(int, end_time.split(':')[:2])

            hours = end_h - start_h + (end_m - start_m) / 60

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

def scan_all_projects():
    """すべてのプロジェクトをスキャン"""
    print("=" * 80)
    print("すべてのプロジェクトからTsuruha業務履歴を抽出中...")
    print("=" * 80)
    print()

    all_projects_data = {}
    total_tsuruha_commits = 0
    total_hours = 0

    # プロジェクトディレクトリを走査
    for item in sorted(PROJECTS_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith('.'):
            continue

        project_name = item.name
        print(f"📁 {project_name} を確認中...")

        if not is_git_repo(item):
            print(f"   ⚠️  Gitリポジトリではありません\n")
            continue

        # Git履歴を取得
        log_text = get_git_log_for_project(item)
        if not log_text:
            print(f"   ℹ️  Git履歴が取得できませんでした\n")
            continue

        # コミットを解析
        all_commits = parse_git_log(item, log_text)
        tsuruha_commits = filter_tsuruha_commits(all_commits)

        if not tsuruha_commits:
            print(f"   ✓ Tsuruha関連のコミットなし\n")
            continue

        # 作業時間を推定
        work_sessions = estimate_work_hours(tsuruha_commits)
        project_hours = sum(session['estimated_hours'] for session in work_sessions)

        print(f"   ✅ Tsuruhaコミット: {len(tsuruha_commits)}件")
        print(f"   ⏱️  推定作業時間: {project_hours}時間")
        print(f"   📅 作業期間: {work_sessions[0]['date']} ~ {work_sessions[-1]['date']}\n" if work_sessions else "")

        total_tsuruha_commits += len(tsuruha_commits)
        total_hours += project_hours

        all_projects_data[project_name] = {
            'project_path': str(item),
            'total_commits': len(all_commits),
            'tsuruha_commits_count': len(tsuruha_commits),
            'estimated_hours': round(project_hours, 2),
            'work_sessions': work_sessions,
            'all_tsuruha_commits': tsuruha_commits
        }

    return all_projects_data, total_tsuruha_commits, total_hours

def main():
    print("\n🔍 Tsuruha業務履歴の全プロジェクトスキャンを開始します...\n")

    all_projects_data, total_commits, total_hours = scan_all_projects()

    # 集計結果を表示
    print("=" * 80)
    print("📊 集計結果")
    print("=" * 80)
    print(f"プロジェクト数: {len(all_projects_data)}")
    print(f"総Tsuruhaコミット数: {total_commits}")
    print(f"推定総作業時間: {round(total_hours, 2)} 時間")
    print()

    # JSONファイルに保存
    output = {
        'extraction_date': datetime.now().isoformat(),
        'company': 'Tsuruha',
        'summary': {
            'total_projects': len(all_projects_data),
            'total_tsuruha_commits': total_commits,
            'estimated_total_hours': round(total_hours, 2)
        },
        'projects': all_projects_data
    }

    output_file = 'all_tsuruha_projects_history.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ すべてのプロジェクトの作業履歴を保存しました: {output_file}")
    print()

    # プロジェクト別サマリーを表示
    if all_projects_data:
        print("=" * 80)
        print("📋 プロジェクト別サマリー")
        print("=" * 80)
        for project_name, data in sorted(all_projects_data.items(),
                                         key=lambda x: x[1]['estimated_hours'],
                                         reverse=True):
            print(f"\n【{project_name}】")
            print(f"  コミット数: {data['tsuruha_commits_count']}")
            print(f"  作業時間: {data['estimated_hours']}時間")
            if data['work_sessions']:
                dates = [s['date'] for s in data['work_sessions']]
                print(f"  期間: {min(dates)} ~ {max(dates)}")

if __name__ == '__main__':
    main()
