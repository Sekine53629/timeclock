"""
データ固定化（スナップショット作成）モジュール
2025年11月16日時点のデータを固定化し、以降の改ざんを防止
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataFreeze:
    """打刻データの固定化（スナップショット作成）"""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.freeze_date = datetime.now().strftime("%Y-%m-%d")
        self.freeze_timestamp = datetime.now().isoformat()

    def create_freeze_snapshot(self):
        """
        現時点のデータを固定化

        実行内容：
        1. 全データのスナップショットを作成
        2. スナップショット全体のハッシュを計算
        3. 固定化情報をconfig.jsonに記録
        4. 全既存レコードにlegacyフラグを付与

        Returns:
            dict: 固定化結果の情報
        """
        logger.info("=" * 60)
        logger.info("データ固定化を開始します")
        logger.info(f"固定日時: {self.freeze_timestamp}")
        logger.info("=" * 60)

        # 現在のデータを読み込み
        data_file = self.data_dir / 'timeclock_data.json'
        edit_log_file = self.data_dir / 'edit_log.json'
        config_file = self.data_dir / 'config.json'

        if not data_file.exists():
            raise FileNotFoundError(f"データファイルが見つかりません: {data_file}")

        with open(data_file, 'r', encoding='utf-8') as f:
            timeclock_data = json.load(f)

        # edit_log.jsonの読み込み（存在しない場合は空リスト）
        if edit_log_file.exists():
            with open(edit_log_file, 'r', encoding='utf-8') as f:
                edit_log = json.load(f)
        else:
            edit_log = []

        # スナップショットを作成
        total_records = self._count_records(timeclock_data)
        logger.info(f"総レコード数: {total_records}")

        snapshot = {
            "freeze_date": self.freeze_date,
            "freeze_timestamp": self.freeze_timestamp,
            "timeclock_data": timeclock_data,
            "edit_log": edit_log,
            "total_records": total_records,
            "metadata": {
                "reason": "新信頼性システム導入のため",
                "performed_by": "system",
                "system_version": "2.0"
            }
        }

        # スナップショット全体のハッシュを計算
        snapshot_json = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
        snapshot_hash = hashlib.sha256(snapshot_json.encode('utf-8')).hexdigest()
        snapshot["snapshot_hash"] = snapshot_hash

        logger.info(f"スナップショットハッシュ: {snapshot_hash}")

        # スナップショットを保存
        snapshot_file = self.data_dir / f'snapshot_{self.freeze_date}.json'
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        logger.info(f"スナップショット保存完了: {snapshot_file}")

        # config.jsonに固定化情報を記録
        self._update_config(snapshot_hash, config_file)

        # 全レコードに legacy フラグを付与
        self._mark_all_as_legacy(timeclock_data, data_file)

        logger.info("=" * 60)
        logger.info("データ固定化が完了しました")
        logger.info("=" * 60)

        return {
            "success": True,
            "freeze_date": self.freeze_date,
            "freeze_timestamp": self.freeze_timestamp,
            "snapshot_hash": snapshot_hash,
            "total_records": total_records,
            "snapshot_file": str(snapshot_file)
        }

    def _count_records(self, data):
        """全アカウントのレコード数を集計"""
        total = 0
        for account_data in data.get('accounts', {}).values():
            total += len(account_data.get('records', []))
        return total

    def _update_config(self, snapshot_hash, config_file):
        """config.jsonに固定化情報を記録"""
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        config['data_freeze'] = {
            "enabled": True,
            "freeze_date": self.freeze_date,
            "freeze_timestamp": self.freeze_timestamp,
            "snapshot_hash": snapshot_hash,
            "legacy_editable": False,  # 固定化後は過去データ編集不可
            "hash_chain_start_date": self.freeze_date,
            "warning": "このデータは固定化されています。過去データの編集はできません。"
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info("config.jsonに固定化情報を記録しました")

    def _mark_all_as_legacy(self, data, data_file):
        """全既存レコードにlegacyフラグを付与"""
        marked_count = 0

        for account, account_data in data.get('accounts', {}).items():
            for record in account_data.get('records', []):
                record['data_status'] = 'legacy'
                record['frozen_at'] = self.freeze_date
                marked_count += 1

        # 保存
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"{marked_count}件のレコードにlegacyフラグを付与しました")


class SnapshotVerifier:
    """スナップショットの完全性を検証"""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    def verify_snapshot(self, snapshot_file):
        """
        スナップショットが改ざんされていないか検証

        Args:
            snapshot_file: スナップショットファイルのパス

        Returns:
            dict: 検証結果
        """
        if not Path(snapshot_file).exists():
            return {
                "is_valid": False,
                "message": "スナップショットファイルが見つかりません",
                "details": {}
            }

        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)

            # 記録されているハッシュを取得
            recorded_hash = snapshot.pop('snapshot_hash')

            # 再計算
            snapshot_json = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
            calculated_hash = hashlib.sha256(snapshot_json.encode('utf-8')).hexdigest()

            # 比較
            is_valid = (recorded_hash == calculated_hash)

            return {
                "is_valid": is_valid,
                "message": "✅ スナップショットは改ざんされていません" if is_valid else "⚠️ スナップショットが改ざんされています！",
                "details": {
                    "recorded_hash": recorded_hash,
                    "calculated_hash": calculated_hash,
                    "freeze_date": snapshot.get('freeze_date'),
                    "total_records": snapshot.get('total_records')
                }
            }
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"検証中にエラーが発生しました: {str(e)}",
                "details": {}
            }


if __name__ == "__main__":
    # コマンドラインから実行された場合
    import sys

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # データディレクトリ
    data_dir = Path.home() / '.timeclock'

    print("\n" + "=" * 60)
    print("打刻データ固定化スクリプト")
    print("=" * 60)
    print(f"データディレクトリ: {data_dir}")
    print()

    # 確認
    response = input("本当にデータを固定化しますか？ (yes/no): ")
    if response.lower() != 'yes':
        print("中止しました。")
        sys.exit(0)

    # 最終確認
    print("\n⚠️ 警告: この操作は取り消せません！")
    response = input("実行するには「FREEZE」と入力してください: ")
    if response != "FREEZE":
        print("入力が一致しません。中止しました。")
        sys.exit(0)

    # 実行
    try:
        freezer = DataFreeze(data_dir)
        result = freezer.create_freeze_snapshot()

        print("\n" + "=" * 60)
        print("✅ データ固定化が完了しました")
        print("=" * 60)
        print(f"固定日時: {result['freeze_timestamp']}")
        print(f"総レコード数: {result['total_records']}")
        print(f"スナップショットハッシュ: {result['snapshot_hash']}")
        print(f"スナップショットファイル: {result['snapshot_file']}")
        print()
        print("⚠️ スナップショットファイルを安全な場所に保管してください！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        sys.exit(1)
