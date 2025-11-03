"""
編集ログ記録モジュール
打刻レコードの編集履歴を管理
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from file_lock import FileLock, FileBackup


class EditLog:
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
        self.log_file = self.data_dir / 'edit_log.json'
        self.lock_file = self.data_dir / '.timeclock.lock'

    def load_logs(self) -> List[Dict]:
        """全ての編集ログを読み込み"""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_logs(self, logs: List[Dict]):
        """ログを保存（ロック・バックアップ付き）"""
        # バックアップを作成
        FileBackup.create_backup(self.log_file)

        # ロックを取得して保存
        with FileLock(str(self.lock_file)):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

    def add_edit_log(self, account: str, record_id: str, action: str,
                     before: Optional[Dict], after: Optional[Dict],
                     reason: str = "", editor: Optional[str] = None):
        """
        編集ログを追加

        Args:
            account: アカウント名
            record_id: レコードID（日付+開始時刻のハッシュなど）
            action: 操作種別（'create', 'edit', 'delete', 'submit'）
            before: 変更前のデータ
            after: 変更後のデータ
            reason: 変更理由
            editor: 編集者（未指定時はaccount）
        """
        logs = self.load_logs()

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'account': account,
            'record_id': record_id,
            'action': action,
            'before': before,
            'after': after,
            'reason': reason,
            'editor': editor or account
        }

        logs.append(log_entry)
        self.save_logs(logs)

    def get_logs_by_account(self, account: str) -> List[Dict]:
        """指定アカウントの編集ログを取得"""
        logs = self.load_logs()
        return [log for log in logs if log.get('account') == account]

    def get_logs_by_record(self, record_id: str) -> List[Dict]:
        """指定レコードの編集ログを取得"""
        logs = self.load_logs()
        return [log for log in logs if log.get('record_id') == record_id]

    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """最近の編集ログを取得"""
        logs = self.load_logs()
        # 新しい順にソート
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return logs[:limit]

    def generate_record_id(self, record: Dict) -> str:
        """
        レコードから一意のIDを生成

        Args:
            record: レコード情報

        Returns:
            レコードID
        """
        # 日付と開始時刻を組み合わせてIDとする
        date = record.get('date', '')
        start_time = record.get('start_time', '')
        account = record.get('account', '')
        # ISO形式のタイムスタンプからシンプルな文字列に
        start_simple = start_time.replace(':', '').replace('-', '').replace('T', '_')
        return f"{account}_{date}_{start_simple}"
