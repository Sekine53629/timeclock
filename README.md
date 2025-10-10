# 打刻システム (TimeClock)

プロジェクト別に作業時間を管理するCLI打刻システムです。複数のアカウント・プロジェクトの作業時間を記録し、日別・プロジェクト別のレポートを出力できます。

## 特徴

- ✅ プロジェクト別の作業時間管理
- ✅ 複数アカウント対応
- ✅ 休憩時間の記録
- ✅ 日別・プロジェクト別・月次レポート
- ✅ プロジェクト別残業時間の自動計算
- ✅ 15日締め・月末締め対応
- ✅ HTML形式での印刷可能なレポート出力
- ✅ シンプルなCLIインターフェース

## インストール

```bash
# リポジトリのクローン
git clone <repository-url>
cd timeclock

# Python 3.7以上が必要です
python --version
```

## 使い方

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
残業時間: 1時間30分 ⚠️

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
# 今月の月次レポート（プロジェクト別残業時間含む）
$ python cli.py report monthly user1

============================================================
【月次レポート - 2025年10月】(月末締め)
============================================================
アカウント: user1
集計期間: 2025-10-01 ～ 2025-10-31
稼働日数: 22日

総作業時間: 185時間30分 (185.50時間)
標準労働時間: 176時間00分 (176.00時間)
総残業時間: 9時間30分 (9.50時間) ⚠️

============================================================
【プロジェクト別内訳】
============================================================

■ project-alpha
  稼働日数: 15日
  作業時間: 105時間30分 (105.50時間)
  残業時間: 5時間45分 (5.75時間) ⚠️

■ project-beta
  稼働日数: 12日
  作業時間: 80時間00分 (80.00時間)
  残業時間: 3時間45分 (3.75時間) ⚠️

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
| `config show <account>` | 設定を表示 | `python cli.py config show user1` |
| `config set <account> --closing-day <15\|31>` | 締め日設定 | `python cli.py config set user1 --closing-day 15` |

### 一覧コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `list accounts` | アカウント一覧 | `python cli.py list accounts` |
| `list projects <account>` | プロジェクト一覧 | `python cli.py list projects user1` |

## データの保存場所

データは以下の場所に JSON 形式で保存されます：

- Windows: `C:\Users\<ユーザー名>\.timeclock\`
- macOS/Linux: `~/.timeclock/`

保存されるファイル:
- `timeclock_data.json`: 打刻データ（作業記録）
- `config.json`: アカウント設定（締め日、標準労働時間）

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

## トラブルシューティング

### 作業を開始できない

既に作業セッションが開始されている可能性があります。

```bash
# 現在の状態を確認
tc status

# 必要に応じて終了
tc end
```

### 休憩を開始できない

作業セッションが開始されていない可能性があります。

```bash
# 先に作業を開始
tc start <account> <project>
tc break
```

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
