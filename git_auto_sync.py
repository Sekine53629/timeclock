#!/usr/bin/env python3
"""
Git自動同期モジュール
作業終了時と自動休憩時にGitの変更を自動的にpushする
"""
import subprocess
import os
from datetime import datetime
from pathlib import Path
from logger import get_logger, log_exception

logger = get_logger(__name__)


class GitAutoSync:
    """Git自動同期クラス"""

    def __init__(self, repo_path=None):
        """
        初期化

        Args:
            repo_path: Gitリポジトリのパス（Noneの場合は現在のディレクトリ）
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        logger.info(f"GitAutoSync初期化: {self.repo_path}")

    def set_repo_path(self, repo_path):
        """
        リポジトリパスを変更

        Args:
            repo_path: 新しいGitリポジトリのパス
        """
        self.repo_path = Path(repo_path)
        logger.info(f"GitAutoSyncリポジトリパス変更: {self.repo_path}")

    def _run_git_command(self, command, check=True):
        """
        Gitコマンドを実行

        Args:
            command: 実行するgitコマンド（リスト形式）
            check: エラー時に例外を発生させるか

        Returns:
            CompletedProcess: コマンド実行結果
        """
        try:
            # コマンド実行
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=check
            )
            logger.debug(f"Git command: {' '.join(command)}")
            logger.debug(f"Output: {result.stdout}")
            if result.stderr:
                logger.debug(f"Stderr: {result.stderr}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(command)}")
            logger.error(f"Error output: {e.stderr}")
            raise

    def has_changes(self):
        """
        変更があるかチェック

        Returns:
            bool: 変更がある場合True
        """
        try:
            result = self._run_git_command(['git', 'status', '--porcelain'])
            has_changes = bool(result.stdout.strip())
            logger.info(f"変更検出: {has_changes}")
            return has_changes
        except Exception as e:
            log_exception(logger, "変更検出エラー", e)
            return False

    def get_current_branch(self):
        """
        現在のブランチ名を取得

        Returns:
            str: ブランチ名
        """
        try:
            result = self._run_git_command(['git', 'branch', '--show-current'])
            branch = result.stdout.strip()
            logger.info(f"現在のブランチ: {branch}")
            return branch
        except Exception as e:
            log_exception(logger, "ブランチ取得エラー", e)
            return "main"

    def get_repo_name(self):
        """
        GitHubリポジトリ名を取得

        Returns:
            str: リポジトリ名（取得できない場合はNone）
        """
        try:
            result = self._run_git_command(['git', 'remote', 'get-url', 'origin'], check=False)
            if result.returncode != 0:
                logger.info("リモートリポジトリが設定されていません")
                return None

            remote_url = result.stdout.strip()
            # URLからリポジトリ名を抽出
            # 例: https://github.com/user/repo.git → repo
            # 例: git@github.com:user/repo.git → repo
            if remote_url:
                # .gitを削除
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                # 最後のスラッシュ以降を取得
                repo_name = remote_url.split('/')[-1]
                logger.info(f"リポジトリ名: {repo_name}")
                return repo_name

            return None
        except Exception as e:
            log_exception(logger, "リポジトリ名取得エラー", e)
            return None

    def commit_changes(self, message=None):
        """
        変更を自動コミット

        Args:
            message: コミットメッセージ（Noneの場合は自動生成）

        Returns:
            bool: コミット成功時True
        """
        try:
            if not self.has_changes():
                logger.info("コミットする変更がありません")
                return True

            # すべての変更をステージング
            self._run_git_command(['git', 'add', '-A'])

            # コミットメッセージの生成
            if message is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Auto-commit: {timestamp}"

            # コミット実行
            self._run_git_command(['git', 'commit', '-m', message])
            logger.info(f"変更をコミットしました: {message}")
            return True

        except Exception as e:
            log_exception(logger, "コミットエラー", e)
            return False

    def fetch_remote(self):
        """
        リモートの変更を取得

        Returns:
            bool: 成功時True
        """
        try:
            self._run_git_command(['git', 'fetch'])
            logger.info("リモートの変更を取得しました")
            return True
        except Exception as e:
            log_exception(logger, "fetch エラー", e)
            return False

    def has_remote_changes(self):
        """
        リモートに新しい変更があるかチェック

        Returns:
            bool: リモートに新しい変更がある場合True
        """
        try:
            branch = self.get_current_branch()
            result = self._run_git_command([
                'git', 'rev-list', '--count', f'HEAD..origin/{branch}'
            ], check=False)

            if result.returncode != 0:
                logger.warning("リモート変更チェック失敗（リモートブランチがない可能性）")
                return False

            count = int(result.stdout.strip())
            has_changes = count > 0
            logger.info(f"リモートの新しいコミット数: {count}")
            return has_changes

        except Exception as e:
            log_exception(logger, "リモート変更チェックエラー", e)
            return False

    def stash_changes(self):
        """
        変更をスタッシュ

        Returns:
            bool: スタッシュ成功時True（変更がない場合もTrue）
        """
        try:
            if not self.has_changes():
                logger.info("スタッシュする変更がありません")
                return True

            result = self._run_git_command(['git', 'stash', 'push', '-m', 'Auto-stash'])
            logger.info("変更をスタッシュしました")
            return True

        except Exception as e:
            log_exception(logger, "スタッシュエラー", e)
            return False

    def stash_pop(self):
        """
        スタッシュをポップ（復元）

        Returns:
            bool: 成功時True
        """
        try:
            # スタッシュがあるかチェック
            result = self._run_git_command(['git', 'stash', 'list'], check=False)
            if not result.stdout.strip():
                logger.info("スタッシュがありません")
                return True

            # スタッシュをポップ
            self._run_git_command(['git', 'stash', 'pop'], check=False)
            logger.info("スタッシュを復元しました")
            return True

        except Exception as e:
            log_exception(logger, "スタッシュpopエラー", e)
            return False

    def pull_with_rebase(self):
        """
        リモートの変更をrebaseで取り込む

        Returns:
            bool: 成功時True、コンフリクト時False
        """
        try:
            branch = self.get_current_branch()
            result = self._run_git_command([
                'git', 'pull', '--rebase', 'origin', branch
            ], check=False)

            if result.returncode != 0:
                # コンフリクトが発生した可能性
                logger.warning("Rebaseに失敗しました。コンフリクトの可能性があります。")
                # rebaseを中止
                self._run_git_command(['git', 'rebase', '--abort'], check=False)
                return False

            logger.info("Rebaseが成功しました")
            return True

        except Exception as e:
            log_exception(logger, "Pull rebaseエラー", e)
            # エラー時はrebaseを中止
            try:
                self._run_git_command(['git', 'rebase', '--abort'], check=False)
            except:
                pass
            return False

    def pull_with_merge(self):
        """
        リモートの変更をマージで取り込む

        Returns:
            bool: 成功時True
        """
        try:
            branch = self.get_current_branch()
            result = self._run_git_command([
                'git', 'pull', 'origin', branch
            ], check=False)

            if result.returncode != 0:
                logger.error("Mergeに失敗しました")
                return False

            logger.info("Mergeが成功しました")
            return True

        except Exception as e:
            log_exception(logger, "Pull mergeエラー", e)
            return False

    def push_changes(self):
        """
        変更をプッシュ

        Returns:
            bool: 成功時True
        """
        try:
            branch = self.get_current_branch()
            self._run_git_command(['git', 'push', 'origin', branch])
            logger.info("変更をプッシュしました")
            return True

        except Exception as e:
            log_exception(logger, "Pushエラー", e)
            return False

    def auto_sync(self, commit_message=None):
        """
        自動同期を実行

        変更のコミット → fetch → pull（rebase優先、失敗時はmerge） → push

        Args:
            commit_message: コミットメッセージ（Noneの場合は自動生成）

        Returns:
            tuple: (成功フラグ, メッセージ)
        """
        try:
            logger.info("=== Git自動同期開始 ===")

            # 1. ローカル変更をコミット
            if self.has_changes():
                logger.info("ステップ1: ローカル変更をコミット")
                if not self.commit_changes(commit_message):
                    return False, "ローカル変更のコミットに失敗しました"
            else:
                logger.info("ステップ1: コミットする変更がありません")

            # 2. リモートの変更を取得
            logger.info("ステップ2: リモートの変更を取得")
            if not self.fetch_remote():
                return False, "リモートの変更取得に失敗しました"

            # 3. リモートに新しい変更があるかチェック
            if self.has_remote_changes():
                logger.info("ステップ3: リモートに新しい変更があります")

                # 3-1. 変更をスタッシュ（念のため）
                has_local_changes = self.has_changes()
                if has_local_changes:
                    logger.info("ステップ3-1: 変更をスタッシュ")
                    if not self.stash_changes():
                        return False, "変更のスタッシュに失敗しました"

                # 3-2. Rebaseで取り込みを試行
                logger.info("ステップ3-2: Rebaseで取り込み試行")
                if self.pull_with_rebase():
                    logger.info("Rebase成功")
                else:
                    # Rebase失敗時はマージで取り込み
                    logger.info("Rebaseに失敗、Mergeで取り込み試行")
                    if not self.pull_with_merge():
                        return False, "リモート変更の取り込みに失敗しました"

                # 3-3. スタッシュを復元
                if has_local_changes:
                    logger.info("ステップ3-3: スタッシュを復元")
                    if not self.stash_pop():
                        logger.warning("スタッシュの復元に失敗しました（手動で確認してください）")
            else:
                logger.info("ステップ3: リモートに新しい変更はありません")

            # 4. プッシュ
            logger.info("ステップ4: プッシュ")
            if not self.push_changes():
                return False, "プッシュに失敗しました"

            logger.info("=== Git自動同期完了 ===")
            return True, "Git自動同期が成功しました"

        except Exception as e:
            log_exception(logger, "Git自動同期エラー", e)
            return False, f"Git自動同期エラー: {str(e)}"


def sync_git_changes(commit_message=None):
    """
    Git変更を自動同期する便利関数

    Args:
        commit_message: コミットメッセージ（Noneの場合は自動生成）

    Returns:
        tuple: (成功フラグ, メッセージ)
    """
    git_sync = GitAutoSync()
    return git_sync.auto_sync(commit_message)


if __name__ == "__main__":
    # テスト実行
    success, message = sync_git_changes("テスト: Git自動同期")
    print(f"結果: {message}")
