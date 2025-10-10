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
                'current_session': None  # 現在の作業セッション
            }

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {'accounts': {}, 'current_session': None}

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

    def set_current_session(self, session: Optional[Dict]):
        """現在の作業セッションを設定"""
        data = self.load_data()
        data['current_session'] = session
        self.save_data(data)

    def get_current_session(self) -> Optional[Dict]:
        """現在の作業セッションを取得"""
        data = self.load_data()
        return data.get('current_session')

    def list_accounts(self) -> List[str]:
        """登録されている全アカウントのリストを取得"""
        data = self.load_data()
        return list(data['accounts'].keys())

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
                'accounts': {}  # アカウントごとの設定
            }

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {'accounts': {}}

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
        if closing_day not in [15, 31]:
            raise ValueError("締め日は15日または31日のみ指定可能です")

        config = self.load_config()
        config['accounts'][account] = {
            'closing_day': closing_day,
            'standard_hours_per_day': standard_hours_per_day
        }
        self.save_config(config)
