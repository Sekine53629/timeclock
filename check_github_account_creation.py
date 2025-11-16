#!/usr/bin/env python3
"""
GitHubアカウントの作成日を調べるスクリプト
GitHub APIを使用してアカウント情報を取得
"""
import subprocess
import json
from datetime import datetime


def get_github_user_info(username: str) -> dict:
    """
    GitHub APIを使ってユーザー情報を取得

    Args:
        username: GitHubユーザー名

    Returns:
        ユーザー情報の辞書
    """
    cmd = ['gh', 'api', f'users/{username}']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"❌ エラー: {result.stderr}")
            return {}
    except Exception as e:
        print(f"❌ 例外が発生しました: {e}")
        return {}


def format_datetime(iso_datetime: str) -> str:
    """
    ISO 8601形式の日時を読みやすい形式に変換

    Args:
        iso_datetime: ISO 8601形式の日時文字列

    Returns:
        読みやすい形式の日時文字列
    """
    dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
    local_dt = dt.astimezone()

    return local_dt.strftime('%Y年%m月%d日 %H:%M:%S (%Z)')


def calculate_account_age(created_at: str) -> str:
    """
    アカウント作成日から経過年月日を計算

    Args:
        created_at: ISO 8601形式の作成日時

    Returns:
        経過年月日の文字列
    """
    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    now = datetime.now(created.tzinfo)

    delta = now - created
    years = delta.days // 365
    months = (delta.days % 365) // 30
    days = (delta.days % 365) % 30

    parts = []
    if years > 0:
        parts.append(f"{years}年")
    if months > 0:
        parts.append(f"{months}ヶ月")
    if days > 0 or not parts:
        parts.append(f"{days}日")

    return ''.join(parts)


def main():
    print("=" * 80)
    print("🔍 GitHubアカウント作成日を調査")
    print("=" * 80)
    print()

    # ユーザー名を入力
    username = input("GitHubユーザー名を入力してください（Enter: Sekine53629）: ").strip()
    if not username:
        username = "Sekine53629"

    print(f"✓ 対象ユーザー: {username}")
    print()

    # ユーザー情報を取得
    print("📡 GitHub APIに問い合わせ中...")
    user_info = get_github_user_info(username)

    if not user_info:
        print("❌ ユーザー情報が取得できませんでした。")
        return

    print("✓ 取得成功")
    print()

    # 結果を表示
    print("=" * 80)
    print("📊 アカウント情報")
    print("=" * 80)
    print()

    # 基本情報
    print(f"🔹 ユーザー名: {user_info.get('login', 'N/A')}")
    print(f"🔹 表示名: {user_info.get('name', 'N/A')}")
    print(f"🔹 プロフィールURL: {user_info.get('html_url', 'N/A')}")
    print()

    # アカウント作成日
    created_at = user_info.get('created_at')
    if created_at:
        formatted_date = format_datetime(created_at)
        account_age = calculate_account_age(created_at)

        print(f"📅 アカウント作成日: {formatted_date}")
        print(f"⏱️  経過期間: {account_age}")
    else:
        print("⚠️  作成日情報が取得できませんでした。")

    print()

    # アカウント更新日
    updated_at = user_info.get('updated_at')
    if updated_at:
        formatted_date = format_datetime(updated_at)
        print(f"🔄 最終更新日: {formatted_date}")
        print()

    # 統計情報
    print("=" * 80)
    print("📈 統計情報")
    print("=" * 80)
    print(f"🔹 公開リポジトリ数: {user_info.get('public_repos', 0)}")
    print(f"🔹 公開Gist数: {user_info.get('public_gists', 0)}")
    print(f"🔹 フォロワー数: {user_info.get('followers', 0)}")
    print(f"🔹 フォロー中: {user_info.get('following', 0)}")
    print()

    # バイオ
    bio = user_info.get('bio')
    if bio:
        print("=" * 80)
        print("📝 自己紹介")
        print("=" * 80)
        print(bio)
        print()

    # 所属
    company = user_info.get('company')
    if company:
        print(f"🏢 所属: {company}")
        print()

    # 場所
    location = user_info.get('location')
    if location:
        print(f"📍 場所: {location}")
        print()

    # メールアドレス
    email = user_info.get('email')
    if email:
        print(f"📧 メールアドレス: {email}")
        print()

    # ブログ/ウェブサイト
    blog = user_info.get('blog')
    if blog:
        print(f"🌐 ウェブサイト: {blog}")
        print()

    # Twitter
    twitter = user_info.get('twitter_username')
    if twitter:
        print(f"🐦 Twitter: @{twitter}")
        print()

    print("=" * 80)


if __name__ == '__main__':
    main()
