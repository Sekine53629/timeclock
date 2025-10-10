"""
設定ファイル管理モジュール
Google Drive上のデータベース配置とアカウント名を管理
Mac/Windows/Linux対応版
"""
import json
import os
import platform
from pathlib import Path
from typing import Dict, Optional, List


class ConfigManager:
    """
    グローバル設定を管理するクラス
    - データベースの保存先（Google Driveパス）
    - デフォルトアカウント名
    """

    DEFAULT_CONFIG_PATH = Path.home() / '.timeclockrc'

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: 設定ファイルのパス（省略時はホームディレクトリの.timeclockrc）
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.system = platform.system()

    def load(self) -> Dict:
        """
        設定ファイルを読み込む

        Returns:
            設定辞書 {
                'db_path': データベースディレクトリのパス,
                'default_account': デフォルトアカウント名（オプション）
            }
        """
        if not self.config_path.exists():
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # パスを展開（~やシンボリックリンクを解決）
                if 'db_path' in config:
                    config['db_path'] = str(Path(os.path.expanduser(config['db_path'])).resolve())
                return config
        except (json.JSONDecodeError, IOError):
            return self._get_default_config()

    def save(self, config: Dict):
        """
        設定ファイルを保存

        Args:
            config: 保存する設定辞書
        """
        # パスをプラットフォーム固有の形式で保存
        save_config = config.copy()
        if 'db_path' in save_config:
            # ~/ 形式で保存することで可搬性を確保
            path = Path(save_config['db_path'])
            home = Path.home()
            try:
                rel_path = path.relative_to(home)
                save_config['db_path'] = f"~/{rel_path.as_posix()}"
            except ValueError:
                # ホームディレクトリ外の場合は絶対パスで保存
                save_config['db_path'] = str(path)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(save_config, f, ensure_ascii=False, indent=2)

    def _get_default_config(self) -> Dict:
        """
        デフォルト設定を返す

        Returns:
            デフォルト設定辞書（ローカルのホームディレクトリを使用）
        """
        return {
            'db_path': str(Path.home() / '.timeclock'),
            'default_account': None
        }

    def _detect_google_drive_paths(self) -> List[str]:
        """
        プラットフォーム別にGoogle Driveの可能性があるパスを検出

        Returns:
            検出されたGoogle Driveパスのリスト
        """
        home = Path.home()
        paths = []

        if self.system == "Darwin":  # macOS
            # 新しいGoogle Drive for desktop
            cloud_storage = home / "Library" / "CloudStorage"
            if cloud_storage.exists():
                for item in cloud_storage.iterdir():
                    if item.is_dir() and item.name.startswith("GoogleDrive-"):
                        my_drive = item / "My Drive"
                        if my_drive.exists():
                            paths.append(str(my_drive / "timeclock"))

            # 古いBackup and Sync
            old_path = home / "Google Drive"
            if old_path.exists():
                # My Drive フォルダがある場合
                if (old_path / "My Drive").exists():
                    paths.append(str(old_path / "My Drive" / "timeclock"))
                else:
                    paths.append(str(old_path / "timeclock"))

        elif self.system == "Windows":
            # Gドライブとしてマウントされている場合
            g_drive = Path("G:/")
            if g_drive.exists():
                if (g_drive / "My Drive").exists():
                    paths.append(str(g_drive / "My Drive" / "timeclock"))
                else:
                    paths.append(str(g_drive / "timeclock"))

            # 通常のGoogle Driveフォルダ
            google_drive = home / "Google Drive"
            if google_drive.exists():
                if (google_drive / "My Drive").exists():
                    paths.append(str(google_drive / "My Drive" / "timeclock"))
                else:
                    paths.append(str(google_drive / "timeclock"))

        else:  # Linux
            google_drive = home / "Google Drive"
            if google_drive.exists():
                paths.append(str(google_drive / "timeclock"))

        # デフォルトのローカルパス
        paths.append(str(home / "Documents" / "timeclock"))
        paths.append(str(home / ".timeclock"))

        return paths

    def get_db_path(self) -> str:
        """
        データベース保存先のパスを取得

        Returns:
            データベースディレクトリのパス
        """
        config = self.load()
        return config.get('db_path', str(Path.home() / '.timeclock'))

    def get_default_account(self) -> Optional[str]:
        """
        デフォルトアカウント名を取得

        Returns:
            デフォルトアカウント名（未設定時はNone）
        """
        config = self.load()
        return config.get('default_account')

    def set_db_path(self, db_path: str):
        """
        データベース保存先を設定

        Args:
            db_path: Google Driveなどのパス
        """
        config = self.load()
        config['db_path'] = str(Path(os.path.expanduser(db_path)).resolve())
        self.save(config)

    def set_default_account(self, account: str):
        """
        デフォルトアカウントを設定

        Args:
            account: アカウント名
        """
        config = self.load()
        config['default_account'] = account
        self.save(config)

    def setup_interactive(self):
        """
        対話的にセットアップを実行
        """
        print("=" * 60)
        print("打刻システム - 初期設定")
        print("=" * 60)
        print()

        # システム情報を表示
        print(f"検出されたOS: {self.system}")
        if self.system == "Darwin":
            print("  macOS環境です")
        elif self.system == "Windows":
            print("  Windows環境です")
        else:
            print("  Linux/Unix環境です")
        print()

        # 現在の設定を表示
        current_config = self.load()
        print(f"現在の設定:")
        print(f"  データベース保存先: {current_config.get('db_path', '未設定')}")
        print(f"  デフォルトアカウント: {current_config.get('default_account', '未設定')}")
        print()

        # Google Driveパスの自動検出
        detected_paths = self._detect_google_drive_paths()

        print("データベースの保存先を設定してください。")
        print()
        print("検出された候補:")
        for i, path in enumerate(detected_paths, 1):
            # パスが実際に存在するかチェック
            path_obj = Path(path).parent
            if path_obj.exists():
                print(f"  {i}. {path} ✓")
            else:
                print(f"  {i}. {path}")

        print()
        print("番号を入力するか、カスタムパスを直接入力してください。")
        print("例: ~/Google Drive/My Drive/timeclock")
        print()

        db_path_input = input(f"保存先パス [{current_config.get('db_path')}]: ").strip()

        if db_path_input:
            # 数字が入力された場合は候補から選択
            if db_path_input.isdigit():
                index = int(db_path_input) - 1
                if 0 <= index < len(detected_paths):
                    db_path = detected_paths[index]
                else:
                    print("無効な番号です。デフォルトを使用します。")
                    db_path = current_config.get('db_path')
            else:
                # カスタムパスを展開
                db_path = str(Path(os.path.expanduser(db_path_input)).resolve())
        else:
            db_path = current_config.get('db_path')

        # デフォルトアカウントの設定
        print()
        print("デフォルトアカウント名を設定してください（省略可）。")
        print("複数のアカウント（仕事用/個人用など）を使い分ける場合に便利です。")
        default_account_input = input(f"アカウント名 [{current_config.get('default_account', '')}]: ").strip()
        if default_account_input:
            default_account = default_account_input
        else:
            default_account = current_config.get('default_account')

        # 設定を保存
        new_config = {
            'db_path': db_path,
            'default_account': default_account
        }
        self.save(new_config)

        # 保存先ディレクトリを作成
        Path(db_path).mkdir(parents=True, exist_ok=True)

        print()
        print("=" * 60)
        print("✓ 設定が完了しました")
        print("=" * 60)
        print(f"データベース保存先: {db_path}")
        if default_account:
            print(f"デフォルトアカウント: {default_account}")
        print()
        print(f"設定ファイル: {self.config_path}")

        # 同期の確認
        if "Google Drive" in db_path or "GoogleDrive" in db_path:
            print()
            print("📌 Google Drive同期の確認:")
            print("  1. Google Drive デスクトップアプリが起動していることを確認")
            print("  2. 同期が完了するまで待機してください")
            if self.system == "Darwin":
                print("  3. Macの場合: メニューバーのGoogle Driveアイコンを確認")
            elif self.system == "Windows":
                print("  3. Windowsの場合: タスクトレイのGoogle Driveアイコンを確認")

        print()

    def verify_setup(self) -> bool:
        """
        設定が正しく行われているか確認

        Returns:
            設定が有効な場合True
        """
        config = self.load()
        db_path = config.get('db_path')

        if not db_path:
            print("❌ データベース保存先が設定されていません")
            return False

        path = Path(db_path)
        if not path.parent.exists():
            print(f"❌ 親ディレクトリが存在しません: {path.parent}")
            return False

        if not path.exists():
            print(f"📁 データベースディレクトリを作成します: {path}")
            path.mkdir(parents=True, exist_ok=True)

        # テストファイルの書き込み確認
        test_file = path / '.test_write'
        try:
            test_file.write_text('test')
            test_file.unlink()
            print(f"✅ データベース保存先への書き込み権限: OK")
            return True
        except Exception as e:
            print(f"❌ 書き込み権限エラー: {e}")
            return False


if __name__ == "__main__":
    # テスト実行
    manager = ConfigManager()
    manager.setup_interactive()
    manager.verify_setup()