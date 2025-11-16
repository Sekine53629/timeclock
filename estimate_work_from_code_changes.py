#!/usr/bin/env python3
"""
コード変更量から作業時間を推定
短時間コミットでも変更量が多い場合は、実際の作業時間を推測
"""
import subprocess
import json
from pathlib import Path
from collections import defaultdict

PROJECTS_ROOT = Path.home() / 'Documents' / 'GitHub' / 'GitHub_Sekine53629'

def get_commit_stats(repo_path, commit_hash):
    """コミットの変更統計を取得"""
    try:
        cmd = ['git', '-C', str(repo_path), 'show', '--stat', '--pretty=format:', commit_hash]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return None

        stats = result.stdout.strip()

        # 最後の行から統計を抽出
        lines = stats.split('\n')
        if not lines:
            return None

        summary_line = lines[-1] if lines else ''

        # "X files changed, Y insertions(+), Z deletions(-)" の形式をパース
        files_changed = 0
        insertions = 0
        deletions = 0

        if 'file' in summary_line:
            parts = summary_line.split(',')
            for part in parts:
                part = part.strip()
                if 'file' in part:
                    files_changed = int(part.split()[0])
                elif 'insertion' in part:
                    insertions = int(part.split()[0])
                elif 'deletion' in part:
                    deletions = int(part.split()[0])

        return {
            'files_changed': files_changed,
            'insertions': insertions,
            'deletions': deletions,
            'total_changes': insertions + deletions
        }
    except Exception as e:
        return None

def estimate_work_hours_from_changes(stats):
    """変更量から作業時間を推定

    基準:
    - 1ファイル変更 ≒ 15分（新規作成は30分）
    - 100行変更 ≒ 30分
    - 500行変更 ≒ 2時間
    - 1000行以上 ≒ 4時間以上
    """
    if not stats:
        return 0

    files = stats['files_changed']
    total_changes = stats['total_changes']

    # ファイル数ベースの推定（分）
    file_based = files * 15

    # 変更行数ベースの推定（分）
    if total_changes < 50:
        line_based = total_changes * 0.5  # 1行あたり30秒
    elif total_changes < 200:
        line_based = 25 + (total_changes - 50) * 0.3  # 1行あたり18秒
    elif total_changes < 500:
        line_based = 70 + (total_changes - 200) * 0.2  # 1行あたり12秒
    else:
        line_based = 130 + (total_changes - 500) * 0.1  # 1行あたり6秒

    # 両方の推定値の平均を取る（分）
    estimated_minutes = (file_based + line_based) / 2

    # 時間に変換
    estimated_hours = estimated_minutes / 60

    return round(estimated_hours, 2)

def analyze_and_estimate():
    """全プロジェクトを分析して作業時間を推定"""

    # 既存のデータを読み込み
    with open('complete_github_work_history_unlimited.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("📊 コード変更量から作業時間を推定")
    print("=" * 80)
    print()

    total_git_based = 0
    total_estimated = 0
    total_final = 0

    tsuruha_git_based = 0
    tsuruha_estimated = 0
    tsuruha_final = 0

    projects_with_estimates = []

    for project in data['all_projects']:
        project_name = project['project_name']
        project_path = PROJECTS_ROOT / project_name

        # kadai、practiceが含まれるプロジェクトは除外
        if 'kadai' in project_name.lower() or 'practice' in project_name.lower():
            print(f"⏭️  {project_name} (学習用プロジェクトのためスキップ)")
            # Git時間ベースのみ設定
            project['git_based_hours'] = project['estimated_total_hours']
            project['estimated_additional_hours'] = 0
            project['final_estimated_hours'] = project['estimated_total_hours']
            project['excluded_reason'] = '学習用プロジェクト（kadai/practice）'
            continue

        if not project_path.exists():
            continue

        print(f"📁 {project_name}")

        git_based_hours = project['estimated_total_hours']
        additional_hours = 0

        # 各作業日を分析
        for work_day in project.get('work_days', []):
            date = work_day['date']
            git_hours = work_day['estimated_hours']
            commits_count = work_day['commits_count']

            # Git時間ベースで短時間（1時間未満）でコミット数が少ない日を対象
            if git_hours < 1.0 and commits_count <= 2:
                # その日のコミットの変更量を確認
                day_changes = {
                    'files': 0,
                    'insertions': 0,
                    'deletions': 0
                }

                # その日の全コミットを取得
                for commit in project.get('recent_commits', []):
                    if commit['date'].startswith(date):
                        commit_hash = commit['hash']
                        stats = get_commit_stats(project_path, commit_hash)

                        if stats:
                            day_changes['files'] += stats['files_changed']
                            day_changes['insertions'] += stats['insertions']
                            day_changes['deletions'] += stats['deletions']

                # 変更量が大きい場合は推定時間を追加
                if day_changes['files'] > 5 or (day_changes['insertions'] + day_changes['deletions']) > 100:
                    estimated = estimate_work_hours_from_changes({
                        'files_changed': day_changes['files'],
                        'insertions': day_changes['insertions'],
                        'deletions': day_changes['deletions'],
                        'total_changes': day_changes['insertions'] + day_changes['deletions']
                    })

                    # Git時間を超える場合のみ追加
                    if estimated > git_hours:
                        additional = estimated - git_hours
                        additional_hours += additional
                        work_day['estimated_additional_hours'] = round(additional, 2)
                        work_day['estimation_reason'] = 'コード変更量が多いため推定時間を追加'

                        print(f"   {date}: Git={git_hours}h, 変更量推定={estimated}h, 追加=+{additional:.2f}h")
                        print(f"      ({day_changes['files']}ファイル, {day_changes['insertions']}+/{day_changes['deletions']}-行)")

        final_hours = git_based_hours + additional_hours

        project['git_based_hours'] = git_based_hours
        project['estimated_additional_hours'] = round(additional_hours, 2)
        project['final_estimated_hours'] = round(final_hours, 2)

        total_git_based += git_based_hours
        total_estimated += additional_hours
        total_final += final_hours

        if project.get('has_tsuruha_email', False):
            tsuruha_git_based += git_based_hours
            tsuruha_estimated += additional_hours
            tsuruha_final += final_hours

        if additional_hours > 0:
            projects_with_estimates.append({
                'name': project_name,
                'git_hours': git_based_hours,
                'additional': additional_hours,
                'final': final_hours,
                'is_tsuruha': project.get('has_tsuruha_email', False)
            })

            print(f"   合計: Git={git_based_hours}h + 推定={additional_hours:.2f}h = {final_hours:.2f}h")

        print()

    # サマリーを更新
    data['estimation_method'] = {
        'description': 'Git時間ベース + コード変更量からの推定',
        'git_based_calculation': '各日の最初と最後のコミット時間の差',
        'code_based_estimation': '短時間コミットでもファイル数や変更行数が多い場合、作業量から推定時間を追加',
        'estimation_formula': {
            'file_based': '1ファイル ≒ 15分',
            'line_based_small': '50行未満: 1行 ≒ 0.5分',
            'line_based_medium': '50-200行: 1行 ≒ 0.3分',
            'line_based_large': '200-500行: 1行 ≒ 0.2分',
            'line_based_xlarge': '500行以上: 1行 ≒ 0.1分'
        },
        'note': '推定時間は参考値です。実際の作業時間とは異なる可能性があります。'
    }

    data['summary']['git_based_hours'] = round(total_git_based, 2)
    data['summary']['estimated_additional_hours'] = round(total_estimated, 2)
    data['summary']['final_estimated_hours'] = round(total_final, 2)
    data['summary']['tsuruha_git_based_hours'] = round(tsuruha_git_based, 2)
    data['summary']['tsuruha_estimated_additional_hours'] = round(tsuruha_estimated, 2)
    data['summary']['tsuruha_final_estimated_hours'] = round(tsuruha_final, 2)

    # 保存
    output_file = 'complete_github_work_history_with_estimation.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # レポート
    print("=" * 80)
    print("📊 最終集計結果")
    print("=" * 80)
    print(f"\n全プロジェクト:")
    print(f"  Git時間ベース: {total_git_based:.2f}時間")
    print(f"  推定追加時間: {total_estimated:.2f}時間 ⚠️ 推測値")
    print(f"  最終推定時間: {total_final:.2f}時間")
    print(f"\n🏢 Tsuruha関連:")
    print(f"  Git時間ベース: {tsuruha_git_based:.2f}時間")
    print(f"  推定追加時間: {tsuruha_estimated:.2f}時間 ⚠️ 推測値")
    print(f"  最終推定時間: {tsuruha_final:.2f}時間")

    if projects_with_estimates:
        print("\n" + "=" * 80)
        print("📋 推定時間が追加されたプロジェクト")
        print("=" * 80)

        projects_with_estimates.sort(key=lambda x: x['additional'], reverse=True)

        for p in projects_with_estimates:
            mark = "🏢" if p['is_tsuruha'] else "  "
            print(f"\n{mark} {p['name']}")
            print(f"   Git: {p['git_hours']:.2f}h + 推定: {p['additional']:.2f}h = 合計: {p['final']:.2f}h")

    print("\n" + "=" * 80)
    print(f"✅ 結果を保存しました: {output_file}")
    print("=" * 80)
    print("\n⚠️  注意: 推定追加時間は変更量から算出した参考値です")
    print("   実際の作業時間とは異なる可能性があります")

if __name__ == '__main__':
    analyze_and_estimate()
