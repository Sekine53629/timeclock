#!/usr/bin/env python3
"""
ロギング設定モジュール
アプリケーション全体で統一されたログ出力を提供
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class TimeclockLogger:
    """タイムクロックアプリケーション用のロガー"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.setup_logging()

    def setup_logging(self):
        """ロギングの設定"""
        # ログディレクトリの作成
        log_dir = Path.home() / '.timeclock'
        log_dir.mkdir(parents=True, exist_ok=True)

        # ログファイルのパス
        log_file = log_dir / 'timeclock.log'

        # ルートロガーの設定
        logger = logging.getLogger('timeclock')
        logger.setLevel(logging.DEBUG)

        # 既存のハンドラをクリア
        logger.handlers.clear()

        # ファイルハンドラ（詳細ログ）
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # コンソールハンドラ（重要なログのみ）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 起動ログ
        logger.info("=" * 60)
        logger.info("タイムクロックアプリケーション起動")
        logger.info(f"ログファイル: {log_file}")
        logger.info("=" * 60)

    def get_logger(self, name: str = 'timeclock') -> logging.Logger:
        """
        ロガーを取得

        Args:
            name: ロガー名（モジュール名を推奨）

        Returns:
            ロガーインスタンス
        """
        return logging.getLogger(name)


# シングルトンインスタンス
_logger_instance = TimeclockLogger()


def get_logger(name: str = 'timeclock') -> logging.Logger:
    """
    ロガーを取得する便利関数

    Args:
        name: ロガー名

    Returns:
        ロガーインスタンス

    Example:
        >>> from logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("処理を開始しました")
    """
    return _logger_instance.get_logger(name)


def log_exception(logger: logging.Logger, message: str, exc: Exception):
    """
    例外情報を含むエラーログを出力

    Args:
        logger: ロガーインスタンス
        message: エラーメッセージ
        exc: 例外オブジェクト
    """
    logger.error(f"{message}: {type(exc).__name__}: {str(exc)}", exc_info=True)


if __name__ == '__main__':
    # テスト
    logger = get_logger(__name__)

    logger.debug("これはデバッグメッセージです")
    logger.info("これは情報メッセージです")
    logger.warning("これは警告メッセージです")
    logger.error("これはエラーメッセージです")

    try:
        1 / 0
    except Exception as e:
        log_exception(logger, "ゼロ除算エラー", e)

    print(f"\nログファイル: {Path.home() / '.timeclock' / 'timeclock.log'}")
