"""
ファイルロック機構
複数PCからの同時書き込みを防止
"""
import os
import time
from pathlib import Path
from typing import Optional


class FileLock:
    """
    簡易ファイルロック実装
    Google Driveなどのクラウドストレージ上でも動作する
    """

    def __init__(self, lock_file_path: str, timeout: int = 10):
        """
        Args:
            lock_file_path: ロックファイルのパス
            timeout: ロック取得のタイムアウト秒数
        """
        self.lock_file_path = Path(lock_file_path)
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        """コンテキストマネージャー（with文）のエントリ"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー（with文）の終了"""
        self.release()

    def acquire(self):
        """
        ロックを取得

        Raises:
            TimeoutError: タイムアウト時
        """
        start_time = time.time()

        while True:
            try:
                # 排他的にファイルを作成（既に存在する場合は失敗）
                fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

                # ロックファイルにプロセスIDと取得時刻を書き込む
                lock_info = f"PID: {os.getpid()}\nTime: {time.time()}\n"
                os.write(fd, lock_info.encode('utf-8'))
                os.close(fd)

                self.acquired = True
                return

            except FileExistsError:
                # ロックファイルが既に存在する場合
                elapsed = time.time() - start_time

                if elapsed >= self.timeout:
                    # タイムアウト: 古いロックファイルをチェック
                    if self._is_stale_lock():
                        # 古いロックなら削除して再試行
                        self._force_release()
                        continue
                    else:
                        raise TimeoutError(
                            f"ロックの取得がタイムアウトしました ({self.timeout}秒)。\n"
                            f"別のプロセスがデータベースを使用中の可能性があります。\n"
                            f"しばらく待ってから再度お試しください。"
                        )

                # 少し待ってから再試行
                time.sleep(0.1)

    def release(self):
        """ロックを解放"""
        if self.acquired:
            try:
                self.lock_file_path.unlink(missing_ok=True)
                self.acquired = False
            except Exception:
                # ロック解放に失敗しても続行
                pass

    def _is_stale_lock(self, max_age: int = 60) -> bool:
        """
        ロックファイルが古いかどうかをチェック

        Args:
            max_age: ロックの最大有効期間（秒）

        Returns:
            古いロックの場合True
        """
        try:
            if not self.lock_file_path.exists():
                return True

            # ロックファイルの更新時刻をチェック
            mtime = self.lock_file_path.stat().st_mtime
            age = time.time() - mtime

            return age > max_age

        except Exception:
            # エラーの場合は保守的に古くないと判定
            return False

    def _force_release(self):
        """強制的にロックを解放（古いロックファイルの削除）"""
        try:
            self.lock_file_path.unlink(missing_ok=True)
        except Exception:
            pass


class FileBackup:
    """
    ファイルの自動バックアップ機能
    操作前にバックアップを作成し、データ損失を防止
    """

    @staticmethod
    def create_backup(file_path: Path, max_backups: int = 5) -> Optional[Path]:
        """
        バックアップファイルを作成

        Args:
            file_path: バックアップ対象のファイル
            max_backups: 保持する最大バックアップ数

        Returns:
            作成したバックアップファイルのパス（ファイルが存在しない場合はNone）
        """
        if not file_path.exists():
            return None

        # タイムスタンプ付きバックアップファイル名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.parent / f"{file_path.name}.backup_{timestamp}"

        # バックアップを作成
        try:
            import shutil
            shutil.copy2(file_path, backup_path)

            # 古いバックアップを削除
            FileBackup._cleanup_old_backups(file_path, max_backups)

            return backup_path

        except Exception:
            # バックアップ作成に失敗しても続行
            return None

    @staticmethod
    def _cleanup_old_backups(original_file: Path, max_backups: int):
        """
        古いバックアップファイルを削除

        Args:
            original_file: 元のファイル
            max_backups: 保持する最大バックアップ数
        """
        try:
            # バックアップファイルを検索
            backup_pattern = f"{original_file.name}.backup_*"
            backup_files = list(original_file.parent.glob(backup_pattern))

            # 更新時刻でソート（新しい順）
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # max_backups より古いファイルを削除
            for old_backup in backup_files[max_backups:]:
                old_backup.unlink(missing_ok=True)

        except Exception:
            # クリーンアップに失敗しても続行
            pass

    @staticmethod
    def list_backups(file_path: Path) -> list:
        """
        バックアップファイルの一覧を取得

        Args:
            file_path: 元のファイル

        Returns:
            バックアップファイルのリスト（新しい順）
        """
        try:
            backup_pattern = f"{file_path.name}.backup_*"
            backup_files = list(file_path.parent.glob(backup_pattern))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return backup_files
        except Exception:
            return []
