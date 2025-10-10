# PowerShellプロファイルの詳細設定ガイド

## PowerShellプロファイルとは
PowerShellプロファイルは、PowerShellを起動するたびに自動的に実行されるスクリプトファイルです。エイリアス、関数、変数などを定義できます。

## プロファイルの種類と場所

### 1. プロファイルの種類
PowerShellには複数のプロファイルがあり、適用範囲が異なります：

| プロファイルの種類 | 変数 | デフォルトパス |
|---|---|---|
| 現在のユーザー、現在のホスト | `$PROFILE` | `C:\Users\[username]\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` |
| 現在のユーザー、全てのホスト | `$PROFILE.CurrentUserAllHosts` | `C:\Users\[username]\Documents\WindowsPowerShell\profile.ps1` |
| 全てのユーザー、現在のホスト | `$PROFILE.AllUsersCurrentHost` | `C:\Windows\System32\WindowsPowerShell\v1.0\Microsoft.PowerShell_profile.ps1` |
| 全てのユーザー、全てのホスト | `$PROFILE.AllUsersAllHosts` | `C:\Windows\System32\WindowsPowerShell\v1.0\profile.ps1` |

### 2. PowerShell Core (PowerShell 7+) の場合
```
C:\Users\[username]\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

### 3. Windows PowerShell 5.1 の場合
```
C:\Users\[username]\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
```

## プロファイルの確認と作成

### 現在のプロファイルパスを確認
```powershell
# 使用中のプロファイルパスを表示
$PROFILE

# 全てのプロファイルパスを表示
$PROFILE | Format-List * -Force

# PowerShellのバージョンを確認
$PSVersionTable.PSVersion
```

### プロファイルの存在確認
```powershell
# プロファイルが存在するか確認
Test-Path $PROFILE

# 結果：
# True  - 存在する
# False - 存在しない
```

### プロファイルの作成
```powershell
# プロファイルとその親ディレクトリを作成
if (!(Test-Path -Path $PROFILE)) {
    # 親ディレクトリが存在しない場合は作成
    $profileDir = Split-Path -Parent $PROFILE
    if (!(Test-Path -Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force
    }

    # プロファイルファイルを作成
    New-Item -ItemType File -Path $PROFILE -Force
    Write-Host "プロファイルを作成しました: $PROFILE"
} else {
    Write-Host "プロファイルは既に存在します: $PROFILE"
}
```

## 実行ポリシーの設定

PowerShellスクリプトを実行するには、実行ポリシーを設定する必要があります。

### 現在の実行ポリシーを確認
```powershell
Get-ExecutionPolicy -List
```

### 実行ポリシーの設定（管理者権限不要）
```powershell
# 現在のユーザーに対してのみ設定（推奨）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 確認プロンプトをスキップする場合
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### 実行ポリシーのレベル
- `Restricted`: スクリプト実行不可（デフォルト）
- `RemoteSigned`: ローカルスクリプトは実行可、リモートは署名必要（推奨）
- `Unrestricted`: 全てのスクリプトを実行可（警告あり）
- `Bypass`: 全てのスクリプトを警告なしで実行

## 打刻システム用のプロファイル設定

### 完全版プロファイル内容
以下の内容を `$PROFILE` ファイルに記載：

```powershell
# ======================================
# PowerShell プロファイル設定
# ======================================

# UTF-8エンコーディングの設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ======================================
# 打刻システム (Timeclock) 設定
# ======================================

# プロジェクトパスの設定（環境に合わせて変更）
$TIMECLOCK_PATH = "C:\Users\imao3\Documents\GitHub\timeclock"

# メイン関数
function timeclock {
    param(
        [Parameter(Position=0, ValueFromRemainingArguments=$true)]
        [string[]]$Arguments
    )

    if (Test-Path "$TIMECLOCK_PATH\cli.py") {
        python "$TIMECLOCK_PATH\cli.py" @Arguments
    } else {
        Write-Host "エラー: 打刻システムが見つかりません: $TIMECLOCK_PATH" -ForegroundColor Red
        Write-Host "パスを確認して、`$PROFILE を編集してください。" -ForegroundColor Yellow
    }
}

# エイリアスの設定
Set-Alias -Name tc -Value timeclock

# よく使うコマンドの関数定義
function tc-in {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account,
        [Parameter(Mandatory=$true)]
        [string]$project
    )
    timeclock start $account $project
}

function tc-out {
    timeclock end
}

function tc-break {
    timeclock break
}

function tc-resume {
    timeclock resume
}

function tc-status {
    timeclock status
}

function tc-report-daily {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account,
        [string]$date,
        [int]$standardHours = 8,
        [switch]$verbose
    )
    $args = @('report', 'daily', $account)
    if ($date) { $args += '--date', $date }
    if ($standardHours -ne 8) { $args += '--standard-hours', $standardHours }
    if ($verbose) { $args += '-v' }
    timeclock @args
}

function tc-report-monthly {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account,
        [string]$yearMonth,
        [string]$output,
        [switch]$verbose
    )
    $args = @('report', 'monthly', $account)
    if ($yearMonth) { $args += $yearMonth }
    if ($output) { $args += '-o', $output }
    if ($verbose) { $args += '-v' }
    timeclock @args
}

function tc-report-project {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account,
        [Parameter(Mandatory=$true)]
        [string]$project,
        [string]$startDate,
        [string]$endDate
    )
    $args = @('report', 'project', $account, $project)
    if ($startDate) { $args += '--start-date', $startDate }
    if ($endDate) { $args += '--end-date', $endDate }
    timeclock @args
}

function tc-list-accounts {
    timeclock list accounts
}

function tc-list-projects {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account
    )
    timeclock list projects $account
}

function tc-setup {
    timeclock setup
}

function tc-config-show {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account
    )
    timeclock config show $account
}

function tc-config-set {
    param(
        [Parameter(Mandatory=$true)]
        [string]$account,
        [Parameter(Mandatory=$true)]
        [ValidateSet(15, 31)]
        [int]$closingDay,
        [int]$standardHours = 8
    )
    timeclock config set $account --closing-day $closingDay --standard-hours $standardHours
}

# ヘルプ関数
function tc-help {
    Write-Host ""
    Write-Host "打刻システム コマンド一覧" -ForegroundColor Cyan
    Write-Host "=========================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "基本コマンド:" -ForegroundColor Yellow
    Write-Host "  tc start [account] [project] : 作業開始"
    Write-Host "  tc end                       : 作業終了"
    Write-Host "  tc break                     : 休憩開始"
    Write-Host "  tc resume                    : 休憩終了・作業再開"
    Write-Host "  tc status                    : 現在の状態確認"
    Write-Host ""
    Write-Host "短縮コマンド:" -ForegroundColor Yellow
    Write-Host "  tc-in [account] [project]              : 作業開始"
    Write-Host "  tc-out                                 : 作業終了"
    Write-Host "  tc-break                               : 休憩開始"
    Write-Host "  tc-resume                              : 休憩終了"
    Write-Host "  tc-status                              : 状態確認"
    Write-Host ""
    Write-Host "レポート関連:" -ForegroundColor Yellow
    Write-Host "  tc-report-daily [account]              : 日別レポート（今日）"
    Write-Host "  tc-report-daily [account] -date [date] : 日別レポート（指定日）"
    Write-Host "  tc-report-monthly [account]            : 月次レポート（今月）"
    Write-Host "  tc-report-monthly [account] [YYYY-MM]  : 月次レポート（指定月）"
    Write-Host "  tc-report-project [account] [project]  : プロジェクト別レポート"
    Write-Host ""
    Write-Host "管理コマンド:" -ForegroundColor Yellow
    Write-Host "  tc-list-accounts                       : アカウント一覧"
    Write-Host "  tc-list-projects [account]             : プロジェクト一覧"
    Write-Host "  tc-config-show [account]               : 設定表示"
    Write-Host "  tc-config-set [account] -closingDay XX : 設定変更"
    Write-Host "  tc-setup                               : 初期設定"
    Write-Host "  tc-help                                : このヘルプを表示"
    Write-Host ""
    Write-Host "使用例:" -ForegroundColor Green
    Write-Host "  tc-in sammy-inc project-a              # Sammy社のプロジェクトAで作業開始"
    Write-Host "  tc-break                               # 休憩"
    Write-Host "  tc-resume                              # 作業再開"
    Write-Host "  tc-out                                 # 作業終了"
    Write-Host "  tc-report-monthly sammy-inc            # 今月のレポート表示"
    Write-Host "  tc-report-monthly sammy-inc 2025-10    # 2025年10月のレポート"
    Write-Host ""
}

# 起動時メッセージ（オプション）
Write-Host "打刻システムが読み込まれました。'tc-help' でコマンド一覧を表示" -ForegroundColor Green

# ======================================
# その他の便利な設定
# ======================================

# プロンプトのカスタマイズ（オプション）
function prompt {
    $currentPath = (Get-Location).Path
    $shortPath = Split-Path -Leaf $currentPath
    Write-Host "PS " -NoNewline -ForegroundColor Green
    Write-Host "$shortPath" -NoNewline -ForegroundColor Yellow
    return "> "
}

# ls の色付け（オプション）
$PSStyle.FileInfo.Directory = "`e[34m"  # ディレクトリを青色に
```

## プロファイルの編集方法

### 方法1: メモ帳で編集
```powershell
notepad $PROFILE
```

### 方法2: VSCodeで編集（VSCodeがインストールされている場合）
```powershell
code $PROFILE
```

### 方法3: PowerShell ISEで編集
```powershell
ise $PROFILE
```

## プロファイルの再読み込み

### 変更を即座に反映
```powershell
. $PROFILE
```
または
```powershell
& $PROFILE
```

## トラブルシューティング

### Q: プロファイルが読み込まれない
```powershell
# プロファイルが正しく読み込まれているか確認
Test-Path $PROFILE

# 実行ポリシーを確認
Get-ExecutionPolicy

# 詳細なエラーを表示
$Error[0].Exception
```

### Q: 文字化けする
プロファイルに以下を追加：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### Q: Python が見つからない
```powershell
# Pythonのパスを確認
where.exe python

# 環境変数PATHを確認
$env:PATH -split ';' | Select-String python
```

### Q: プロファイルの場所がわからない
```powershell
# 全てのプロファイルパスを表示
Write-Host "CurrentUserCurrentHost: $($PROFILE.CurrentUserCurrentHost)"
Write-Host "CurrentUserAllHosts: $($PROFILE.CurrentUserAllHosts)"
Write-Host "AllUsersCurrentHost: $($PROFILE.AllUsersCurrentHost)"
Write-Host "AllUsersAllHosts: $($PROFILE.AllUsersAllHosts)"
```

## セキュリティの注意事項

1. **実行ポリシー**: `RemoteSigned`が推奨。`Unrestricted`や`Bypass`は避ける
2. **プロファイルの権限**: 他のユーザーが編集できないように権限を設定
3. **パスワード**: プロファイルにパスワードや機密情報を記載しない

## バックアップの推奨

プロファイルのバックアップを作成：
```powershell
# バックアップを作成
Copy-Item $PROFILE "$PROFILE.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# バックアップの確認
Get-ChildItem (Split-Path $PROFILE) -Filter "*.backup_*"
```