#!/usr/bin/env python3
"""
すべてのプロジェクトの開発履歴を抽出し、Tsuruha業務関連かどうか判断できるように整理
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECTS_ROOT = Path.home() / 'Documents' / 'GitHub' / 'GitHub_Sekine53629'

def is_git_repo(path):
    """Gitリポジトリかどうか確認"""
    return (path / '.git').exists()

def get_project_git_summary(project_path):
    """プロジェクトのGit履歴サマリーを取得"""
    try:
        # 全コミット数
        cmd_count = ['git', '-C', str(project_path), 'rev-list', '--all', '--count']
        count_result = subprocess.run(cmd_count, capture_output=True, text=True, timeout=10)
        total_commits = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

        # 最初と最後のコミット日時
        cmd_first = ['git', '-C', str(project_path), 'log', '--reverse', '--pretty=format:%ad', '--date=iso', '-1']
        first_result = subprocess.run(cmd_first, capture_output=True, text=True, timeout=10)
        first_commit_date = first_result.stdout.strip() if first_result.returncode == 0 else None

        cmd_last = ['git', '-C', str(project_path), 'log', '--pretty=format:%ad', '--date=iso', '-1']
        last_result = subprocess.run(cmd_last, capture_output=True, text=True, timeout=10)
        last_commit_date = last_result.stdout.strip() if last_result.returncode == 0 else None

        # コミット履歴（詳細）
        cmd_log = ['git', '-C', str(project_path), 'log', '--all', '--pretty=format:%H|%an|%ae|%ad|%s', '--date=iso']
        log_result = subprocess.run(cmd_log, capture_output=True, text=True, timeout=30)

        commits = []
        authors = set()
        emails = set()
        commits_by_date = defaultdict(list)

        if log_result.returncode == 0:
            for line in log_result.stdout.strip().split('\n'):
                if '|' in line and len(line.split('|')) == 5:
                    parts = line.split('|')
                    commit_hash = parts[0]
                    author = parts[1]
                    email = parts[2]
                    date = parts[3]
                    subject = parts[4]

                    authors.add(author)
                    emails.add(email)

                    date_only = date[:10]
                    time_only = date[11:19]

                    commit_data = {
                        'hash': commit_hash[:8],
                        'author': author,
                        'email': email,
                        'date': date,
                        'subject': subject
                    }

                    commits.append(commit_data)
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

                # 最低30分、最大8時間
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

        # Tsuruha関連かどうかの判定材料
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
            'recent_commits': commits[:10],  # 最新10件
            'success': True
        }

    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }

def scan_all_projects():
    """すべてのプロジェクトをスキャン"""
    print("=" * 80)
    print("すべてのプロジェクトの開発履歴を抽出中...")
    print("=" * 80)
    print()

    all_projects = []
    tsuruha_projects = []
    total_hours_all = 0
    total_hours_tsuruha = 0

    for item in sorted(PROJECTS_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith('.'):
            continue

        project_name = item.name
        print(f"📁 {project_name}")

        if not is_git_repo(item):
            print(f"   ⚠️  Gitリポジトリではありません\n")
            continue

        summary = get_project_git_summary(item)

        if not summary['success']:
            print(f"   ❌ エラー: {summary.get('error', '不明')}\n")
            continue

        project_data = {
            'project_name': project_name,
            'project_path': str(item),
            **summary
        }

        all_projects.append(project_data)
        total_hours_all += summary['estimated_total_hours']

        # 表示
        print(f"   コミット数: {summary['total_commits']}")
        print(f"   推定作業時間: {summary['estimated_total_hours']}時間")
        print(f"   作業日数: {summary['work_days_count']}日")

        if summary['first_commit_date'] and summary['last_commit_date']:
            period = f"{summary['first_commit_date'][:10]} ~ {summary['last_commit_date'][:10]}"
            print(f"   期間: {period}")

        if summary['has_tsuruha_email']:
            print(f"   ✅ Tsuruha関連メールアドレスあり")
            tsuruha_projects.append(project_data)
            total_hours_tsuruha += summary['estimated_total_hours']

        print()

    return all_projects, tsuruha_projects, total_hours_all, total_hours_tsuruha

def main():
    print("\n🔍 全プロジェクトの開発履歴スキャンを開始します...\n")

    all_projects, tsuruha_projects, total_hours_all, total_hours_tsuruha = scan_all_projects()

    # 集計結果
    print("=" * 80)
    print("📊 全体集計結果")
    print("=" * 80)
    print(f"総プロジェクト数: {len(all_projects)}")
    print(f"総推定作業時間: {round(total_hours_all, 2)} 時間")
    print()
    print(f"Tsuruha関連プロジェクト数: {len(tsuruha_projects)}")
    print(f"Tsuruha関連推定作業時間: {round(total_hours_tsuruha, 2)} 時間")
    print()

    # JSONファイルに保存
    output = {
        'extraction_date': datetime.now().isoformat(),
        'company': 'Tsuruha',
        'summary': {
            'total_projects': len(all_projects),
            'total_estimated_hours_all': round(total_hours_all, 2),
            'tsuruha_projects_count': len(tsuruha_projects),
            'tsuruha_estimated_hours': round(total_hours_tsuruha, 2)
        },
        'all_projects': all_projects,
        'tsuruha_projects': tsuruha_projects,
        'instructions': {
            'description': 'このJSONファイルには全プロジェクトの開発履歴が含まれています',
            'tsuruha_determination': 'has_tsuruha_email フィールドがtrueのプロジェクトは自動的にTsuruha関連と判定されています',
            'manual_check': 'その他のプロジェクトについても、プロジェクト名や最近のコミット内容を確認してTsuruha業務に関連するか判断できます'
        }
    }

    output_file = 'all_projects_work_history.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 全プロジェクトの開発履歴を保存しました: {output_file}")
    print()

    # プロジェクト別サマリー（作業時間が多い順）
    if all_projects:
        print("=" * 80)
        print("📋 プロジェクト別サマリー（作業時間が多い順）")
        print("=" * 80)

        sorted_projects = sorted(all_projects,
                                key=lambda x: x['estimated_total_hours'],
                                reverse=True)

        for i, project in enumerate(sorted_projects[:20], 1):  # 上位20件
            tsuruha_mark = "🏢" if project['has_tsuruha_email'] else "  "
            print(f"\n{i:2d}. {tsuruha_mark} 【{project['project_name']}】")
            print(f"      作業時間: {project['estimated_total_hours']}時間")
            print(f"      コミット数: {project['total_commits']}")
            print(f"      作業日数: {project['work_days_count']}日")

            if project.get('first_commit_date'):
                period = f"{project['first_commit_date'][:10]} ~ {project['last_commit_date'][:10]}"
                print(f"      期間: {period}")

    print("\n" + "=" * 80)
    print("💡 ヒント:")
    print("   🏢 マークはTsuruhaメールアドレスが含まれるプロジェクトです")
    print("   JSONファイルで各プロジェクトの詳細を確認し、Tsuruha業務関連かどうか判断してください")
    print("=" * 80)

if __name__ == '__main__':
    main()
