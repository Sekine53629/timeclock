#!/usr/bin/env python3
"""
締め日設定のテストスクリプト
"""
from timeclock import TimeClock
from storage import Storage

def test_closing_day():
    """締め日設定の動作確認"""
    tc = TimeClock()

    # テストアカウント名
    test_account = "テストユーザー"

    print("=" * 60)
    print("締め日設定テスト")
    print("=" * 60)

    # 1. 月末締めで設定
    print("\n【ステップ1】月末締めに設定")
    tc.set_account_config(test_account, closing_day=31, standard_hours_per_day=8)

    config = tc.get_account_config(test_account)
    print(f"設定後の値: 締め日={config['closing_day']}, 標準時間={config['standard_hours_per_day']}")

    # 月次レポート取得
    try:
        summary = tc.get_monthly_summary(test_account, 2025, 10)
        print(f"集計期間: {summary['start_date']} ～ {summary['end_date']}")
        print(f"締め日設定: {summary['closing_day']} ({'月末締め' if summary['closing_day'] == 31 else '15日締め'})")
    except Exception as e:
        print(f"レポート取得エラー: {e}")

    # 2. 15日締めに変更
    print("\n【ステップ2】15日締めに変更")
    tc.set_account_config(test_account, closing_day=15, standard_hours_per_day=8)

    config = tc.get_account_config(test_account)
    print(f"設定後の値: 締め日={config['closing_day']}, 標準時間={config['standard_hours_per_day']}")

    # 月次レポート取得
    try:
        summary = tc.get_monthly_summary(test_account, 2025, 10)
        print(f"集計期間: {summary['start_date']} ～ {summary['end_date']}")
        print(f"締め日設定: {summary['closing_day']} ({'月末締め' if summary['closing_day'] == 31 else '15日締め'})")
    except Exception as e:
        print(f"レポート取得エラー: {e}")

    # 3. JSONファイルを直接確認
    print("\n【ステップ3】JSONファイルの内容確認")
    storage = Storage()
    config_data = storage.load_config()

    if test_account in config_data.get('accounts', {}):
        account_config = config_data['accounts'][test_account]
        print(f"JSONファイル内の設定:")
        print(f"  closing_day: {account_config.get('closing_day')}")
        print(f"  standard_hours_per_day: {account_config.get('standard_hours_per_day')}")
    else:
        print(f"{test_account} の設定がJSONファイルに見つかりません")

    # 4. user_infoでの取得確認
    print("\n【ステップ4】get_user_info での取得確認")
    user_info = storage.get_user_info(test_account)
    print(f"user_info:")
    print(f"  closing_day: {user_info['closing_day']}")
    print(f"  standard_hours_per_day: {user_info['standard_hours_per_day']}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

if __name__ == '__main__':
    test_closing_day()
