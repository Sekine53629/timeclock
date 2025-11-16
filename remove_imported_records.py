#!/usr/bin/env python3
"""
インポート済みレコードを削除
"""
import json
from datetime import datetime

def main():
    db_path = 'json/timeclock_data.json'

    # データベースを読み込み
    with open(db_path, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    account = '0053629'
    if account not in db_data['accounts']:
        print("アカウントが見つかりません")
        return

    records = db_data['accounts'][account]['records']
    original_count = len(records)

    # インポート済みレコードを削除
    filtered_records = [r for r in records if r.get('submission_status') != 'imported']

    removed_count = original_count - len(filtered_records)

    print(f"元のレコード数: {original_count}")
    print(f"削除するレコード数: {removed_count}")
    print(f"残りのレコード数: {len(filtered_records)}")

    if removed_count > 0:
        # バックアップ
        backup_path = db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
        print(f"\nバックアップ作成: {backup_path}")

        # 更新
        db_data['accounts'][account]['records'] = filtered_records

        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)

        print(f"✓ {removed_count}件のインポート済みレコードを削除しました")
    else:
        print("削除対象のレコードがありません")

if __name__ == '__main__':
    main()
