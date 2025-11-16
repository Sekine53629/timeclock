"""
GitHub Commit History Analyzer for Multiple Accounts
複数のGitHubアカウントからコミット履歴を収集し、残業時間を推定するツール
"""

import os
import json
import csv
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


class GitHubCommitAnalyzer:
    """GitHubの複数アカウントからコミット履歴を収集・分析"""

    def __init__(self, github_tokens: List[str]):
        """
        Args:
            github_tokens: GitHubのPersonal Access Tokenのリスト（複数アカウント対応）
        """
        self.tokens = github_tokens
        self.all_commits = []
        self.rate_limit_remaining = {}

    def estimate_work_time_from_changes(self, lines_added: int, lines_deleted: int,
                                       files_changed: int) -> float:
        """
        コード変更量から作業時間を推定（分単位）

        推定ロジック:
        - 新規追加: 10行 = 約5分
        - 削除: 10行 = 約2分（削除は追加より速い）
        - ファイル変更数: 1ファイル = 最低10分（切り替えコスト）
        - 複数ファイル変更: 追加で1ファイルあたり5分
        """
        # 基本時間: 行数ベース
        add_time = (lines_added / 10) * 5  # 10行で5分
        delete_time = (lines_deleted / 10) * 2  # 10行で2分

        # ファイル変更による追加時間
        if files_changed > 0:
            file_time = 10 + (files_changed - 1) * 5  # 最初のファイル10分 + 追加ファイルごとに5分
        else:
            file_time = 0

        # 合計時間（最低5分）
        total_time = max(add_time + delete_time + file_time, 5)

        # 非常に大きな変更の場合は上限を設ける（1コミット最大480分=8時間）
        total_time = min(total_time, 480)

        return round(total_time, 1)

    def get_commit_details(self, token: str, owner: str, repo: str, sha: str) -> Dict:
        """コミットの詳細情報を取得（変更ファイル数、行数など）"""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        url = f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}'

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})

                files_changed = len(data.get('files', []))
                lines_added = stats.get('additions', 0)
                lines_deleted = stats.get('deletions', 0)

                return {
                    'files_changed': files_changed,
                    'lines_added': lines_added,
                    'lines_deleted': lines_deleted
                }
            else:
                return {'files_changed': 0, 'lines_added': 0, 'lines_deleted': 0}

        except Exception as e:
            print(f"  Error getting commit details: {e}")
            return {'files_changed': 0, 'lines_added': 0, 'lines_deleted': 0}

    def get_user_repos(self, token: str, username: Optional[str] = None) -> List[Dict]:
        """ユーザーのリポジトリ一覧を取得（プライベートリポジトリ含む）"""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # まず認証ユーザー情報を取得
        user_response = requests.get('https://api.github.com/user', headers=headers)
        if user_response.status_code == 200:
            authenticated_username = user_response.json()['login']
        else:
            raise Exception(f"Failed to get user info: {user_response.status_code}")

        # usernameが指定されていない場合は認証ユーザーを使用
        if not username:
            username = authenticated_username

        repos = []
        page = 1

        # 認証ユーザー自身の場合は /user/repos を使用（プライベートリポジトリも取得）
        if username == authenticated_username:
            while True:
                url = 'https://api.github.com/user/repos'
                params = {
                    'per_page': 100,
                    'page': page,
                    'visibility': 'all',  # all, public, private
                    'affiliation': 'owner,collaborator,organization_member'
                }
                response = requests.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    print(f"Error fetching repos: {response.status_code}")
                    break

                data = response.json()
                if not data:
                    break

                repos.extend(data)
                page += 1

                # レート制限チェック
                self.rate_limit_remaining[username] = int(response.headers.get('X-RateLimit-Remaining', 0))
                if self.rate_limit_remaining[username] < 10:
                    print(f"Warning: Rate limit low for {username}: {self.rate_limit_remaining[username]}")
                    time.sleep(60)
        else:
            # 他のユーザーの場合は公開リポジトリのみ
            while True:
                url = f'https://api.github.com/users/{username}/repos'
                params = {'per_page': 100, 'page': page, 'type': 'all'}
                response = requests.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    print(f"Error fetching repos: {response.status_code}")
                    break

                data = response.json()
                if not data:
                    break

                repos.extend(data)
                page += 1

                # レート制限チェック
                self.rate_limit_remaining[username] = int(response.headers.get('X-RateLimit-Remaining', 0))
                if self.rate_limit_remaining[username] < 10:
                    print(f"Warning: Rate limit low for {username}: {self.rate_limit_remaining[username]}")
                    time.sleep(60)

        print(f"Found {len(repos)} repositories for {username} (including private repos)")
        return repos

    def get_repo_commits(self, token: str, owner: str, repo: str, author: str) -> List[Dict]:
        """特定のリポジトリから特定のauthorのコミットを取得"""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        commits = []
        page = 1

        while True:
            url = f'https://api.github.com/repos/{owner}/{repo}/commits'
            params = {
                'author': author,
                'per_page': 100,
                'page': page
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 404:
                # リポジトリが空またはアクセス不可
                break
            elif response.status_code != 200:
                print(f"Error fetching commits from {owner}/{repo}: {response.status_code}")
                break

            data = response.json()
            if not data:
                break

            commits.extend(data)
            page += 1

            # APIレート制限対策
            time.sleep(0.5)

        return commits

    def collect_all_commits(self, usernames: List[str]) -> List[Dict]:
        """全アカウントから全コミットを収集"""
        all_commits = []

        for idx, (token, username) in enumerate(zip(self.tokens, usernames)):
            print(f"\n=== Processing account {idx+1}/{len(usernames)}: {username} ===")

            try:
                repos = self.get_user_repos(token, username)

                for repo in repos:
                    repo_name = repo['name']
                    owner = repo['owner']['login']

                    print(f"Collecting commits from {owner}/{repo_name}...")
                    commits = self.get_repo_commits(token, owner, repo_name, username)

                    for commit in commits:
                        commit_data = self.parse_commit(commit, repo_name, owner, username, token)
                        if commit_data:
                            all_commits.append(commit_data)

                    print(f"  Found {len(commits)} commits")

            except Exception as e:
                print(f"Error processing {username}: {e}")
                continue

        self.all_commits = sorted(all_commits, key=lambda x: x['timestamp'])
        print(f"\n=== Total commits collected: {len(self.all_commits)} ===")
        return self.all_commits

    def parse_commit(self, commit: Dict, repo_name: str, owner: str, account: str, token: str) -> Optional[Dict]:
        """コミット情報をパース（詳細情報含む）"""
        try:
            commit_info = commit['commit']
            author_info = commit_info['author']

            # タイムスタンプをパース
            timestamp_str = author_info['date']
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')

            # 日本時間に変換
            jst_timestamp = timestamp + timedelta(hours=9)

            # コミットの詳細情報を取得（変更ファイル数、行数など）
            sha_full = commit['sha']
            details = self.get_commit_details(token, owner, repo_name, sha_full)

            # 作業時間を推定
            estimated_minutes = self.estimate_work_time_from_changes(
                details['lines_added'],
                details['lines_deleted'],
                details['files_changed']
            )

            return {
                'account': account,
                'repo_owner': owner,
                'repo_name': repo_name,
                'sha': sha_full[:8],
                'sha_full': sha_full,
                'message': commit_info['message'].split('\n')[0][:200],
                'author_name': author_info['name'],
                'author_email': author_info['email'],
                'timestamp': timestamp,
                'timestamp_jst': jst_timestamp,
                'date': jst_timestamp.date(),
                'time': jst_timestamp.time(),
                'hour': jst_timestamp.hour,
                'weekday': jst_timestamp.strftime('%A'),
                'weekday_jp': self.get_japanese_weekday(jst_timestamp.weekday()),
                'is_weekend': jst_timestamp.weekday() >= 5,
                'is_overtime': jst_timestamp.hour >= 18 or jst_timestamp.hour < 9,
                'is_late_night': jst_timestamp.hour >= 22 or jst_timestamp.hour < 5,
                'files_changed': details['files_changed'],
                'lines_added': details['lines_added'],
                'lines_deleted': details['lines_deleted'],
                'estimated_work_minutes': estimated_minutes,
                'estimated_work_hours': round(estimated_minutes / 60, 2),
                'url': commit['html_url']
            }
        except Exception as e:
            print(f"Error parsing commit: {e}")
            return None

    @staticmethod
    def get_japanese_weekday(weekday: int) -> str:
        """曜日を日本語に変換"""
        days = ['月', '火', '水', '木', '金', '土', '日']
        return days[weekday]

    def save_to_csv(self, filename: str = 'github_commits_evidence.csv'):
        """CSVファイルとして保存（Excel/VBAインポート用）"""
        if not self.all_commits:
            print("No commits to save")
            return

        # Shift-JIS（日本語Excel用）で保存
        with open(filename, 'w', newline='', encoding='shift_jis', errors='ignore') as f:
            writer = csv.writer(f)

            # ヘッダー（日本語、git_importと互換性のある形式）
            writer.writerow([
                '日付', '時刻', '曜日', 'プロジェクト名', 'コミットID',
                '作業内容', '変更ファイル数', '追加行数', '削除行数',
                '推定作業時間（分）', '時間外', '休日', '深夜', '作業者名'
            ])

            # データ行
            for commit in self.all_commits:
                writer.writerow([
                    commit['date'],
                    commit['time'],
                    commit['weekday_jp'],
                    commit['repo_name'],
                    commit['sha'],
                    commit['message'],
                    commit['files_changed'],
                    commit['lines_added'],
                    commit['lines_deleted'],
                    commit['estimated_work_minutes'],
                    '○' if commit['is_overtime'] else '',
                    '○' if commit['is_weekend'] else '',
                    '○' if commit['is_late_night'] else '',
                    commit['author_name']
                ])

        print(f"Saved to {filename}")

    def save_to_json(self, filename: str = 'github_commits_evidence.json'):
        """JSONファイルとして保存"""
        if not self.all_commits:
            print("No commits to save")
            return

        # datetime オブジェクトを文字列に変換
        commits_serializable = []
        for commit in self.all_commits:
            commit_copy = commit.copy()
            commit_copy['timestamp'] = commit['timestamp'].isoformat()
            commit_copy['timestamp_jst'] = commit['timestamp_jst'].isoformat()
            commit_copy['date'] = str(commit['date'])
            commit_copy['time'] = str(commit['time'])
            commits_serializable.append(commit_copy)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(commits_serializable, f, ensure_ascii=False, indent=2)

        print(f"Saved to {filename}")

    def generate_summary_report(self) -> Dict:
        """サマリーレポートを生成"""
        if not self.all_commits:
            return {}

        total_commits = len(self.all_commits)
        overtime_commits = [c for c in self.all_commits if c['is_overtime']]
        weekend_commits = [c for c in self.all_commits if c['is_weekend']]
        late_night_commits = [c for c in self.all_commits if c['is_late_night']]

        # 月別集計
        monthly_stats = {}
        for commit in self.all_commits:
            month_key = commit['timestamp_jst'].strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'total': 0,
                    'overtime': 0,
                    'weekend': 0,
                    'late_night': 0,
                    'projects': set()
                }

            monthly_stats[month_key]['total'] += 1
            if commit['is_overtime']:
                monthly_stats[month_key]['overtime'] += 1
            if commit['is_weekend']:
                monthly_stats[month_key]['weekend'] += 1
            if commit['is_late_night']:
                monthly_stats[month_key]['late_night'] += 1
            monthly_stats[month_key]['projects'].add(commit['repo_name'])

        # プロジェクト別集計
        project_stats = {}
        for commit in self.all_commits:
            project_key = f"{commit['repo_owner']}/{commit['repo_name']}"
            if project_key not in project_stats:
                project_stats[project_key] = 0
            project_stats[project_key] += 1

        summary = {
            'total_commits': total_commits,
            'overtime_commits': len(overtime_commits),
            'weekend_commits': len(weekend_commits),
            'late_night_commits': len(late_night_commits),
            'overtime_percentage': len(overtime_commits) / total_commits * 100 if total_commits > 0 else 0,
            'date_range': {
                'start': str(self.all_commits[0]['date']),
                'end': str(self.all_commits[-1]['date'])
            },
            'accounts_analyzed': list(set([c['account'] for c in self.all_commits])),
            'total_projects': len(set([c['repo_name'] for c in self.all_commits])),
            'monthly_breakdown': {k: {**v, 'projects': len(v['projects'])} for k, v in monthly_stats.items()},
            'top_projects': dict(sorted(project_stats.items(), key=lambda x: x[1], reverse=True)[:10])
        }

        return summary

    def print_summary(self):
        """サマリーを表示"""
        summary = self.generate_summary_report()

        print("\n" + "="*60)
        print("GitHub Commit History Analysis - Summary Report")
        print("="*60)
        print(f"\n【分析対象期間】")
        print(f"  開始: {summary['date_range']['start']}")
        print(f"  終了: {summary['date_range']['end']}")
        print(f"\n【分析対象アカウント】")
        for account in summary['accounts_analyzed']:
            print(f"  - {account}")
        print(f"\n【総合統計】")
        print(f"  総コミット数: {summary['total_commits']:,} 件")
        print(f"  時間外コミット数: {summary['overtime_commits']:,} 件 ({summary['overtime_percentage']:.1f}%)")
        print(f"  深夜コミット数: {summary['late_night_commits']:,} 件")
        print(f"  休日コミット数: {summary['weekend_commits']:,} 件")
        print(f"  総プロジェクト数: {summary['total_projects']} 個")
        print(f"\n【月別サマリー（時間外労働）】")
        for month, stats in sorted(summary['monthly_breakdown'].items()):
            print(f"  {month}: 時間外 {stats['overtime']:3d}件 / 休日 {stats['weekend']:3d}件 / 深夜 {stats['late_night']:3d}件")
        print(f"\n【コミット数TOP10プロジェクト】")
        for project, count in summary['top_projects'].items():
            print(f"  {project}: {count:,} 件")
        print("="*60 + "\n")

        # サマリーをJSONで保存
        with open('github_commits_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print("Summary saved to github_commits_summary.json")


def main():
    """メイン実行関数"""
    print("GitHub Commit History Analyzer")
    print("="*60)

    # 設定ファイルから読み込むか、直接入力
    # セキュリティのため、環境変数から読み込むことを推奨

    # 方法1: 環境変数から読み込み
    token1 = os.getenv('GITHUB_TOKEN_1')
    token2 = os.getenv('GITHUB_TOKEN_2')
    username1 = os.getenv('GITHUB_USERNAME_1')
    username2 = os.getenv('GITHUB_USERNAME_2')

    # 方法2: 設定ファイルから読み込み
    config_file = 'github_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            tokens = config.get('tokens', [])
            usernames = config.get('usernames', [])
    elif token1 and token2:
        tokens = [token1, token2]
        usernames = [username1, username2]
    else:
        print("\nConfiguration not found. Please create github_config.json:")
        print("""
{
  "tokens": [
    "ghp_your_token_1_here",
    "ghp_your_token_2_here"
  ],
  "usernames": [
    "username1",
    "username2"
  ]
}
        """)
        return

    if not tokens:
        print("Error: No GitHub tokens configured")
        return

    # アナライザー実行
    analyzer = GitHubCommitAnalyzer(tokens)

    print(f"\nCollecting commits from {len(usernames)} accounts...")
    analyzer.collect_all_commits(usernames)

    # サマリー表示
    analyzer.print_summary()

    # ファイルに保存
    analyzer.save_to_csv('github_commits_evidence.csv')
    analyzer.save_to_json('github_commits_evidence.json')

    print("\n✓ Analysis complete!")
    print("\nGenerated files:")
    print("  - github_commits_evidence.csv (Excel/Djangoインポート用)")
    print("  - github_commits_evidence.json (詳細データ)")
    print("  - github_commits_summary.json (サマリーレポート)")


if __name__ == '__main__':
    main()
