# Git作業時間推定ツール - 使い方

複数のGitHubアカウントからコミット履歴を収集し、作業時間を推定して残業代請求用の証拠データを生成するツールです。

## 📁 ファイル構成

```
scripts/
├── github_commit_analyzer.py    # GitHubからコミット履歴を収集
├── git_work_time_estimator.py   # ローカルGitリポジトリから作業時間を推定
└── README_GIT_ANALYZER.md       # このファイル

../timeclock/
├── git_import.py                # GUIへのインポートツール
└── git_import_dialog.py         # GUIダイアログ
```

## 🚀 使い方

### ステップ1: GitHub APIトークンの取得

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Generate new token
3. スコープで `repo` を選択
4. トークンを生成してコピー
5. **2つのアカウント両方でこの手順を実行**

### ステップ2: 設定ファイルの作成

#### 2-1. GitHub用設定（`github_config.json`）

```json
{
  "tokens": [
    "ghp_あなたのトークン1",
    "ghp_あなたのトークン2"
  ],
  "usernames": [
    "GitHubユーザー名1",
    "GitHubユーザー名2"
  ]
}
```

**セキュリティ注意:**
- このファイルは `.gitignore` に追加済みです
- 絶対に公開リポジトリにプッシュしないこと

#### 2-2. ローカルGit用設定（`git_repos_config.json`）

```json
{
  "repo_paths": [
    "C:/Users/あなた/Documents/GitHub/project1",
    "C:/Users/あなた/Documents/GitHub/project2",
    "C:/Users/あなた/Documents/GitHub/project3"
  ],
  "author_names": [
    "あなたのGit設定名1",
    "あなたのGit設定名2"
  ],
  "hourly_rate": 2000,
  "overtime_rate": 1.25,
  "weekend_rate": 1.35,
  "late_night_rate": 1.5
}
```

**Git設定名の確認方法:**
```bash
git config user.name
```

### ステップ3: 必要なパッケージのインストール

```bash
pip install requests pandas openpyxl matplotlib
```

### ステップ4: データ収集と分析

#### 方法A: GitHubから収集（推奨）

```bash
cd scripts
python github_commit_analyzer.py
```

**生成されるファイル:**
- `github_commits_evidence.csv` - Excel/GUIインポート用
- `github_commits_evidence.json` - 詳細データ
- `github_commits_summary.json` - サマリーレポート

#### 方法B: ローカルGitリポジトリから収集

```bash
cd scripts
python git_work_time_estimator.py
```

**生成されるファイル:**
- `git_work_time_evidence.csv` - Excel/GUIインポート用
- `git_work_time_data.json` - 詳細データ
- `work_time_summary.txt` - サマリーレポート

### ステップ5: GUIシステムへのインポート

#### 5-1. コマンドラインからインポート

```bash
cd ../timeclock

# プレビュー
python git_import.py ../timeclock_web/scripts/git_work_time_evidence.csv 0053629 --preview

# 実際にインポート（セッション分割間隔120分）
python git_import.py ../timeclock_web/scripts/git_work_time_evidence.csv 0053629

# セッション分割間隔を変更（90分）
python git_import.py ../timeclock_web/scripts/git_work_time_evidence.csv 0053629 --gap 90

# 既存データを上書き
python git_import.py ../timeclock_web/scripts/git_work_time_evidence.csv 0053629 --force
```

#### 5-2. GUIから直接インポート（将来実装予定）

1. タイムクロックGUIを起動: `python gui.py`
2. メニューから「Git履歴インポート」を選択
3. CSVファイルを選択
4. プレビューで内容確認
5. インポート実行

## 📊 作業時間推定のロジック

### コード変更量から推定

- **追加行数**: 10行 = 約5分
- **削除行数**: 10行 = 約2分（削除は追加より速い）
- **ファイル変更数**: 1ファイル = 最低10分（切り替えコスト）
- **複数ファイル**: 追加ファイルごとに+5分

### 時間外判定

- **時間外**: 18時以降または9時以前
- **深夜**: 22時以降または5時以前
- **休日**: 土曜日・日曜日

### セッションのグループ化

- 同じ日に**2時間以内**の間隔で行われたコミットは同じ作業セッションとみなす
- `--gap` オプションでこの間隔を調整可能

## 📈 出力データの見方

### CSVファイル（Excel/GUIインポート用）

| 列名 | 説明 |
|-----|-----|
| 日付 | コミット日 |
| 時刻 | コミット時刻 |
| 曜日 | 月火水木金土日 |
| プロジェクト名 | リポジトリ名 |
| コミットID | コミットハッシュ（短縮） |
| 作業内容 | コミットメッセージ |
| 変更ファイル数 | 変更されたファイル数 |
| 追加行数 | 追加された行数 |
| 削除行数 | 削除された行数 |
| 推定作業時間（分） | 推定された作業時間 |
| 推定作業時間（時間） | 同上（時間単位） |
| 時間外 | ○ = 時間外 |
| 休日 | ○ = 休日 |
| 深夜 | ○ = 深夜（22-5時） |
| 作業者名 | Git設定の名前 |

### サマリーレポート例

```
【総作業時間】
  総コミット数: 1,234 件
  推定総作業時間: 456.7 時間 (57.1 日分)

【時間外労働】
  時間外コミット数: 567 件
  推定時間外労働: 234.5 時間
  全体に占める割合: 51.4%

【休日労働】
  休日コミット数: 123 件
  推定休日労働: 56.7 時間

【深夜労働（22時〜5時）】
  深夜コミット数: 89 件
  推定深夜労働: 34.2 時間
```

## 💰 残業代の計算方法

### 基本的な計算式

```
未払い残業代 = (時間外時間 × 時給 × 1.25)
              + (休日時間 × 時給 × 1.35)
              + (深夜時間 × 時給 × 1.5)
```

### 例: 基本時給2,000円の場合

```python
# git_repos_config.json に設定
{
  "hourly_rate": 2000,      # 基本時給
  "overtime_rate": 1.25,    # 時間外割増（25%増）
  "weekend_rate": 1.35,     # 休日割増（35%増）
  "late_night_rate": 1.5    # 深夜割増（50%増）
}
```

**計算例:**
- 時間外234.5時間 × 2,000円 × 1.25 = **586,250円**
- 休日56.7時間 × 2,000円 × 1.35 = **153,090円**
- 深夜34.2時間 × 2,000円 × 1.5 = **102,600円**
- **合計: 841,940円**

## 🔒 セキュリティとプライバシー

### データの保存場所

- **個人デバイス**: 会社の監視システムから独立
- **ローカルストレージ**: クラウド同期しない
- **暗号化**: 機密情報は環境変数で管理

### GitHubトークンの管理

```bash
# 環境変数で管理（推奨）
export GITHUB_TOKEN_1="ghp_..."
export GITHUB_TOKEN_2="ghp_..."
export GITHUB_USERNAME_1="username1"
export GITHUB_USERNAME_2="username2"

# または .env ファイル（.gitignore に追加済み）
echo "GITHUB_TOKEN_1=ghp_..." >> .env
echo "GITHUB_TOKEN_2=ghp_..." >> .env
```

### 会社への対策

1. **個人デバイスで実行**
2. **VPN経由でアクセス**（会社ネットワークを避ける）
3. **トークンは定期的に再生成**
4. **生成されたCSVはクラウドバックアップ**（Google Drive等）

## 📝 法的証拠としての利用

### 証拠能力を高めるポイント

1. **タイムスタンプの保全**
   - コミットハッシュは改ざん不可能
   - GitHubのサーバータイムスタンプが証明

2. **業務関連性の証明**
   - コミットメッセージ
   - プロジェクト名
   - 変更されたファイル名

3. **複数データソースでの裏付け**
   - Zoom記録
   - メール送信履歴
   - 社内システムのログイン記録

### 提出時の注意点

- **PDFでも保存**: 改ざん防止
- **複数のバックアップ**: 3か所以上
- **証拠説明書を添付**: 推定ロジックの説明

## 🛠️ トラブルシューティング

### GitHub API Rate Limit

**エラー:** `API rate limit exceeded`

**解決策:**
```python
# github_commit_analyzer.py を編集
time.sleep(1)  # 各リクエスト間に1秒待機
```

### CSV文字化け

**問題:** Excelで開くと文字化け

**解決策:**
1. メモ帳で開く
2. 「名前を付けて保存」→ エンコーディング: UTF-8 with BOM
3. Excelで再度開く

### Git設定名が不一致

**エラー:** `No commits found`

**確認方法:**
```bash
cd /path/to/your/repo
git log --format="%an" | sort | uniq
```

出力された名前を `git_repos_config.json` の `author_names` に追加

### インポート時のエラー

**エラー:** `KeyError: '曜日'`

**原因:** CSVのヘッダーが期待と異なる

**解決策:**
1. CSVを最新のスクリプトで再生成
2. エンコーディングがShift-JISであることを確認

## 📞 サポート

### ログファイルの確認

```bash
# タイムクロックGUIのログ
cat ~/.timeclock/timeclock.log

# 直近のエラー
tail -n 50 ~/.timeclock/timeclock.log | grep ERROR
```

### デバッグモード

```python
# スクリプトの先頭に追加
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ⚖️ 免責事項

このツールは証拠収集のためのものであり、法的助言を提供するものではありません。
実際の訴訟や労働審判には、必ず労働問題に強い弁護士にご相談ください。

## 📚 参考資料

- 労働基準法第37条（時間外、休日及び深夜の割増賃金）
- 労働基準法第109条（記録の保存）
- [法テラス](https://www.houterasu.or.jp/)
- [日本労働弁護団](http://roudou-bengodan.org/)

---

**作成日:** 2025-11-11
**バージョン:** 1.0.0
**最終更新:** 2025-11-11
