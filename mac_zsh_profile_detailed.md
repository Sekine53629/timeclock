# Zshプロファイルの詳細設定ガイド (macOS)

## Zshプロファイルとは
Zshプロファイルは、ターミナルを起動するたびに自動的に実行される設定ファイルです。エイリアス、関数、環境変数などを定義できます。

## プロファイルの種類と場所

### 1. プロファイルファイルの種類
Zshには複数の設定ファイルがあり、読み込まれる順序が異なります：

| ファイル名 | 読み込まれるタイミング | 用途 |
|---|---|---|
| `~/.zshenv` | 常に最初 | 環境変数の設定 |
| `~/.zprofile` | ログイン時 | ログインシェルの設定 |
| `~/.zshrc` | 対話シェル起動時 | エイリアス、関数、プロンプト（**最もよく使う**） |
| `~/.zlogin` | ログイン後 | ログイン後の処理 |
| `~/.zlogout` | ログアウト時 | ログアウト時の処理 |

### 2. macOSのデフォルト
macOS Catalina (10.15) 以降、デフォルトシェルはZshです：
```bash
# デフォルトシェルを確認
echo $SHELL
# 出力: /bin/zsh
```

### 3. 推奨ファイル
通常は **`~/.zshrc`** にエイリアスや関数を記述します。

## プロファイルの確認と作成

### 現在のプロファイルパスを確認
```bash
# zshrcファイルのパスを表示
echo ~/.zshrc

# zshrcファイルが存在するか確認
ls -la ~/.zshrc
```

### プロファイルの存在確認
```bash
# プロファイルが存在するか確認
test -f ~/.zshrc && echo "存在します" || echo "存在しません"
```

### プロファイルの作成
```bash
# .zshrcファイルを作成
touch ~/.zshrc

# 確認
ls -la ~/.zshrc
```

## 打刻システム用のプロファイル設定

### 完全版プロファイル内容
以下の内容を `~/.zshrc` ファイルに追記：

```bash
# ======================================
# Zsh プロファイル設定
# ======================================

# UTF-8エンコーディングの設定
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8

# ======================================
# 打刻システム (Timeclock) 設定
# ======================================

# プロジェクトパスの設定（環境に合わせて変更）
export TIMECLOCK_PATH="/Users/yoshipc/Documents/GitHub/GitHub_Sekine53629/timeclock"

# メイン関数
timeclock() {
    if [ -f "$TIMECLOCK_PATH/cli.py" ]; then
        python3 "$TIMECLOCK_PATH/cli.py" "$@"
    else
        echo "\033[31mエラー: 打刻システムが見つかりません: $TIMECLOCK_PATH\033[0m"
        echo "\033[33mパスを確認して、~/.zshrc を編集してください。\033[0m"
        return 1
    fi
}

# エイリアスの設定
alias tc='timeclock'

# よく使うコマンドの関数定義

# 作業開始
tc-in() {
    if [ $# -lt 2 ]; then
        echo "使用法: tc-in <account> <project>"
        return 1
    fi
    timeclock start "$1" "$2"
}

# 作業終了
tc-out() {
    timeclock end
}

# 休憩開始
tc-break() {
    timeclock break
}

# 休憩終了・作業再開
tc-resume() {
    timeclock resume
}

# 現在の状態確認
tc-status() {
    timeclock status
}

# 日別レポート
tc-report-daily() {
    local account="$1"
    local date=""
    local standard_hours=""
    local verbose=""

    shift

    while [ $# -gt 0 ]; do
        case "$1" in
            --date)
                date="$2"
                shift 2
                ;;
            --standard-hours)
                standard_hours="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose="-v"
                shift
                ;;
            *)
                echo "不明なオプション: $1"
                return 1
                ;;
        esac
    done

    local args=(report daily "$account")
    [ -n "$date" ] && args+=(--date "$date")
    [ -n "$standard_hours" ] && args+=(--standard-hours "$standard_hours")
    [ -n "$verbose" ] && args+=("$verbose")

    timeclock "${args[@]}"
}

# 月次レポート
tc-report-monthly() {
    local account="$1"
    local year_month=""
    local output=""
    local verbose=""

    shift

    while [ $# -gt 0 ]; do
        case "$1" in
            -o|--output)
                output="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose="-v"
                shift
                ;;
            20[0-9][0-9]-[0-1][0-9])
                year_month="$1"
                shift
                ;;
            *)
                echo "不明なオプション: $1"
                return 1
                ;;
        esac
    done

    local args=(report monthly "$account")
    [ -n "$year_month" ] && args+=("$year_month")
    [ -n "$output" ] && args+=(-o "$output")
    [ -n "$verbose" ] && args+=("$verbose")

    timeclock "${args[@]}"
}

# プロジェクト別レポート
tc-report-project() {
    local account="$1"
    local project="$2"
    local start_date=""
    local end_date=""

    shift 2

    while [ $# -gt 0 ]; do
        case "$1" in
            --start-date)
                start_date="$2"
                shift 2
                ;;
            --end-date)
                end_date="$2"
                shift 2
                ;;
            *)
                echo "不明なオプション: $1"
                return 1
                ;;
        esac
    done

    local args=(report project "$account" "$project")
    [ -n "$start_date" ] && args+=(--start-date "$start_date")
    [ -n "$end_date" ] && args+=(--end-date "$end_date")

    timeclock "${args[@]}"
}

# アカウント一覧
tc-list-accounts() {
    timeclock list accounts
}

# プロジェクト一覧
tc-list-projects() {
    if [ $# -lt 1 ]; then
        echo "使用法: tc-list-projects <account>"
        return 1
    fi
    timeclock list projects "$1"
}

# 初期設定
tc-setup() {
    timeclock setup
}

# 設定表示
tc-config-show() {
    if [ $# -lt 1 ]; then
        echo "使用法: tc-config-show <account>"
        return 1
    fi
    timeclock config show "$1"
}

# 設定変更
tc-config-set() {
    local account="$1"
    local closing_day=""
    local standard_hours="8"

    shift

    while [ $# -gt 0 ]; do
        case "$1" in
            --closing-day)
                closing_day="$2"
                shift 2
                ;;
            --standard-hours)
                standard_hours="$2"
                shift 2
                ;;
            *)
                echo "不明なオプション: $1"
                return 1
                ;;
        esac
    done

    if [ -z "$closing_day" ]; then
        echo "エラー: --closing-day は必須です"
        return 1
    fi

    timeclock config set "$account" --closing-day "$closing_day" --standard-hours "$standard_hours"
}

# ヘルプ関数
tc-help() {
    echo ""
    echo "\033[36m打刻システム コマンド一覧\033[0m"
    echo "\033[36m=========================\033[0m"
    echo ""
    echo "\033[33m基本コマンド:\033[0m"
    echo "  tc start [account] [project] : 作業開始"
    echo "  tc end                       : 作業終了"
    echo "  tc break                     : 休憩開始"
    echo "  tc resume                    : 休憩終了・作業再開"
    echo "  tc status                    : 現在の状態確認"
    echo ""
    echo "\033[33m短縮コマンド:\033[0m"
    echo "  tc-in [account] [project]              : 作業開始"
    echo "  tc-out                                 : 作業終了"
    echo "  tc-break                               : 休憩開始"
    echo "  tc-resume                              : 休憩終了"
    echo "  tc-status                              : 状態確認"
    echo ""
    echo "\033[33mレポート関連:\033[0m"
    echo "  tc-report-daily [account]              : 日別レポート（今日）"
    echo "  tc-report-daily [account] --date [date]: 日別レポート（指定日）"
    echo "  tc-report-monthly [account]            : 月次レポート（今月）"
    echo "  tc-report-monthly [account] [YYYY-MM]  : 月次レポート（指定月）"
    echo "  tc-report-project [account] [project]  : プロジェクト別レポート"
    echo ""
    echo "\033[33m管理コマンド:\033[0m"
    echo "  tc-list-accounts                       : アカウント一覧"
    echo "  tc-list-projects [account]             : プロジェクト一覧"
    echo "  tc-config-show [account]               : 設定表示"
    echo "  tc-config-set [account] --closing-day XX: 設定変更"
    echo "  tc-setup                               : 初期設定"
    echo "  tc-help                                : このヘルプを表示"
    echo ""
    echo "\033[32m使用例:\033[0m"
    echo "  tc-in sammy-inc project-a              # Sammy社のプロジェクトAで作業開始"
    echo "  tc-break                               # 休憩"
    echo "  tc-resume                              # 作業再開"
    echo "  tc-out                                 # 作業終了"
    echo "  tc-report-monthly sammy-inc            # 今月のレポート表示"
    echo "  tc-report-monthly sammy-inc 2025-10    # 2025年10月のレポート"
    echo ""
}

# 起動時メッセージ（オプション）
echo "\033[32m打刻システムが読み込まれました。'tc-help' でコマンド一覧を表示\033[0m"

# ======================================
# その他の便利な設定
# ======================================

# プロンプトのカスタマイズ（オプション）
# シンプルなプロンプト: ディレクトリ名のみ表示
# PROMPT='%F{green}%1~%f %# '

# Git情報付きプロンプト（gitブランチを表示）
# autoload -Uz vcs_info
# precmd_vcs_info() { vcs_info }
# precmd_functions+=( precmd_vcs_info )
# setopt prompt_subst
# RPROMPT='${vcs_info_msg_0_}'
# zstyle ':vcs_info:git:*' formats '%F{yellow}(%b)%f'
# zstyle ':vcs_info:*' enable git

# ls の色付け（macOS）
export CLICOLOR=1
export LSCOLORS=ExGxBxDxCxEgEdxbxgxcxd

# エイリアス（その他便利なもの）
alias ll='ls -lah'
alias la='ls -A'
alias l='ls -CF'

# historyの設定
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt share_history
setopt hist_ignore_dups
setopt hist_ignore_all_dups
```

## プロファイルの編集方法

### 方法1: nanoエディタで編集（シンプル）
```bash
nano ~/.zshrc
```
- `Ctrl + O`: 保存
- `Ctrl + X`: 終了

### 方法2: Vimで編集
```bash
vim ~/.zshrc
```
- `i`: 挿入モード
- `Esc`: コマンドモード
- `:wq`: 保存して終了

### 方法3: VSCodeで編集（推奨）
```bash
code ~/.zshrc
```

### 方法4: デフォルトエディタで開く
```bash
open -e ~/.zshrc
```

## プロファイルの再読み込み

### 変更を即座に反映
```bash
source ~/.zshrc
```

または

```bash
. ~/.zshrc
```

### 新しいターミナルタブを開く
新しいタブを開くと自動的に再読み込みされます。

## 簡単セットアップスクリプト

以下のコマンドを実行すると、自動的に設定が追加されます：

```bash
# バックアップを作成
cp ~/.zshrc ~/.zshrc.backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || touch ~/.zshrc

# 設定を追加
cat >> ~/.zshrc << 'EOF'

# ======================================
# 打刻システム (Timeclock) 設定
# ======================================

export TIMECLOCK_PATH="/Users/yoshipc/Documents/GitHub/GitHub_Sekine53629/timeclock"

timeclock() {
    if [ -f "$TIMECLOCK_PATH/cli.py" ]; then
        python3 "$TIMECLOCK_PATH/cli.py" "$@"
    else
        echo "\033[31mエラー: 打刻システムが見つかりません: $TIMECLOCK_PATH\033[0m"
        return 1
    fi
}

alias tc='timeclock'
alias tc-in='tc start'
alias tc-out='tc end'
alias tc-break='tc break'
alias tc-resume='tc resume'
alias tc-status='tc status'

echo "\033[32m打刻システムが読み込まれました。'tc --help' でコマンド一覧を表示\033[0m"
EOF

# 再読み込み
source ~/.zshrc
```

## トラブルシューティング

### Q: プロファイルが読み込まれない
```bash
# zshrcファイルが存在するか確認
ls -la ~/.zshrc

# シェルを確認
echo $SHELL

# bashを使っている場合は ~/.bashrc か ~/.bash_profile に記述
```

### Q: 文字化けする
```bash
# エンコーディングを確認
echo $LANG

# UTF-8に設定
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
```

### Q: Python が見つからない
```bash
# Pythonのパスを確認
which python3

# Pythonのバージョンを確認
python3 --version

# Homebrewでインストールする場合
brew install python3
```

### Q: コマンドが見つからない
```bash
# エイリアスが設定されているか確認
alias | grep tc

# 関数が定義されているか確認
type tc
type timeclock

# プロファイルを再読み込み
source ~/.zshrc
```

### Q: パスが間違っている
```bash
# 現在のディレクトリを確認
pwd

# 正しいパスを環境変数に設定
export TIMECLOCK_PATH="/正しい/パス/timeclock"

# またはプロファイルを編集
nano ~/.zshrc
```

## セキュリティの注意事項

1. **パーミッション**: プロファイルファイルは自分だけが編集できるようにする
   ```bash
   chmod 600 ~/.zshrc
   ```

2. **パスワード**: プロファイルにパスワードや機密情報を記載しない

3. **スクリプトの内容**: 不明なスクリプトをコピペしない

## バックアップの推奨

プロファイルのバックアップを作成：

```bash
# バックアップを作成
cp ~/.zshrc ~/.zshrc.backup_$(date +%Y%m%d_%H%M%S)

# バックアップの確認
ls -la ~/.zshrc.backup_*

# バックアップから復元（必要な場合）
cp ~/.zshrc.backup_YYYYMMDD_HHMMSS ~/.zshrc
source ~/.zshrc
```

## よくある質問

### .zshrc と .bash_profile の違いは？
- **`.zshrc`**: Zsh用（macOS 10.15以降のデフォルト）
- **`.bash_profile`** / **`.bashrc`**: Bash用（古いmacOS）

現在のシェルを確認：
```bash
echo $SHELL
```

### Oh My Zsh を使っている場合は？
Oh My Zshを使っている場合も、`.zshrc`に設定を追加できます。
通常は `# User configuration` セクションに追加します。

### 複数のPCで同じ設定を使いたい
`.zshrc`ファイルをGitHubやクラウドストレージで管理し、各PCでシンボリックリンクを作成：

```bash
# dotfilesリポジトリを作成（例）
ln -s ~/dotfiles/.zshrc ~/.zshrc
```

## まとめ

1. **基本設定**: `~/.zshrc`に設定を追加
2. **パスの変更**: `TIMECLOCK_PATH`を自分の環境に合わせる
3. **再読み込み**: `source ~/.zshrc`で反映
4. **確認**: `tc --help`でテスト
5. **バックアップ**: 定期的にバックアップを作成

これで打刻システムが快適に使えるようになります！
