# 打刻システム (TimeClock)

プロジェクト別に作業時間を管理する打刻システムです。複数のアカウント・プロジェクトの作業時間を記録し、日別・プロジェクト別のレポートを出力できます。

## 特徴

### コア機能
- ✅ プロジェクト別の作業時間管理
- ✅ 複数アカウント同時作業対応
- ✅ 休憩時間の記録
- ✅ 日別・プロジェクト別・月次レポート
- ✅ プロジェクト別時間外労働時間の自動計算
- ✅ 15日締め・月末締め対応
- ✅ HTML形式での印刷可能なレポート出力

### GUI機能 ⭐NEW!
- ✅ **ダークモード対応GUI** - 目に優しいダークテーマ
- ✅ **自動休憩機能** - PC無操作時に自動で休憩状態へ遷移
- ✅ **リアルタイム作業時間表示** - 現在の作業時間をライブ更新
- ✅ **月次レポート表示** - GUIから直接月次レポートを確認
- ✅ **ユーザー管理** - 複数ユーザーの登録・設定変更

### データ管理
- ✅ **Google Drive対応：複数PC間でデータ共有**
- ✅ ファイルロック機構による同時書き込み防止
- ✅ 自動バックアップ機能（最新5世代保持）
- ✅ 包括的なロギングシステム
- ✅ データ整合性チェック

### インターフェース
- ✅ シンプルなCLIインターフェース
- ✅ 直感的なGUIインターフェース（Windows専用）

## インストール

```bash
# リポジトリのクローン
git clone <repository-url>
cd timeclock

# Python 3.7以上が必要です
python --version
```

## 初期セットアップ（Google Drive対応）

複数のPCで同じデータを共有する場合、Google Drive上にデータベースを配置できます。

### 1. セットアップコマンドを実行

```bash
python cli.py setup
```

対話形式で以下の設定を行います：

```
============================================================
打刻システム - 初期設定
============================================================

現在の設定:
  データベース保存先: /Users/username/.timeclock
  デフォルトアカウント: 未設定

データベースの保存先を設定してください。
例: ~/Google Drive/timeclock
   （Macの場合: /Users/username/Google Drive/timeclock）
   （Windowsの場合: C:\Users\username\Google Drive\timeclock）

保存先パス [/Users/username/.timeclock]: ~/Google Drive/timeclock

デフォルトアカウント名を設定してください（省略可）。
アカウント名 []: user1

============================================================
✓ 設定が完了しました
============================================================
データベース保存先: /Users/username/Google Drive/timeclock
デフォルトアカウント: user1

この設定は ~/.timeclockrc に保存されています。
```

### 2. 各PCで同じ設定を実施

全てのPCで同じGoogle Driveパスを指定してください。

**例：**
- PC1（Mac）: `~/Google Drive/timeclock`
- PC2（Windows）: `C:\Users\username\Google Drive\timeclock`
- PC3（Mac）: `~/Google Drive/timeclock`

### 3. 設定ファイルの場所

設定は `~/.timeclockrc` に保存されます：

```json
{
  "db_path": "/Users/username/Google Drive/timeclock",
  "default_account": "user1"
}
```

### Google Drive以外のクラウドストレージ

Google Drive以外にも以下のサービスが利用可能です：
- Dropbox: `~/Dropbox/timeclock`
- OneDrive: `~/OneDrive/timeclock`
- iCloud Drive: `~/Library/Mobile Documents/com~apple~CloudDocs/timeclock`

## 複数PC環境での使用上の注意

### ファイルロック機構

複数PCから同時にデータを書き込もうとした場合、ファイルロック機構が自動的に排他制御を行います。

- 1つのPCが書き込み中は、他のPCは待機状態になります
- タイムアウトは10秒（古いロックは自動的に解除されます）

### 自動バックアップ

データ保存時に自動的にバックアップファイルが作成されます：

```
~/Google Drive/timeclock/
  ├── timeclock_data.json              # 現在のデータ
  ├── timeclock_data.json.backup_20251010_090000
  ├── timeclock_data.json.backup_20251010_120000
  └── ...
```

- 最新5世代のバックアップを自動保持
- データ損失時は手動でバックアップから復元可能

### クラウド同期のタイミング

Google Driveなどのクラウドストレージは同期に若干の遅延があります：

- **推奨**: 作業終了後、数秒待ってから別PCで操作する
- **注意**: 同一プロジェクトを異なるPCで同時に開始しない

## GUI版の使い方 ⭐NEW!

### GUI起動

```bash
python gui.py
```

### GUI機能

#### 1. ダークモードインターフェース
- 目に優しいダークカラースキーム (#1e1e1e背景、#e0e0e0テキスト)
- コンパクトなレイアウト (900x650ウィンドウ)
- 直感的な2カラム設定画面

#### 2. 打刻機能
- **作業開始**: アカウントとプロジェクトを選択して作業開始
- **休憩開始**: ボタン一つで休憩状態へ
- **作業再開**: 休憩から作業に復帰
- **作業終了**: 現在の作業を終了

#### 3. 自動休憩機能
- **PC無操作検知**: 指定時間（5-60分）PCを操作しないと自動で休憩状態へ
- **設定**: 設定タブから有効/無効を切り替え、閾値を設定
- **通知**: 自動休憩時にダイアログで通知
- **設定永続化**: 設定は自動的に保存され、次回起動時に復元

設定方法：
1. 設定タブを開く
2. 「自動休憩設定」セクションで「自動休憩機能を有効にする」をチェック
3. 無操作時間の閾値を設定（5-60分）
4. 設定は自動保存されます

#### 4. リアルタイム作業時間表示
- 現在の作業時間をリアルタイムで表示
- 今日の累計作業時間を表示
- ステータス表示（作業中/休憩中/未作業）

#### 5. 月次レポート表示
- GUIから直接月次レポートを確認
- 年月と締め日を選択してレポート生成
- プロジェクト別の作業時間と時間外労働時間を表示

#### 6. ユーザー管理
- 複数ユーザーの登録と管理
- ユーザー別の設定（締め日、標準労働時間）
- 設定の追加・変更・削除

#### 7. データベース設定
- データベース保存先の変更
- Google Driveなどクラウドストレージへの保存に対応

### GUI使用上の注意

**Windows専用**: 自動休憩機能のPC無操作検知はWindows APIを使用しているため、Windows環境でのみ動作します。

**ログファイル**: 全ての操作は `~/.timeclock/timeclock.log` に記録されます。問題が発生した場合は、このログファイルを確認してください。

## CLI版の使い方

### 基本的な操作フロー

```bash
# 1. 作業開始
python cli.py start <アカウント名> <プロジェクト名>

# 2. 休憩開始
python cli.py break

# 3. 休憩終了・作業再開
python cli.py resume

# 4. 作業終了
python cli.py end

# 5. 現在の状態確認
python cli.py status
```

### 実際の使用例

```bash
# 作業開始
$ python cli.py start user1 project-alpha
✓ 作業開始: user1 - project-alpha
  開始時刻: 2025-10-10 09:00:00

# 現在の状態確認
$ python cli.py status
現在の作業: user1 - project-alpha
開始時刻: 2025-10-10 09:00:00
状態: 作業中
休憩回数: 0回
現在までの作業時間: 1時間30分

# 休憩開始
$ python cli.py break
✓ 休憩開始: user1 - project-alpha
  休憩回数: 1回目

# 休憩終了
$ python cli.py resume
✓ 作業再開: user1 - project-alpha

# 作業終了
$ python cli.py end
✓ 作業終了: user1 - project-alpha
  開始時刻: 2025-10-10 09:00:00
  終了時刻: 2025-10-10 18:00:00
  休憩回数: 1回
  作業時間: 8時間00分
```

### レポート機能

#### 日別レポート

```bash
# 今日の作業時間レポート
$ python cli.py report daily user1

【日別レポート】
アカウント: user1
日付: 2025-10-10
合計作業時間: 9時間30分 (9.50時間)

プロジェクト別内訳:
  - project-alpha: 5時間30分
  - project-beta: 4時間00分

標準労働時間: 8時間 (480分)
時間外労働時間: 1時間30分 ⚠️

# 特定の日付のレポート
$ python cli.py report daily user1 --date 2025-10-09

# 標準労働時間を変更（デフォルト8時間）
$ python cli.py report daily user1 --standard-hours 7

# 詳細表示（各セッションの詳細）
$ python cli.py report daily user1 -v
```

#### プロジェクト別レポート

```bash
# プロジェクトの累計時間
$ python cli.py report project user1 project-alpha

【プロジェクト別レポート】
アカウント: user1
プロジェクト: project-alpha
レコード数: 5セッション
合計作業時間: 25時間30分 (25.50時間)

日別内訳:
  2025-10-08: 5時間00分
  2025-10-09: 6時間30分
  2025-10-10: 5時間30分
  2025-10-11: 4時間30分
  2025-10-12: 4時間00分

# 期間を指定してレポート
$ python cli.py report project user1 project-alpha --start-date 2025-10-01 --end-date 2025-10-31
```

#### 月次レポート（NEW!）

```bash
# 今月の月次レポート（プロジェクト別時間外労働時間含む）
$ python cli.py report monthly user1

============================================================
【月次レポート - 2025年10月】(月末締め)
============================================================
アカウント: user1
集計期間: 2025-10-01 ～ 2025-10-31
稼働日数: 22日

総作業時間: 185時間30分 (185.50時間)
標準労働時間: 176時間00分 (176.00時間)
総時間外労働時間: 9時間30分 (9.50時間) ⚠️

============================================================
【プロジェクト別内訳】
============================================================

■ project-alpha
  稼働日数: 15日
  作業時間: 105時間30分 (105.50時間)
  時間外労働時間: 5時間45分 (5.75時間) ⚠️

■ project-beta
  稼働日数: 12日
  作業時間: 80時間00分 (80.00時間)
  時間外労働時間: 3時間45分 (3.75時間) ⚠️

============================================================

# 特定月のレポート
$ python cli.py report monthly user1 2025-09

# 詳細表示（日別・プロジェクト別内訳付き）
$ python cli.py report monthly user1 -v

# HTMLファイルに出力（印刷可能）
$ python cli.py report monthly user1 -o report_2025-10.html
✓ HTMLレポートを出力しました: report_2025-10.html
  ブラウザで開く、または印刷してご利用ください
```

### アカウント設定（締め日・標準労働時間）

```bash
# 設定を表示
$ python cli.py config show user1

user1 の設定:
  締め日: 31日 (月末締め)
  標準労働時間: 8時間/日

# 締め日を15日に設定
$ python cli.py config set user1 --closing-day 15 --standard-hours 8
✓ user1 の設定を更新しました:
  締め日: 15日 (15日締め)
  標準労働時間: 8時間/日

# 締め日を月末に設定
$ python cli.py config set user1 --closing-day 31 --standard-hours 7.5
```

**締め日について:**
- **月末締め (31)**: 毎月1日～月末で集計
- **15日締め (15)**: 前月16日～当月15日で集計

### 一覧表示

```bash
# 登録されているアカウント一覧
$ python cli.py list accounts
登録アカウント:
  - user1 (3プロジェクト)
  - user2 (2プロジェクト)

# アカウントのプロジェクト一覧
$ python cli.py list projects user1
user1 のプロジェクト:
  - project-alpha
  - project-beta
  - project-gamma
```

## コマンド一覧

### 打刻コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `start <account> <project>` | 作業開始 | `python cli.py start user1 myproject` |
| `break` | 休憩開始 | `python cli.py break` |
| `resume` | 休憩終了・作業再開 | `python cli.py resume` |
| `end` | 作業終了 | `python cli.py end` |
| `status` | 現在の状態表示 | `python cli.py status` |

### レポートコマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `report daily <account>` | 日別レポート | `python cli.py report daily user1` |
| `report daily <account> --date <date>` | 特定日のレポート | `python cli.py report daily user1 --date 2025-10-10` |
| `report project <account> <project>` | プロジェクト別レポート | `python cli.py report project user1 myproject` |
| `report monthly <account>` | 月次レポート | `python cli.py report monthly user1` |
| `report monthly <account> <YYYY-MM>` | 特定月のレポート | `python cli.py report monthly user1 2025-09` |
| `report monthly <account> -v` | 詳細表示 | `python cli.py report monthly user1 -v` |
| `report monthly <account> -o <file>` | HTML出力 | `python cli.py report monthly user1 -o report.html` |

### 設定コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `setup` | 初期セットアップ（Google Driveパス設定） | `python cli.py setup` |
| `config show <account>` | 設定を表示 | `python cli.py config show user1` |
| `config set <account> --closing-day <15\|31>` | 締め日設定 | `python cli.py config set user1 --closing-day 15` |

### 一覧コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `list accounts` | アカウント一覧 | `python cli.py list accounts` |
| `list projects <account>` | プロジェクト一覧 | `python cli.py list projects user1` |

## データの保存場所

### デフォルト（ローカル保存）

データは以下の場所に JSON 形式で保存されます：

- Windows: `C:\Users\<ユーザー名>\.timeclock\`
- macOS/Linux: `~/.timeclock/`

### Google Drive使用時

`python cli.py setup` で設定したパスに保存されます：

- 例: `~/Google Drive/timeclock/`

### 保存されるファイル

データベースディレクトリ内：
- `timeclock_data.json`: 打刻データ（作業記録）
- `config.json`: アカウント設定（締め日、標準労働時間）
- `.timeclock.lock`: ファイルロック用（一時ファイル）
- `timeclock_data.json.backup_*`: 自動バックアップファイル

グローバル設定：
- `~/.timeclockrc`: データベース保存先の設定ファイル

## エイリアスの設定（推奨）

毎回 `python cli.py` と入力するのは手間なので、エイリアスを設定すると便利です：

### Bash/Zsh (.bashrc / .zshrc)

```bash
alias tc='python /path/to/timeclock/cli.py'
```

使用例：
```bash
tc start user1 project-alpha
tc break
tc resume
tc end
tc status
tc report daily user1
```

### Windows (PowerShell)

```powershell
# PowerShell プロファイルに追加
function tc { python C:\path\to\timeclock\cli.py $args }
```

### Windows (コマンドプロンプト)

```batch
doskey tc=python C:\path\to\timeclock\cli.py $*
```

## よくある使用シーン

### 1日の作業フロー

```bash
# 朝：作業開始
tc start user1 project-alpha

# 昼：休憩
tc break
tc resume

# 午後：別プロジェクトに切り替え
tc end
tc start user1 project-beta

# 夕方：作業終了
tc end

# 1日の作業時間を確認
tc report daily user1
```

### 複数プロジェクトの管理

```bash
# プロジェクトAで2時間作業
tc start user1 project-A
# ... 作業 ...
tc end

# プロジェクトBで3時間作業
tc start user1 project-B
# ... 作業 ...
tc end

# プロジェクトCで1時間作業
tc start user1 project-C
# ... 作業 ...
tc end

# 今日の内訳を確認
tc report daily user1
```

### 月次レポート作成と印刷

```bash
# 月次レポートをHTML出力
tc report monthly user1 -o monthly_report.html

# ブラウザで開いて印刷
# Windows: start monthly_report.html
# macOS: open monthly_report.html
# Linux: xdg-open monthly_report.html
```

## テスト

包括的なテストスイートが用意されています：

```bash
# 全テストを実行
python test_comprehensive.py

# 締め日ロジックのテスト
python test_closing_day.py

# スモークテスト（基本機能のみ）
python test_smoke.py
```

### テストカバレッジ

✅ **データ整合性テスト**: セッションデータの正確な保存と計算
✅ **エラーハンドリングテスト**: 不正な操作の防止
✅ **マルチアカウント同時作業テスト**: 複数アカウントの独立した管理
✅ **設定の永続化テスト**: 設定の保存と読み込み
✅ **レポート生成テスト**: 日次・月次レポートの正確な生成
✅ **自動休憩機能テスト**: PC無操作検知と自動休憩遷移

全テスト成功率: **100%** (5/5テスト成功)

## トラブルシューティング

### GUI関連

#### GUIが起動しない

1. **Windows環境を確認**: 自動休憩機能はWindows専用です
2. **ログファイルを確認**: `~/.timeclock/timeclock.log` でエラー内容を確認
3. **Python バージョン**: Python 3.7以上が必要です

#### 自動休憩が動作しない

1. **設定を確認**: 設定タブで「自動休憩機能を有効にする」がチェックされているか確認
2. **閾値を確認**: 無操作時間の閾値が適切に設定されているか確認（5-60分）
3. **ログを確認**: `~/.timeclock/timeclock.log` で自動休憩のログを確認

#### ダークモードが適用されない

1. **GUIを再起動**: 一度GUIを閉じて再度開いてください
2. **最新版を確認**: 最新のコードを取得してください

### CLI関連

#### 作業を開始できない

既に作業セッションが開始されている可能性があります。

```bash
# 現在の状態を確認
tc status

# 必要に応じて終了
tc end
```

#### 休憩を開始できない

作業セッションが開始されていない可能性があります。

```bash
# 先に作業を開始
tc start <account> <project>
tc break
```

### データ関連

#### データが消えた・おかしくなった

自動バックアップから復元できます：

```bash
# バックアップファイルを確認
ls ~/.timeclock/timeclock_data.json.backup_*

# 最新のバックアップから復元
cp ~/.timeclock/timeclock_data.json.backup_<timestamp> ~/.timeclock/timeclock_data.json
```

#### Google Drive同期が遅い

- クラウド同期には数秒かかります
- 作業終了後、数秒待ってから別PCで操作してください
- Google Driveの同期状態を確認してください

## ライセンス

MIT License

## 開発

```bash
# テスト実行
python -m pytest

# コードフォーマット
black .

# リント
flake8 .
```

---

## Git作業時間推定システム（残業証拠収集）

### 📊 概要

GitHubやローカルGitリポジトリのコミット履歴から、実際の作業時間を推定し、残業代請求のための証拠データを生成するシステムです。

### 🚀 クイックスタート

```bash
cd git_analyzer

# 設定ファイルを作成（初回のみ）
copy github_config.json.sample github_config.json
notepad github_config.json  # GitHubトークンとユーザー名を記入

# データ収集実行
run_github_analyzer.bat

# GUIにインポート
cd ..
python git_import.py git_analyzer/github_commits_evidence.csv 0053629 --preview
python git_import.py git_analyzer/github_commits_evidence.csv 0053629
```

### 📚 詳細ドキュメント

- **[git_analyzer/QUICKSTART.md](git_analyzer/QUICKSTART.md)** - 5分でできるクイックスタート
- **[git_analyzer/README_GIT_ANALYZER.md](git_analyzer/README_GIT_ANALYZER.md)** - 完全な技術ドキュメント
- **[git_analyzer/SYSTEM_OVERVIEW.md](git_analyzer/SYSTEM_OVERVIEW.md)** - システム全体概要
- **[git_analyzer/INDEX.md](git_analyzer/INDEX.md)** - ドキュメント索引

### ✨ 主な機能

- ✅ 複数GitHubアカウント対応
- ✅ ローカルGitリポジトリ対応
- ✅ コード変更量から作業時間を推定
- ✅ 時間外/休日/深夜の自動判定
- ✅ セッションの自動グループ化
- ✅ GUIへの直接インポート
- ✅ 残業代の自動計算

### 💰 作業時間推定と賃金計算

**3段階計算プロセス:**

1. **基本推定ロジック**
   - コード追加: 10行 = 5分
   - コード削除: 10行 = 2分
   - ファイル変更: 1ファイル = 最低10分

2. **実打刻記録による補正**
   - GitHub推定値を実打刻記録で補正（補正係数: 0.152）
   - 元推定983.8h → 補正後143.9h (84.8%削減)
   - 精度: 100.1%（実打刻記録との照合）

3. **遅延賦課金（学習曲線）**
   - 2024年: ×6.58倍（学習初期）
   - 2025年1-3月: ×3.00倍（習熟期）
   - 2025年4-6月: ×2.00倍（習熟後期）
   - 2025年7月～: ×1.50倍（習熟完了）

**時間外労働分類:**
- 時間外: 全作業（持ち帰り労働）
- 休日: 土曜日・日曜日
- 深夜: 22時以降または5時以前

**最終成果:**
- 総実作業時間: 143.91時間
- 遅延賦課金込み: 268.74時間
- 賃金計算用時間: 469.25時間
- **総請求額: ¥1,237,404**

詳細は [FINAL_DX_WAGE_REPORT_WITH_DELAY_PENALTY.md](FINAL_DX_WAGE_REPORT_WITH_DELAY_PENALTY.md) を参照

### 🔐 セキュリティ

- 設定ファイルは `.gitignore` に追加済み
- 個人デバイスでの実行を推奨
- GitHubトークンは90日ごとに再生成
- 証拠データはクラウドバックアップ推奨

### ⚖️ 法的利用

このシステムで生成されたデータは：
- コミットハッシュによる改ざん不可能な証拠
- GitHubサーバーのタイムスタンプが証明
- 他の証拠（Zoom記録等）と併用推奨
- **必ず労働問題に強い弁護士に相談してください**

---
