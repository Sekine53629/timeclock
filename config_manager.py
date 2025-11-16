"""
設定ファイル管理モジュール
Google Drive上のデータベース配置とアカウント名を管理
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional


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

    @staticmethod
    def get_application_path() -> Path:
        """
        アプリケーションの実行ファイルがあるディレクトリを取得
        PyInstallerでエグゼ化した場合にも対応

        Returns:
            アプリケーションディレクトリのPath
        """
        if getattr(sys, 'frozen', False):
            # PyInstallerでエグゼ化されている場合
            application_path = Path(sys.executable).parent
        else:
            # 通常のPythonスクリプトとして実行されている場合
            application_path = Path(__file__).parent
        return application_path

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
                    config['db_path'] = os.path.expanduser(config['db_path'])
                return config
        except (json.JSONDecodeError, IOError):
            return self._get_default_config()

    def save(self, config: Dict):
        """
        設定ファイルを保存

        Args:
            config: 保存する設定辞書
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _get_default_config(self) -> Dict:
        """
        デフォルト設定を返す

        Returns:
            デフォルト設定辞書（プログラムフォルダ内のdbフォルダを使用）
        """
        # プログラムフォルダ内のdbフォルダをデフォルトとする
        app_path = self.get_application_path()
        default_db_path = app_path / 'db'

        return {
            'db_path': str(default_db_path),
            'default_account': 'testUser'
        }

    def get_db_path(self) -> str:
        """
        データベース保存先のパスを取得

        Returns:
            データベースディレクトリのパス
        """
        config = self.load()
        # デフォルトはプログラムフォルダ内のdbフォルダ
        default_path = self._get_default_config()['db_path']
        db_path = config.get('db_path', default_path)

        # DBフォルダが存在しない場合は作成し、初期データを配置
        self._initialize_db_folder(db_path)

        return db_path

    def _initialize_db_folder(self, db_path: str):
        """
        DBフォルダを初期化し、デフォルトのconfig.jsonを作成

        Args:
            db_path: データベースフォルダのパス
        """
        db_folder = Path(db_path)
        config_file = db_folder / 'config.json'

        # フォルダが存在しない場合は作成
        db_folder.mkdir(parents=True, exist_ok=True)

        # config.jsonが存在しない場合はテスト用のデフォルトを作成
        if not config_file.exists():
            default_config = {
                "accounts": {
                    "testUser": {
                        "closing_day": 31,
                        "standard_hours_per_day": 8
                    }
                },
                "users": [
                    "testUser"
                ]
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)

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
        config['db_path'] = db_path
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

        # 現在の設定を表示
        current_config = self.load()
        print(f"現在の設定:")
        print(f"  データベース保存先: {current_config.get('db_path', '未設定')}")
        print(f"  デフォルトアカウント: {current_config.get('default_account', '未設定')}")
        print()

        # データベース保存先の設定
        print("データベースの保存先を設定してください。")
        print("例: ~/Google Drive/timeclock")
        print("   （Macの場合: /Users/username/Google Drive/timeclock）")
        print("   （Windowsの場合: C:\\Users\\username\\Google Drive\\timeclock）")
        print()

        db_path_input = input(f"保存先パス [{current_config.get('db_path')}]: ").strip()
        if db_path_input:
            db_path = os.path.expanduser(db_path_input)
        else:
            db_path = current_config.get('db_path')

        # デフォルトアカウントの設定
        print()
        print("デフォルトアカウント名を設定してください（省略可）。")
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
        print("この設定は ~/.timeclockrc に保存されています。")
        print()
