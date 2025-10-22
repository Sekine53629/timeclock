#!/usr/bin/env python3
"""
スモークテスト - 基本機能の動作確認
"""

from timeclock import TimeClock
from storage import Storage
from logger import get_logger
from pathlib import Path
import sys

logger = get_logger(__name__)


def test_basic_functionality():
    """基本機能のテスト"""
    print("=" * 60)
    print("基本機能スモークテスト")
    print("=" * 60)

    tc = TimeClock()
    test_account = "test_user_smoke"
    test_project = "test_project"

    tests_passed = 0
    tests_total = 0

    # 前のセッションをクリーンアップ
    try:
        tc.end_work(test_account)
    except:
        pass  # セッションがない場合は無視

    # Test 1: 作業開始
    tests_total += 1
    try:
        session = tc.start_work(test_account, test_project)
        assert session is not None
        assert session['account'] == test_account
        assert session['project'] == test_project
        print(f"[OK] Test 1: 作業開始 - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 1: 作業開始 - FAIL: {e}")

    # Test 2: 休憩開始
    tests_total += 1
    try:
        session = tc.start_break(test_account)
        assert session['status'] == 'on_break'
        print(f"[OK] Test 2: 休憩開始 - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 2: 休憩開始 - FAIL: {e}")

    # Test 3: 作業再開
    tests_total += 1
    try:
        session = tc.end_break(test_account)
        assert session['status'] == 'working'
        print(f"[OK] Test 3: 作業再開 - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 3: 作業再開 - FAIL: {e}")

    # Test 4: 作業終了
    tests_total += 1
    try:
        session = tc.end_work(test_account)
        assert session['end_time'] is not None
        print(f"[OK] Test 4: 作業終了 - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 4: 作業終了 - FAIL: {e}")

    # Test 5: 日別サマリー
    tests_total += 1
    try:
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        summary = tc.get_daily_summary(test_account, today)
        assert summary is not None
        assert summary['account'] == test_account
        print(f"[OK] Test 5: 日別サマリー - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 5: 日別サマリー - FAIL: {e}")

    # Test 6: アカウントリスト
    tests_total += 1
    try:
        accounts = tc.list_accounts()
        assert test_account in accounts
        print(f"[OK] Test 6: アカウントリスト - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 6: アカウントリスト - FAIL: {e}")

    # Test 7: 設定の保存と読み込み
    tests_total += 1
    try:
        tc.set_account_config(test_account, 15, 8)
        config = tc.get_account_config(test_account)
        assert config['closing_day'] == 15
        assert config['standard_hours_per_day'] == 8
        print(f"[OK] Test 7: 設定の保存と読み込み - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 7: 設定の保存と読み込み - FAIL: {e}")

    # Test 8: ログファイルの存在確認
    tests_total += 1
    try:
        log_file = Path.home() / '.timeclock' / 'timeclock.log'
        assert log_file.exists()
        print(f"[OK] Test 8: ログファイル - PASS")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Test 8: ログファイル - FAIL: {e}")

    print("\n" + "=" * 60)
    print(f"結果: {tests_passed}/{tests_total} テスト成功")
    print("=" * 60)

    if tests_passed == tests_total:
        print("[OK] 全てのテストが成功しました!")
        print(f"\nログファイル: {Path.home() / '.timeclock' / 'timeclock.log'}")
        return 0
    else:
        print(f"[FAIL] {tests_total - tests_passed} 件のテストが失敗しました")
        return 1


if __name__ == '__main__':
    try:
        exit_code = test_basic_functionality()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"スモークテストでエラー: {e}", exc_info=True)
        print(f"\n[FAIL] テスト実行中にエラー: {e}")
        sys.exit(1)
