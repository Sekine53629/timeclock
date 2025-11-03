#!/usr/bin/env python3
"""
編集・申請機能のテスト
"""
import tempfile
from pathlib import Path
from timeclock import TimeClock
from storage import Storage
import shutil

def test_edit_features():
    """編集・申請機能のテスト"""
    # テスト用の一時ディレクトリを作成
    test_dir = Path(tempfile.mkdtemp())

    try:
        print(f"テストディレクトリ: {test_dir}")

        # TimeClockインスタンスを作成
        storage = Storage(data_dir=str(test_dir))
        tc = TimeClock(storage=storage)

        # 1. 作業開始（コメント付き）
        print("\n1. 作業開始（コメント付き）")
        session = tc.start_work("test_user", "test_project", "テスト作業")
        print(f"   セッション作成: {session['account']} - {session['project']}")
        print(f"   コメント: {session.get('comment', '')}")

        # 1-2. 休憩開始
        print("\n1-2. 休憩開始")
        break_session = tc.start_break("test_user")
        print(f"   休憩開始: {break_session['status']}")

        # 1-3. 休憩終了
        print("\n1-3. 休憩終了")
        resume_session = tc.end_break("test_user")
        print(f"   作業再開: {resume_session['status']}")
        print(f"   休憩回数: {len(resume_session['breaks'])}")

        # 2. 作業終了
        print("\n2. 作業終了")
        completed = tc.end_work("test_user")
        print(f"   完了: {completed['total_minutes']}分")

        # 休憩時間を計算して表示
        break_minutes = 0
        for brk in completed.get('breaks', []):
            if brk.get('end'):
                from datetime import datetime
                break_start = datetime.fromisoformat(brk['start'])
                break_end = datetime.fromisoformat(brk['end'])
                break_minutes += int((break_end - break_start).total_seconds() / 60)
        print(f"   休憩時間: {break_minutes}分")

        # 3. レコード取得
        print("\n3. レコード取得")
        records = storage.get_records("test_user")
        print(f"   レコード数: {len(records)}")
        if records:
            print(f"   最初のレコード: {records[0]['date']} - {records[0]['project']}")
            print(f"   コメント: {records[0].get('comment', 'なし')}")

        # 4. レコード編集（コメント）
        print("\n4. レコード編集（コメント）")
        if records:
            updated = records[0].copy()
            updated['comment'] = "編集後のコメント"
            success = tc.update_record("test_user", 0, updated, "テスト編集")
            print(f"   編集結果: {'成功' if success else '失敗'}")

            # 編集後のレコード確認
            updated_records = storage.get_records("test_user")
            print(f"   編集後コメント: {updated_records[0].get('comment', 'なし')}")
            print(f"   申請状態: {updated_records[0].get('submission_status', 'なし')}")

        # 4-2. 休憩時間の編集
        print("\n4-2. 休憩時間の編集")
        if records:
            updated = updated_records[0].copy()
            # 30分の休憩時間を設定
            updated['total_break_minutes'] = 30
            # 総時間から休憩時間を引いた値を作業時間とする
            from datetime import datetime
            start_dt = datetime.fromisoformat(updated['start_time'])
            end_dt = datetime.fromisoformat(updated['end_time'])
            total_minutes = int((end_dt - start_dt).total_seconds() / 60)
            updated['total_minutes'] = total_minutes - 30

            success = tc.update_record("test_user", 0, updated, "休憩時間を30分に変更")
            print(f"   編集結果: {'成功' if success else '失敗'}")

            # 編集後のレコード確認
            final_records = storage.get_records("test_user")
            print(f"   総時間: {total_minutes}分")
            print(f"   休憩時間: {final_records[0].get('total_break_minutes', 0)}分")
            print(f"   作業時間: {final_records[0].get('total_minutes', 0)}分")

        # 5. 編集ログ確認
        print("\n5. 編集ログ確認")
        logs = tc.get_edit_logs(account="test_user")
        print(f"   ログ件数: {len(logs)}")
        if logs:
            for log in logs:
                print(f"   - {log['action']}: {log.get('reason', '')}")

        # 6. レコード申請
        print("\n6. レコード申請")
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        count = tc.submit_records("test_user", today, today, "月次申請テスト")
        print(f"   申請件数: {count}")

        # 申請後のレコード確認
        submitted_records = storage.get_records("test_user")
        if submitted_records:
            print(f"   申請状態: {submitted_records[0].get('submission_status', 'なし')}")

        # 7. レコード削除
        print("\n7. レコード削除")
        success = tc.delete_record("test_user", 0, "テスト削除")
        print(f"   削除結果: {'成功' if success else '失敗'}")

        remaining = storage.get_records("test_user")
        print(f"   残りレコード数: {len(remaining)}")

        # 8. 編集ログの最終確認
        print("\n8. 編集ログの最終確認")
        final_logs = tc.get_edit_logs(account="test_user")
        print(f"   最終ログ件数: {len(final_logs)}")
        for log in final_logs:
            print(f"   - {log['timestamp'][:19]}: {log['action']} ({log.get('reason', '')})")

        print("\n✓ すべてのテストが完了しました")

    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # テストディレクトリを削除
        shutil.rmtree(test_dir)
        print(f"\nテストディレクトリを削除: {test_dir}")

if __name__ == "__main__":
    test_edit_features()
