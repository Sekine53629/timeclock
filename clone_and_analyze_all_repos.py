#!/usr/bin/env python3
"""
GitHub上のすべてのリポジトリをクローンして作業履歴を抽出
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

PROJECTS_ROOT = Path.home() / 'Documents' / 'GitHub' / 'GitHub_Sekine53629'

def get_all_github_repos():
    """GitHub CLIを使って全リポジトリのリストを取得"""
    cmd = ['gh', 'repo', 'list', 'Sekine53629', '--limit', '100', '--json', 'name,nameWithOwner,url,pushedAt,isPrivate']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"エラー: {e}")
        return []

def clone_repo(repo_url, target_dir):
    """リポジトリをクローン"""
    if target_dir.exists():
        print(f"   ✓ 既にクローン済み")
        return True

    try:
        cmd = ['git', 'clone', repo_url, str(target_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"   ✅ クローン成功")
            return True
        else:
            print(f"   ❌ クローン失敗: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def get_repo_git_summary(repo_path):
    """リポジトリのGit履歴サマリーを取得"""
    try:
        # 全コミット数
        cmd_count = ['git', '-C', str(repo_path), 'rev-list', '--all', '--count']
        count_result = subprocess.run(cmd_count, capture_output=True, text=True, timeout=30)
        total_commits = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

        if total_commits == 0:
            return None

        # 最初と最後のコミット日時
        cmd_first = ['git', '-C', str(repo_path), 'log', '--reverse', '--pretty=format:%ad', '--date=iso', '-1']
        first_result = subprocess.run(cmd_first, capture_output=True, text=True, timeout=10)
        first_commit_date = first_result.stdout.strip() if first_result.returncode == 0 else None

        cmd_last = ['git', '-C', str(repo_path), 'log', '--pretty=format:%ad', '--date=iso', '-1']
        last_result = subprocess.run(cmd_last, capture_output=True, text=True, timeout=10)
        last_commit_date = last_result.stdout.strip() if last_result.returncode == 0 else None

        # コミット履歴
        cmd_log = ['git', '-C', str(repo_path), 'log', '--all', '--pretty=format:%H|%an|%ae|%ad|%s', '--date=iso']
        log_result = subprocess.run(cmd_log, capture_output=True, text=True, timeout=60)

        commits = []
        authors = set()
        emails = set()
        commits_by_date = defaultdict(list)

        if log_result.returncode == 0:
            for line in log_result.stdout.strip().split('\n'):
                if '|' in line and len(line.split('|')) >= 5:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        commit_hash = parts[0]
                        author = parts[1]
                        email = parts[2]
                        date = parts[3]
                        subject = '|'.join(parts[4:])  # 件名に|が含まれる場合に対応

                        authors.add(author)
                        emails.add(email)

                        date_only = date[:10]
                        time_only = date[11:19]

                        commits.append({
                            'hash': commit_hash[:8],
                            'author': author,
                            'email': email,
                            'date': date,
                            'subject': subject
                        })

                        commits_by_date[date_only].append(time_only)

        # 各日の作業時間を推定
        work_days = []
        for date, times in sorted(commits_by_date.items()):
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

                work_days.append({
                    'date': date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'estimated_hours': round(hours, 2),
                    'commits_count': len(commits_by_date[date])
                })

        total_estimated_hours = sum(day['estimated_hours'] for day in work_days)

        # Tsuruha関連かどうかの判定
        has_tsuruha_email = any('tsuruha.co.jp' in email.lower() for email in emails)

        return {
            'total_commits': total_commits,
            'first_commit_date': first_commit_date,
            'last_commit_date': last_commit_date,
            'authors': list(authors),
            'emails': list(emails),
            'has_tsuruha_email': has_tsuruha_email,
            'work_days_count': len(work_days),
            'estimated_total_hours': round(total_estimated_hours, 2),
            'work_days': work_days,
            'recent_commits': commits[:10],
            'success': True
        }

    except Exception as e:
        return {'error': str(e), 'success': False}

def main():
    print("\n" + "=" * 80)
    print("🚀 GitHub上の全リポジトリをクローン＆分析")
    print("=" * 80)
    print()

    # GitHub上のリポジトリ一覧を取得
    print("📡 GitHub APIからリポジトリ一覧を取得中...")
    repos = get_all_github_repos()

    if not repos:
        print("❌ リポジトリが取得できませんでした")
        return

    print(f"✅ {len(repos)}個のリポジトリが見つかりました\n")

    all_projects_data = []
    tsuruha_projects_data = []
    total_hours = 0
    tsuruha_hours = 0

    # 各リポジトリを処理
    for i, repo in enumerate(repos, 1):
        repo_name = repo['name']
        repo_url = repo['url']
        is_private = repo['isPrivate']

        privacy_mark = "🔒" if is_private else "🌐"
        print(f"{i:2d}. {privacy_mark} {repo_name}")

        # クローン先ディレクトリ
        target_dir = PROJECTS_ROOT / repo_name

        # クローン
        if not clone_repo(repo_url, target_dir):
            continue

        # Git履歴を分析
        print(f"   📊 Git履歴を分析中...")
        summary = get_repo_git_summary(target_dir)

        if not summary or not summary.get('success'):
            print(f"   ⚠️  分析できませんでした\n")
            continue

        project_data = {
            'project_name': repo_name,
            'project_url': repo_url,
            'is_private': is_private,
            'pushed_at': repo['pushedAt'],
            **summary
        }

        all_projects_data.append(project_data)
        total_hours += summary['estimated_total_hours']

        print(f"   ✓ コミット数: {summary['total_commits']}")
        print(f"   ✓ 推定作業時間: {summary['estimated_total_hours']}時間")
        print(f"   ✓ 作業日数: {summary['work_days_count']}日")

        if summary['has_tsuruha_email']:
            print(f"   🏢 Tsuruha関連")
            tsuruha_projects_data.append(project_data)
            tsuruha_hours += summary['estimated_total_hours']

        print()

    # 結果をJSONに保存
    output = {
        'extraction_date': datetime.now().isoformat(),
        'company': 'Tsuruha',
        'summary': {
            'total_repos': len(repos),
            'analyzed_repos': len(all_projects_data),
            'total_estimated_hours': round(total_hours, 2),
            'tsuruha_repos_count': len(tsuruha_projects_data),
            'tsuruha_estimated_hours': round(tsuruha_hours, 2)
        },
        'all_projects': all_projects_data,
        'tsuruha_projects': tsuruha_projects_data
    }

    output_file = 'complete_github_work_history.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # サマリー表示
    print("=" * 80)
    print("📊 最終集計結果")
    print("=" * 80)
    print(f"総リポジトリ数: {len(repos)}")
    print(f"分析成功: {len(all_projects_data)}")
    print(f"総推定作業時間: {round(total_hours, 2)} 時間")
    print()
    print(f"🏢 Tsuruha関連リポジトリ数: {len(tsuruha_projects_data)}")
    print(f"🏢 Tsuruha関連推定作業時間: {round(tsuruha_hours, 2)} 時間")
    print()
    print(f"✅ 結果を保存しました: {output_file}")
    print("=" * 80)

    # Tsuruha関連プロジェクトのリスト
    if tsuruha_projects_data:
        print("\n🏢 Tsuruha関連プロジェクト一覧:")
        for project in sorted(tsuruha_projects_data, key=lambda x: x['estimated_total_hours'], reverse=True):
            print(f"  - {project['project_name']}: {project['estimated_total_hours']}時間")

if __name__ == '__main__':
    main()
