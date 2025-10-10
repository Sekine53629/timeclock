# Windows環境での打刻コマンドエイリアス設定

## PowerShellでのエイリアス設定（推奨）

### 1. PowerShellプロファイルの作成・編集

PowerShellを開いて以下のコマンドを実行：

```powershell
# プロファイルの場所を確認
echo $PROFILE

# プロファイルが存在しない場合は作成
if (!(Test-Path -Path $PROFILE)) {
    New-Item -Type File -Path $PROFILE -Force
}

# プロファイルを編集
notepad $PROFILE
```

### 2. プロファイルにエイリアスを追加

開いたメモ帳に以下を追加（パスは環境に合わせて変更）：

```powershell
# 打刻システムのエイリアス
function timeclock { python C:\Users\imao3\Documents\GitHub\timeclock\cli.py $args }
Set-Alias tc timeclock

# よく使うコマンドの短縮版
function tc-in { python C:\Users\imao3\Documents\GitHub\timeclock\cli.py checkin $args }
function tc-out { python C:\Users\imao3\Documents\GitHub\timeclock\cli.py checkout $args }
function tc-status { python C:\Users\imao3\Documents\GitHub\timeclock\cli.py status $args }
function tc-report { python C:\Users\imao3\Documents\GitHub\timeclock\cli.py report $args }
```

### 3. プロファイルを再読み込み

```powershell
. $PROFILE
```

### 4. 使用例

```powershell
# 打刻開始
tc checkin -p "プロジェクトA"

# ステータス確認
tc status

# 短縮版を使用
tc-in -p "プロジェクトB"
tc-out
tc-status
```

## コマンドプロンプト（CMD）でのバッチファイル設定

### 1. バッチファイルの作成

`C:\Users\imao3\bin` フォルダを作成し、以下のバッチファイルを配置：

**tc.bat:**
```batch
@echo off
python C:\Users\imao3\Documents\GitHub\timeclock\cli.py %*
```

**tc-in.bat:**
```batch
@echo off
python C:\Users\imao3\Documents\GitHub\timeclock\cli.py checkin %*
```

**tc-out.bat:**
```batch
@echo off
python C:\Users\imao3\Documents\GitHub\timeclock\cli.py checkout %*
```

**tc-status.bat:**
```batch
@echo off
python C:\Users\imao3\Documents\GitHub\timeclock\cli.py status %*
```

### 2. PATHに追加

1. システムのプロパティを開く（Win + Pause/Break）
2. 「システムの詳細設定」→「環境変数」をクリック
3. ユーザー環境変数の「Path」を選択して「編集」
4. 「新規」をクリックして `C:\Users\imao3\bin` を追加
5. 「OK」をクリックして保存

### 3. 使用例

新しいコマンドプロンプトを開いて：

```cmd
# 打刻開始
tc checkin -p "プロジェクトA"

# ステータス確認
tc status

# 短縮版を使用
tc-in -p "プロジェクトB"
tc-out
tc-status
```

## Windows Terminal統合（オプション）

Windows Terminalを使用している場合、カスタムプロファイルを追加できます。

### settings.jsonに追加：

```json
{
    "profiles": {
        "list": [
            {
                "name": "Timeclock Status",
                "commandline": "powershell.exe -NoExit -Command \"python C:\\Users\\imao3\\Documents\\GitHub\\timeclock\\cli.py status\"",
                "icon": "⏰",
                "startingDirectory": "%USERPROFILE%"
            }
        ]
    }
}
```

## Git Bashでのエイリアス設定

Git Bashを使用している場合は、`~/.bashrc` または `~/.bash_profile` に追加：

```bash
# 打刻システムのエイリアス
alias tc='python /c/Users/imao3/Documents/GitHub/timeclock/cli.py'
alias tc-in='tc checkin'
alias tc-out='tc checkout'
alias tc-status='tc status'
alias tc-report='tc report'
```

## トラブルシューティング

### Q: PowerShellで「スクリプトの実行がシステムで無効」エラー
A: 管理者権限でPowerShellを開き、以下を実行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: Pythonが認識されない
A: Pythonのパスが環境変数に設定されているか確認：
```powershell
python --version
```

表示されない場合は、Pythonのインストールパス（例：`C:\Python39`）をPATHに追加してください。

### Q: 文字化けする
A: PowerShellで文字コードをUTF-8に設定：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

この設定もPowerShellプロファイルに追加することをお勧めします。