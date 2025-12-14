#!/usr/bin/env python3
"""
各プロジェクトの.gitignoreにnulファイルを追加するスクリプト
"""
import json
import os
from pathlib import Path
from logger import get_logger

logger = get_logger(__name__)


def add_nul_to_gitignore(repo_path):
    """
    指定されたリポジトリの.gitignoreにnulを追加

    Args:
        repo_path: Gitリポジトリのパス

    Returns:
        bool: 追加した場合True、既に存在する場合False
    """
    gitignore_path = Path(repo_path) / ".gitignore"

    # .gitignoreが存在しない場合は作成
    if not gitignore_path.exists():
        logger.info(f".gitignoreが存在しないため作成: {gitignore_path}")
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write("# Windows command redirect artifacts\n")
            f.write("nul\n")
        return True

    # .gitignoreを読み込み
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 既にnulが含まれているかチェック
    lines = content.splitlines()
    if 'nul' in lines or '/nul' in lines or '**/nul' in lines:
        logger.info(f"既にnulが.gitignoreに含まれています: {gitignore_path}")
        return False

    # nulを追加
    if not content.endswith('\n'):
        content += '\n'

    content += '\n# Windows command redirect artifacts\n'
    content += 'nul\n'

    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f".gitignoreにnulを追加しました: {gitignore_path}")
    return True


def process_all_projects():
    """
    config.jsonから全プロジェクトのGitパスを読み込んで処理
    """
    config_path = Path(__file__).parent / "json" / "config.json"

    if not config_path.exists():
        print(f"config.jsonが見つかりません: {config_path}")
        logger.error(f"config.jsonが見つかりません: {config_path}")
        return

    # config.jsonを読み込み
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    project_settings = config.get("project_settings", {})

    processed_count = 0
    added_count = 0

    # 各アカウントのプロジェクト設定を処理
    for account, projects in project_settings.items():
        for project_name, settings in projects.items():
            git_repo_path = settings.get("git_repo_path")

            if git_repo_path and os.path.exists(git_repo_path):
                print(f"処理中: {project_name} ({git_repo_path})")
                logger.info(f"\n処理中: {project_name} ({git_repo_path})")
                processed_count += 1

                if add_nul_to_gitignore(git_repo_path):
                    print(f"  → .gitignoreにnulを追加")
                    added_count += 1
                else:
                    print(f"  → 既に追加済み")
            elif git_repo_path:
                print(f"パスが存在しません: {project_name} -> {git_repo_path}")
                logger.warning(f"パスが存在しません: {project_name} -> {git_repo_path}")

    print(f"\n完了: {processed_count}個のプロジェクトを処理し、{added_count}個に追加しました")
    logger.info(f"\n完了: {processed_count}個のプロジェクトを処理し、{added_count}個に追加しました")


if __name__ == "__main__":
    print("=== .gitignoreにnulを追加開始 ===")
    logger.info("=== .gitignoreにnulを追加開始 ===")
    process_all_projects()
    logger.info("=== .gitignoreにnulを追加完了 ===")
    print("=== .gitignoreにnulを追加完了 ===")
