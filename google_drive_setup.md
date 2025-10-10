# Google Drive連携の正しい設定方法（Mac/Windows両対応）

## 問題の原因
プログラムがGoogle DriveのWebURL（`https://drive.google.com/...`）を直接ファイルパスとして使用しようとしたため、Windowsでファイル名に使用できない文字（`:`）を含むファイル名が作成されてエラーが発生しました。

## 正しい設定方法

### 1. Google Drive デスクトップアプリのインストール
1. [Google Drive for Desktop](https://www.google.com/drive/download/)をダウンロード・インストール
2. Google アカウントでログイン
3. 同期するフォルダを選択

### 2. プラットフォーム別のローカルパス

#### macOS
**新しいGoogle Drive for desktop（推奨）:**
```
~/Library/CloudStorage/GoogleDrive-[メールアドレス]/My Drive/timeclock
```
例：
```
~/Library/CloudStorage/GoogleDrive-user@gmail.com/My Drive/timeclock
```

**古いBackup and Sync:**
```
~/Google Drive/timeclock
または
~/Google Drive/My Drive/timeclock
```

#### Windows
**通常のインストール:**
```
C:\Users\[ユーザー名]\Google Drive\My Drive\timeclock
```

**Gドライブとしてマウント:**
```
G:\My Drive\timeclock
```

#### Linux
```
~/Google Drive/timeclock
```

### 3. 打刻システムの設定

初期設定コマンドを実行：
```bash
python cli.py setup
```

システムが自動的にGoogle Driveのパスを検出し、候補を表示します。

#### 設定例（macOS）：
```
検出されたOS: Darwin
  macOS環境です

検出された候補:
  1. /Users/username/Library/CloudStorage/GoogleDrive-user@gmail.com/My Drive/timeclock ✓
  2. /Users/username/Documents/timeclock
  3. /Users/username/.timeclock

保存先パス: 1
デフォルトアカウント: work
```

#### 設定例（Windows）：
```
検出されたOS: Windows
  Windows環境です

検出された候補:
  1. G:\My Drive\timeclock ✓
  2. C:\Users\username\Google Drive\My Drive\timeclock ✓
  3. C:\Users\username\Documents\timeclock
  4. C:\Users\username\.timeclock

保存先パス: 1
デフォルトアカウント: personal
```

### 4. 設定ファイル（~/.timeclockrc）の内容

設定ファイルは自動的に可搬性のある形式で保存されます：

**macOS/Linux:**
```json
{
  "db_path": "~/Library/CloudStorage/GoogleDrive-user@gmail.com/My Drive/timeclock",
  "default_account": "work"
}
```

**Windows:**
```json
{
  "db_path": "~/Google Drive/My Drive/timeclock",
  "default_account": "personal"
}
```

## バックアップファイルの管理

バックアップファイルは以下の場所に自動保存されます：
- メインデータ: `[db_path]/timeclock_data.json`
- バックアップ: `[db_path]/backups/timeclock_data.json.backup_YYYYMMDD_HHMMSS`

## 複数デバイスでの使用

### Mac → Windows 間の移行
1. 両方のデバイスで同じGoogle アカウントにログイン
2. Google Drive for Desktopをインストール
3. 各デバイスで`python cli.py setup`を実行
4. 自動検出されたGoogle Driveパスを選択

### 注意事項
- ファイルロック機能により同時編集は防止されます
- 設定ファイル（~/.timeclockrc）は各デバイスで個別に作成されます
- パスは相対パス（~/）で保存されるため、異なるユーザー名でも動作します

## トラブルシューティング

### Q: macOSでGoogle Driveフォルダが見つからない
A: 新しいGoogle Drive for desktopでは以下の場所に保存されます：
```
~/Library/CloudStorage/GoogleDrive-[メールアドレス]/
```
Finderで「ライブラリ」フォルダを表示するには、`Cmd + Shift + G`で`~/Library`を入力してください。

### Q: Windowsで「invalid path」エラーが発生する
A: パス区切り文字を確認してください：
- 正しい: `C:\Users\username\Google Drive\My Drive\timeclock`
- 間違い: `C:/Users/username/Google Drive/My Drive/timeclock`

### Q: Google Driveが同期されない
A: 以下を確認してください：
- **macOS**: メニューバーのGoogle Driveアイコンが同期中でないか
- **Windows**: タスクトレイのGoogle Driveアイコンを確認
- 両OS共通: Google Driveアプリで「同期を一時停止」していないか確認

### Q: 複数のGoogleアカウントを使用している
A: Google Drive for desktopは複数アカウントに対応しています：
- macOS: `~/Library/CloudStorage/`内に複数の`GoogleDrive-`フォルダが作成されます
- Windows: 各アカウントごとに異なるドライブレターが割り当てられることがあります

### Q: バックアップファイルが多すぎる
A: 古いバックアップは定期的に手動で削除してください。将来のバージョンで自動削除機能を追加予定です。