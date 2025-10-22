"""
データ保存・読み込みモジュール
JSON形式で打刻データを永続化
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from file_lock import FileLock, FileBackup

class Storage:
    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: データ保存ディレクトリ（指定なしの場合はホームディレクトリ）
        """
        if data_dir is None:
            self.data_dir = Path.home() / '.timeclock'
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / 'timeclock_data.json'
        self.config_file = self.data_dir / 'config.json'
        self.lock_file = self.data_dir / '.timeclock.lock'

    def load_data(self) -> Dict:
        """全データを読み込み"""
        if not self.data_file.exists():
            return {
                'accounts': {},  # アカウント別のデータ
                'current_sessions': {}  # アカウント別の現在の作業セッション
            }

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 旧形式（current_session）から新形式（current_sessions）への移行
                if 'current_session' in data and 'current_sessions' not in data:
                    data['current_sessions'] = {}
                    if data['current_session']:
                        account = data['current_session'].get('account')
                        if account:
                            data['current_sessions'][account] = data['current_session']
                    del data['current_session']
                return data
        except json.JSONDecodeError:
            return {'accounts': {}, 'current_sessions': {}}

    def save_data(self, data: Dict):
        """データを保存（ロック・バックアップ付き）"""
        # バックアップを作成
        FileBackup.create_backup(self.data_file)

        # ロックを取得して保存
        with FileLock(str(self.lock_file)):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get_account_data(self, account: str) -> Dict:
        """指定アカウントのデータを取得"""
        data = self.load_data()
        if account not in data['accounts']:
            data['accounts'][account] = {
                'projects': {},
                'records': []
            }
            self.save_data(data)
        return data['accounts'][account]

    def add_record(self, account: str, record: Dict):
        """打刻レコードを追加"""
        data = self.load_data()
        if account not in data['accounts']:
            data['accounts'][account] = {'projects': {}, 'records': []}
        data['accounts'][account]['records'].append(record)
        self.save_data(data)

    def get_records(self, account: str, date: Optional[str] = None,
                   project: Optional[str] = None) -> List[Dict]:
        """
        レコードを取得

        Args:
            account: アカウント名
            date: 日付フィルタ（YYYY-MM-DD形式）
            project: プロジェクト名フィルタ
        """
        account_data = self.get_account_data(account)
        records = account_data['records']

        if date:
            records = [r for r in records if r.get('date') == date]

        if project:
            records = [r for r in records if r.get('project') == project]

        return records

    def set_current_session(self, session: Optional[Dict], account: Optional[str] = None):
        """
        現在の作業セッションを設定（アカウント別）

        Args:
            session: セッション情報（Noneの場合は削除）
            account: アカウント名（sessionがNoneでない場合は自動取得）
        """
        data = self.load_data()
        if 'current_sessions' not in data:
            data['current_sessions'] = {}

        if session is None:
            # セッション削除
            if account and account in data['current_sessions']:
                del data['current_sessions'][account]
        else:
            # セッション保存
            account = account or session.get('account')
            if account:
                data['current_sessions'][account] = session

        self.save_data(data)

    def get_current_session(self, account: Optional[str] = None) -> Optional[Dict]:
        """
        現在の作業セッションを取得

        Args:
            account: アカウント名（指定した場合は特定アカウントのセッションを取得）

        Returns:
            セッション情報（accountを指定しない場合は最初に見つかったセッション）
        """
        data = self.load_data()
        current_sessions = data.get('current_sessions', {})

        if account:
            # 特定のアカウントのセッションを取得
            return current_sessions.get(account)
        else:
            # 互換性のため、最初のセッションを返す
            if current_sessions:
                return next(iter(current_sessions.values()))
            return None

    def get_all_current_sessions(self) -> Dict[str, Dict]:
        """全アカウントの現在のセッションを取得"""
        data = self.load_data()
        return data.get('current_sessions', {})

    def list_accounts(self) -> List[str]:
        """
        登録されている全アカウントのリストを取得
        設定ファイルのユーザーリストと稼働履歴のあるアカウントを統合
        """
        data = self.load_data()
        config = self.load_config()

        # 稼働履歴があるアカウント（文字列として明示的に変換）
        active_accounts = set(str(k) for k in data['accounts'].keys())

        # 設定ファイルに登録されているユーザー（文字列として明示的に変換）
        registered_users = set(str(u) for u in config.get('users', []))

        # 両方を統合（重複排除）
        all_accounts = active_accounts | registered_users

        return sorted(list(all_accounts))

    def list_projects(self, account: str) -> List[str]:
        """指定アカウントの全プロジェクトのリストを取得"""
        account_data = self.get_account_data(account)
        projects = set()
        for record in account_data['records']:
            if 'project' in record:
                projects.add(record['project'])
        return sorted(list(projects))

    def load_config(self) -> Dict:
        """設定を読み込み"""
        if not self.config_file.exists():
            return {
                'accounts': {},  # アカウントごとの設定
                'users': []  # ユーザーリスト（新規追加）
            }

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 古い形式との互換性
                if 'users' not in config:
                    config['users'] = []
                return config
        except json.JSONDecodeError:
            return {'accounts': {}, 'users': []}

    def save_config(self, config: Dict):
        """設定を保存（ロック・バックアップ付き）"""
        # バックアップを作成
        FileBackup.create_backup(self.config_file)

        # ロックを取得して保存
        with FileLock(str(self.lock_file)):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

    def get_account_config(self, account: str) -> Dict:
        """
        アカウントの設定を取得

        Returns:
            設定辞書（closing_day: 締め日 15 or 31）
        """
        # 文字列として明示的に変換（数値の場合に先頭の0が消えないように）
        account = str(account)

        config = self.load_config()
        if account not in config['accounts']:
            # デフォルトは月末締め
            config['accounts'][account] = {
                'closing_day': 31,
                'standard_hours_per_day': 8
            }
            self.save_config(config)
        return config['accounts'][account]

    def set_account_config(self, account: str, closing_day: int,
                          standard_hours_per_day: int = 8):
        """
        アカウントの設定を保存

        Args:
            account: アカウント名
            closing_day: 締め日（15 or 31）
            standard_hours_per_day: 1日の標準労働時間
        """
        # 文字列として明示的に変換（数値の場合に先頭の0が消えないように）
        account = str(account)

        if closing_day not in [15, 31]:
            raise ValueError("締め日は15日または31日のみ指定可能です")

        config = self.load_config()
        config['accounts'][account] = {
            'closing_day': closing_day,
            'standard_hours_per_day': standard_hours_per_day
        }
        self.save_config(config)

    def get_registered_users(self) -> List[str]:
        """設定ファイルに登録されているユーザーリストを取得"""
        config = self.load_config()
        return config.get('users', [])

    def add_user(self, username: str):
        """
        ユーザーをリストに追加

        Args:
            username: ユーザー名
        """
        config = self.load_config()
        if 'users' not in config:
            config['users'] = []

        if username not in config['users']:
            config['users'].append(username)
            config['users'].sort()  # アルファベット順にソート
            self.save_config(config)

    def remove_user(self, username: str):
        """
        ユーザーをリストから削除

        Args:
            username: ユーザー名
        """
        config = self.load_config()
        if 'users' in config and username in config['users']:
            config['users'].remove(username)
            self.save_config(config)

    def get_user_info(self, username: str) -> Dict:
        """
        ユーザーの情報を取得

        Args:
            username: ユーザー名

        Returns:
            ユーザー情報の辞書
        """
        # 文字列として明示的に変換（数値の場合に先頭の0が消えないように）
        username = str(username)

        config = self.load_config()
        data = self.load_data()

        # 登録状態
        is_registered = username in config.get('users', [])

        # 稼働履歴の有無
        has_records = username in data['accounts']

        # 現在作業中かどうか
        is_working = username in data.get('current_sessions', {})

        # アカウント設定
        account_config = config.get('accounts', {}).get(username, {
            'closing_day': 31,
            'standard_hours_per_day': 8
        })

        # プロジェクト数
        project_count = 0
        record_count = 0
        if has_records:
            projects = self.list_projects(username)
            project_count = len(projects)
            records = self.get_records(username)
            record_count = len(records)

        return {
            'username': username,
            'is_registered': is_registered,
            'has_records': has_records,
            'is_working': is_working,
            'project_count': project_count,
            'record_count': record_count,
            'closing_day': account_config.get('closing_day', 31),
            'standard_hours_per_day': account_config.get('standard_hours_per_day', 8)
        }
