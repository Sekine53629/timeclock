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
from edit_log import EditLog

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
        self.edit_log = EditLog(data_dir)

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

    def update_record(self, account: str, record_index: int, updated_record: Dict,
                     reason: str = "", editor: Optional[str] = None) -> bool:
        """
        レコードを更新

        Args:
            account: アカウント名
            record_index: レコードのインデックス
            updated_record: 更新後のレコード
            reason: 変更理由
            editor: 編集者（未指定時はaccount）

        Returns:
            成功した場合True
        """
        data = self.load_data()
        if account not in data['accounts']:
            return False

        records = data['accounts'][account]['records']
        if record_index < 0 or record_index >= len(records):
            return False

        # 変更前のレコードを保存
        before = records[record_index].copy()

        # レコードIDを生成
        record_id = self.edit_log.generate_record_id(before)

        # レコードを更新
        records[record_index] = updated_record

        # 申請状態を「編集済み」に設定
        if 'submission_status' not in updated_record:
            records[record_index]['submission_status'] = 'edited'

        self.save_data(data)

        # 編集ログを記録
        self.edit_log.add_edit_log(
            account=account,
            record_id=record_id,
            action='edit',
            before=before,
            after=updated_record,
            reason=reason,
            editor=editor
        )

        return True

    def delete_record(self, account: str, record_index: int,
                     reason: str = "", editor: Optional[str] = None) -> bool:
        """
        レコードを削除

        Args:
            account: アカウント名
            record_index: レコードのインデックス
            reason: 削除理由
            editor: 編集者（未指定時はaccount）

        Returns:
            成功した場合True
        """
        data = self.load_data()
        if account not in data['accounts']:
            return False

        records = data['accounts'][account]['records']
        if record_index < 0 or record_index >= len(records):
            return False

        # 削除前のレコードを保存
        deleted_record = records[record_index].copy()

        # レコードIDを生成
        record_id = self.edit_log.generate_record_id(deleted_record)

        # レコードを削除
        del records[record_index]
        self.save_data(data)

        # 編集ログを記録
        self.edit_log.add_edit_log(
            account=account,
            record_id=record_id,
            action='delete',
            before=deleted_record,
            after=None,
            reason=reason,
            editor=editor
        )

        return True

    def submit_records(self, account: str, start_date: str, end_date: str,
                      reason: str = "", editor: Optional[str] = None) -> int:
        """
        指定期間のレコードを申請状態にする

        Args:
            account: アカウント名
            start_date: 開始日（YYYY-MM-DD形式）
            end_date: 終了日（YYYY-MM-DD形式）
            reason: 申請理由
            editor: 申請者（未指定時はaccount）

        Returns:
            申請したレコード数
        """
        data = self.load_data()
        if account not in data['accounts']:
            return 0

        records = data['accounts'][account]['records']
        submitted_count = 0

        for record in records:
            record_date = record.get('date', '')
            if start_date <= record_date <= end_date:
                # 申請状態を更新
                old_status = record.get('submission_status', 'none')
                record['submission_status'] = 'submitted'
                record['submission_date'] = datetime.now().isoformat()

                # 編集ログを記録
                record_id = self.edit_log.generate_record_id(record)
                self.edit_log.add_edit_log(
                    account=account,
                    record_id=record_id,
                    action='submit',
                    before={'submission_status': old_status},
                    after={'submission_status': 'submitted'},
                    reason=reason,
                    editor=editor
                )

                submitted_count += 1

        self.save_data(data)
        return submitted_count

    def get_edit_logs(self, account: Optional[str] = None,
                     record_id: Optional[str] = None,
                     limit: int = 50) -> List[Dict]:
        """
        編集ログを取得

        Args:
            account: アカウント名（指定時はそのアカウントのログのみ）
            record_id: レコードID（指定時はそのレコードのログのみ）
            limit: 取得件数

        Returns:
            編集ログのリスト
        """
        if record_id:
            return self.edit_log.get_logs_by_record(record_id)
        elif account:
            logs = self.edit_log.get_logs_by_account(account)
            return logs[-limit:]  # 最新のN件
        else:
            return self.edit_log.get_recent_logs(limit)

    def set_company_overtime(self, account: str, year: int, month: int, hours: float):
        """
        会社での打刻実績（時間外労働時間）を保存

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月、例: 11月期 = 10/16-11/15）
            hours: 会社打刻実績の時間外労働時間
        """
        config = self.load_config()

        if 'company_overtime_records' not in config:
            config['company_overtime_records'] = {}

        if account not in config['company_overtime_records']:
            config['company_overtime_records'][account] = {}

        # キーを "YYYY-MM" 形式で保存
        period_key = f"{year:04d}-{month:02d}"
        config['company_overtime_records'][account][period_key] = hours

        self.save_config(config)

    def get_company_overtime(self, account: str, year: int, month: int) -> float:
        """
        会社での打刻実績（時間外労働時間）を取得

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月）

        Returns:
            会社打刻実績の時間外労働時間（時間単位）、未設定の場合は0.0
        """
        config = self.load_config()

        if 'company_overtime_records' not in config:
            return 0.0

        if account not in config['company_overtime_records']:
            return 0.0

        period_key = f"{year:04d}-{month:02d}"
        return config['company_overtime_records'][account].get(period_key, 0.0)

    def get_all_company_overtime(self, account: str) -> Dict[str, float]:
        """
        指定アカウントの全ての会社打刻実績を取得

        Args:
            account: アカウント名

        Returns:
            {"YYYY-MM": hours, ...} の辞書
        """
        config = self.load_config()

        if 'company_overtime_records' not in config:
            return {}

        return config['company_overtime_records'].get(account, {})

    def set_shift_total_hours(self, account: str, year: int, month: int, hours: float):
        """
        月ごとのシフト総労働時間を保存

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月、例: 11月期 = 10/16-11/15）
            hours: シフトの総労働時間
        """
        config = self.load_config()

        if 'shift_total_hours' not in config:
            config['shift_total_hours'] = {}

        if account not in config['shift_total_hours']:
            config['shift_total_hours'][account] = {}

        # キーを "YYYY-MM" 形式で保存
        period_key = f"{year:04d}-{month:02d}"
        config['shift_total_hours'][account][period_key] = hours

        self.save_config(config)

    def get_shift_total_hours(self, account: str, year: int, month: int) -> float:
        """
        月ごとのシフト総労働時間を取得

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月）

        Returns:
            シフトの総労働時間（時間単位）、未設定の場合は0.0
        """
        config = self.load_config()

        if 'shift_total_hours' not in config:
            return 0.0

        if account not in config['shift_total_hours']:
            return 0.0

        period_key = f"{year:04d}-{month:02d}"
        return config['shift_total_hours'][account].get(period_key, 0.0)

    def get_all_shift_total_hours(self, account: str) -> Dict[str, float]:
        """
        指定アカウントの全てのシフト総労働時間を取得

        Args:
            account: アカウント名

        Returns:
            {"YYYY-MM": hours, ...} の辞書
        """
        config = self.load_config()

        if 'shift_total_hours' not in config:
            return {}

        return config['shift_total_hours'].get(account, {})

    def set_project_main_job_flag(self, account: str, project: str, is_main_job: bool):
        """
        プロジェクトが本職の勤務時間に含まれるかどうかを設定

        Args:
            account: アカウント名
            project: プロジェクト名
            is_main_job: 本職の勤務時間に含める場合True
        """
        config = self.load_config()

        if 'project_settings' not in config:
            config['project_settings'] = {}

        if account not in config['project_settings']:
            config['project_settings'][account] = {}

        if project not in config['project_settings'][account]:
            config['project_settings'][account][project] = {}

        config['project_settings'][account][project]['is_main_job'] = is_main_job

        self.save_config(config)

    def get_project_main_job_flag(self, account: str, project: str) -> bool:
        """
        プロジェクトが本職の勤務時間に含まれるかどうかを取得

        Args:
            account: アカウント名
            project: プロジェクト名

        Returns:
            本職の勤務時間に含める場合True、デフォルトはTrue
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return True  # デフォルトは本職に含める

        if account not in config['project_settings']:
            return True

        project_settings = config['project_settings'][account].get(project, {})
        return project_settings.get('is_main_job', True)

    def set_project_git_repo_path(self, account: str, project: str, git_repo_path: str = None):
        """
        プロジェクトのGitリポジトリパスを設定

        Args:
            account: アカウント名
            project: プロジェクト名
            git_repo_path: Gitリポジトリのパス（Noneの場合は設定を削除）
        """
        config = self.load_config()

        if 'project_settings' not in config:
            config['project_settings'] = {}

        if account not in config['project_settings']:
            config['project_settings'][account] = {}

        if project not in config['project_settings'][account]:
            config['project_settings'][account][project] = {}

        if git_repo_path is None:
            # Noneの場合は削除
            if 'git_repo_path' in config['project_settings'][account][project]:
                del config['project_settings'][account][project]['git_repo_path']
        else:
            config['project_settings'][account][project]['git_repo_path'] = git_repo_path

        self.save_config(config)

    def get_project_git_repo_path(self, account: str, project: str) -> str:
        """
        プロジェクトのGitリポジトリパスを取得

        Args:
            account: アカウント名
            project: プロジェクト名

        Returns:
            Gitリポジトリのパス（未設定の場合はNone）
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return None

        if account not in config['project_settings']:
            return None

        project_settings = config['project_settings'][account].get(project, {})
        return project_settings.get('git_repo_path', None)

    def set_project_company(self, account: str, project: str, company: str = None):
        """
        プロジェクトの会社/クライアントを設定

        Args:
            account: アカウント名
            project: プロジェクト名
            company: 会社/クライアント名（Noneの場合は設定を削除）
        """
        config = self.load_config()

        if 'project_settings' not in config:
            config['project_settings'] = {}

        if account not in config['project_settings']:
            config['project_settings'][account] = {}

        if project not in config['project_settings'][account]:
            config['project_settings'][account][project] = {}

        if company is None:
            # Noneの場合は削除
            if 'company' in config['project_settings'][account][project]:
                del config['project_settings'][account][project]['company']
        else:
            config['project_settings'][account][project]['company'] = company

        self.save_config(config)

    def get_project_company(self, account: str, project: str) -> str:
        """
        プロジェクトの会社/クライアントを取得

        Args:
            account: アカウント名
            project: プロジェクト名

        Returns:
            会社/クライアント名（未設定の場合はNone）
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return None

        if account not in config['project_settings']:
            return None

        project_settings = config['project_settings'][account].get(project, {})
        return project_settings.get('company', None)

    def list_companies(self, account: str) -> List[str]:
        """
        指定アカウントの全ての会社/クライアント名を取得

        Args:
            account: アカウント名

        Returns:
            会社/クライアント名のリスト（重複なし）
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return []

        if account not in config['project_settings']:
            return []

        companies = set()
        for project_settings in config['project_settings'][account].values():
            if isinstance(project_settings, dict) and 'company' in project_settings:
                companies.add(project_settings['company'])

        return sorted(list(companies))

    def list_projects_by_company(self, account: str, company: str) -> List[str]:
        """
        指定会社/クライアントに属するプロジェクトのリストを取得

        Args:
            account: アカウント名
            company: 会社/クライアント名

        Returns:
            プロジェクト名のリスト
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return []

        if account not in config['project_settings']:
            return []

        projects = []
        for project_name, project_settings in config['project_settings'][account].items():
            if isinstance(project_settings, dict):
                if project_settings.get('company') == company:
                    projects.append(project_name)

        return sorted(projects)

    def get_all_project_settings(self, account: str) -> Dict[str, Dict]:
        """
        指定アカウントの全てのプロジェクト設定を取得

        Args:
            account: アカウント名

        Returns:
            {"project_name": {"is_main_job": bool}, ...} の辞書
        """
        config = self.load_config()

        if 'project_settings' not in config:
            return {}

        return config['project_settings'].get(account, {})
