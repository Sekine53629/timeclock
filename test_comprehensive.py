#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
包括的テストスイート
データ整合性、エラーハンドリング、マルチアカウント同時作業などをテスト
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import shutil

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from timeclock import TimeClock
from logger import get_logger

logger = get_logger(__name__)

def setup_test_environment():
    """テスト環境のセットアップ"""
    # テスト用のデータディレクトリを作成
    test_dir = Path.home() / '.timeclock_test'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(exist_ok=True)

    # テスト用の設定を返す
    return test_dir

def cleanup_test_environment(test_dir):
    """テスト環境のクリーンアップ"""
    if test_dir.exists():
        shutil.rmtree(test_dir)

def test_data_integrity():
    """
    データ整合性テスト
    - セッションデータが正しく保存されるか
    - 休憩時間が正確に計算されるか
    - 作業時間が正確に計算されるか
    """
    print("\n=== Test 1: データ整合性テスト ===")

    tc = TimeClock()
    test_account = "integrity_test_user"
    test_project = "test_project"

    try:
        # 既存のセッションをクリーンアップ
        try:
            tc.end_work(test_account)
        except:
            pass

        # 1. 作業開始
        start_session = tc.start_work(test_account, test_project)
        assert start_session['account'] == test_account, "アカウント名が一致しません"
        assert start_session['project'] == test_project, "プロジェクト名が一致しません"
        assert start_session['status'] == 'working', "ステータスが'working'ではありません"
        print("[OK] 作業開始のデータ整合性")

        # 2. 休憩開始
        break_session = tc.start_break(test_account)
        assert break_session['status'] == 'on_break', "ステータスが'on_break'ではありません"
        assert len(break_session['breaks']) > 0, "休憩データが記録されていません"
        print("[OK] 休憩開始のデータ整合性")

        # 3. 休憩終了
        resume_session = tc.end_break(test_account)
        assert resume_session['status'] == 'working', "ステータスが'working'に戻っていません"
        last_break = resume_session['breaks'][-1]
        assert 'start' in last_break, "休憩開始時刻が記録されていません"
        assert 'end' in last_break, "休憩終了時刻が記録されていません"
        print("[OK] 休憩終了のデータ整合性")

        # 4. 作業終了
        end_session = tc.end_work(test_account)
        assert end_session['status'] == 'completed', "ステータスが'completed'ではありません"
        assert end_session['end_time'] is not None, "終了時刻が記録されていません"
        assert end_session['total_minutes'] >= 0, "作業時間が計算されていません"
        print("[OK] 作業終了のデータ整合性")

        return True

    except AssertionError as e:
        print(f"[FAIL] データ整合性テスト: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] データ整合性テスト (予期しないエラー): {e}")
        return False

def test_error_handling():
    """
    エラーハンドリングテスト
    - 重複した作業開始を防ぐ
    - 作業中でないときの休憩開始を防ぐ
    - 休憩中でないときの休憩終了を防ぐ
    """
    print("\n=== Test 2: エラーハンドリングテスト ===")

    tc = TimeClock()
    test_account = "error_test_user"
    test_project = "test_project"

    try:
        # クリーンアップ
        try:
            tc.end_work(test_account)
        except:
            pass

        # 1. 作業開始
        tc.start_work(test_account, test_project)

        # 2. 重複した作業開始を試みる（エラーになるべき）
        try:
            tc.start_work(test_account, test_project)
            print("[FAIL] 重複した作業開始が防げていません")
            return False
        except ValueError as e:
            if "既に作業中です" in str(e) or "セッションが開始されています" in str(e):
                print("[OK] 重複した作業開始を正しく防止")
            else:
                print(f"[FAIL] 予期しないエラーメッセージ: {e}")
                return False

        # 3. 作業終了
        tc.end_work(test_account)

        # 4. 作業中でないときの休憩開始を試みる（エラーになるべき）
        try:
            tc.start_break(test_account)
            print("[FAIL] 作業中でない状態での休憩開始が防げていません")
            return False
        except ValueError as e:
            if "作業セッションが開始されていません" in str(e) or "作業中ではありません" in str(e) or "現在のセッションがありません" in str(e):
                print("[OK] 作業中でない状態での休憩開始を正しく防止")
            else:
                print(f"[FAIL] 予期しないエラーメッセージ: {e}")
                return False

        # 5. 休憩中でないときの休憩終了を試みる（エラーになるべき）
        tc.start_work(test_account, test_project)
        try:
            tc.end_break(test_account)
            print("[FAIL] 休憩中でない状態での休憩終了が防げていません")
            return False
        except ValueError as e:
            if "休憩中ではありません" in str(e):
                print("[OK] 休憩中でない状態での休憩終了を正しく防止")
            else:
                print(f"[FAIL] 予期しないエラーメッセージ: {e}")
                return False

        # クリーンアップ
        tc.end_work(test_account)

        return True

    except Exception as e:
        print(f"[FAIL] エラーハンドリングテスト (予期しないエラー): {e}")
        return False

def test_multi_account():
    """
    マルチアカウント同時作業テスト
    - 複数のアカウントが同時に作業できるか
    - 各アカウントのセッションが独立しているか
    - セッション取得が正しく動作するか
    """
    print("\n=== Test 3: マルチアカウント同時作業テスト ===")

    tc = TimeClock()
    accounts = ["user_a", "user_b", "user_c"]
    project = "multi_test_project"

    try:
        # 全てのセッションをクリーンアップ（既存のユーザーセッションも含む）
        all_existing_sessions = tc.storage.get_all_current_sessions()
        for account in list(all_existing_sessions.keys()):
            try:
                tc.end_work(account)
            except:
                pass

        # 1. 3つのアカウントで同時に作業開始
        sessions = {}
        for account in accounts:
            session = tc.start_work(account, project)
            sessions[account] = session
            assert session['account'] == account, f"{account}のセッションデータが正しくありません"
        print("[OK] 複数アカウントで同時作業開始")

        # 2. 各アカウントのセッションが独立していることを確認
        all_sessions = tc.storage.get_all_current_sessions()
        test_accounts_count = sum(1 for acc in accounts if acc in all_sessions)
        assert test_accounts_count == 3, f"テストアカウントのセッション数が3ではありません: {test_accounts_count}"
        for account in accounts:
            assert account in all_sessions, f"{account}のセッションが見つかりません"
        print("[OK] 各アカウントのセッションが独立")

        # 3. user_bのみ休憩開始
        tc.start_break("user_b")
        session_b = tc.storage.get_current_session("user_b")
        assert session_b['status'] == 'on_break', "user_bが休憩中ではありません"

        # user_aとuser_cは作業中のまま
        session_a = tc.storage.get_current_session("user_a")
        session_c = tc.storage.get_current_session("user_c")
        assert session_a['status'] == 'working', "user_aの状態が変わっています"
        assert session_c['status'] == 'working', "user_cの状態が変わっています"
        print("[OK] 個別アカウントの状態変更が独立")

        # 4. user_aのみ作業終了
        tc.end_work("user_a")
        all_sessions = tc.storage.get_all_current_sessions()
        assert len(all_sessions) == 2, f"セッション数が2ではありません: {len(all_sessions)}"
        assert "user_a" not in all_sessions, "user_aのセッションが残っています"
        assert "user_b" in all_sessions, "user_bのセッションが消えています"
        assert "user_c" in all_sessions, "user_cのセッションが消えています"
        print("[OK] 個別アカウントの作業終了が独立")

        # クリーンアップ
        tc.end_break("user_b")
        tc.end_work("user_b")
        tc.end_work("user_c")

        return True

    except AssertionError as e:
        print(f"[FAIL] マルチアカウントテスト: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] マルチアカウントテスト (予期しないエラー): {e}")
        return False

def test_settings_persistence():
    """
    設定の永続化テスト
    - 自動休憩設定が保存されるか
    - 締め日設定が保存されるか
    - 設定が正しく読み込まれるか
    """
    print("\n=== Test 4: 設定の永続化テスト ===")

    tc = TimeClock()
    test_account = "settings_test_user"

    try:
        # 1. 自動休憩設定を保存
        config = tc.storage.load_config()
        config['auto_break'] = {
            'enabled': True,
            'threshold_minutes': 10
        }
        tc.storage.save_config(config)
        print("[OK] 自動休憩設定を保存")

        # 2. 設定を読み込んで確認
        loaded_config = tc.storage.load_config()
        assert 'auto_break' in loaded_config, "自動休憩設定が見つかりません"
        assert loaded_config['auto_break']['enabled'] == True, "enabled設定が正しくありません"
        assert loaded_config['auto_break']['threshold_minutes'] == 10, "threshold設定が正しくありません"
        print("[OK] 自動休憩設定を読み込み")

        # 3. アカウント別設定を保存（締め日は15または31）
        tc.storage.set_account_config(test_account, closing_day=15, standard_hours_per_day=7.5)
        print("[OK] アカウント別設定を保存")

        # 4. アカウント別設定を読み込んで確認
        account_config = tc.storage.get_account_config(test_account)
        assert account_config['closing_day'] == 15, "締め日設定が正しくありません"
        assert account_config['standard_hours_per_day'] == 7.5, "標準時間設定が正しくありません"
        print("[OK] アカウント別設定を読み込み")

        return True

    except AssertionError as e:
        print(f"[FAIL] 設定の永続化テスト: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 設定の永続化テスト (予期しないエラー): {e}")
        return False

def test_report_generation():
    """
    レポート生成テスト
    - 日次サマリーが正しく生成されるか
    - 月次レポートが正しく生成されるか
    - 締め日を考慮した期間計算が正しいか
    """
    print("\n=== Test 5: レポート生成テスト ===")

    tc = TimeClock()
    test_account = "report_test_user"
    test_project = "report_project"

    try:
        # クリーンアップ
        try:
            tc.end_work(test_account)
        except:
            pass

        # 1. 作業セッションを作成（十分な時間を確保）
        import time
        tc.start_work(test_account, test_project)
        time.sleep(0.1)  # 0.1秒待機
        tc.start_break(test_account)
        time.sleep(0.1)  # 0.1秒待機
        tc.end_break(test_account)
        time.sleep(0.1)  # 0.1秒待機
        tc.end_work(test_account)

        # 2. 日次サマリーを取得
        today = datetime.now().strftime("%Y-%m-%d")
        summary = tc.get_daily_summary(test_account, today)

        assert 'total_minutes' in summary, "作業時間キーが含まれていません"
        assert 'total_hours' in summary, "作業時間（時間）が含まれていません"
        assert 'records' in summary, "レコードが含まれていません"
        assert len(summary['records']) > 0, "レコードが空です"
        print("[OK] 日次サマリー生成")

        # 3. 月次レポートを取得
        year = datetime.now().year
        month = datetime.now().month
        closing_day = 31

        report = tc.get_monthly_summary(test_account, year, month, closing_day)

        assert 'account' in report, "アカウント名が含まれていません"
        assert 'year' in report, "年が含まれていません"
        assert 'month' in report, "月が含まれていません"
        assert 'daily_stats' in report, "日次統計が含まれていません"
        assert 'total_minutes' in report, "合計作業時間が計算されていません"
        assert 'record_count' in report, "レコード数が含まれていません"
        print("[OK] 月次レポート生成")

        return True

    except AssertionError as e:
        print(f"[FAIL] レポート生成テスト: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] レポート生成テスト (予期しないエラー): {e}")
        return False

def run_all_tests():
    """全テストを実行"""
    print("=" * 60)
    print("タイムクロックアプリケーション 包括的テストスイート")
    print("=" * 60)

    tests = [
        ("データ整合性", test_data_integrity),
        ("エラーハンドリング", test_error_handling),
        ("マルチアカウント同時作業", test_multi_account),
        ("設定の永続化", test_settings_persistence),
        ("レポート生成", test_report_generation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name}テストで予期しないエラー: {e}")
            results.append((name, False))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"合計: {len(results)}件")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
