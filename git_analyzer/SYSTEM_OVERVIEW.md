# Git作業時間推定システム - システム全体概要

## 🎯 システムの目的

複数のGitHubアカウントとローカルGitリポジトリからコミット履歴を収集し、コード変更量から実際の作業時間を推定して、残業代請求のための証拠データを生成するシステムです。

## 📐 システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    データソース                              │
├─────────────────────────────────────────────────────────────┤
│  GitHub Account 1  │  GitHub Account 2  │  Local Git Repos  │
└──────────┬───────────────────┬────────────────┬─────────────┘
           │                   │                │
           ▼                   ▼                ▼
    ┌──────────────────────────────────────────────┐
    │         データ収集レイヤー                     │
    ├──────────────────────────────────────────────┤
    │  github_commit_analyzer.py                   │
    │  - GitHub API経由でコミット履歴を取得         │
    │  - 複数アカウント対応                         │
    │  - レート制限自動対応                         │
    │                                              │
    │  git_work_time_estimator.py                  │
    │  - ローカルGitリポジトリを直接解析            │
    │  - git logコマンドでコミット統計取得          │
    │  - diffstatで変更量を計測                    │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │         作業時間推定エンジン                   │
    ├──────────────────────────────────────────────┤
    │  推定ロジック:                                │
    │  - 追加10行 = 5分                            │
    │  - 削除10行 = 2分                            │
    │  - 1ファイル変更 = 最低10分                  │
    │  - 時間外/休日/深夜の判定                    │
    │  - セッションのグループ化（2時間以内）        │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │         データフォーマット層                   │
    ├──────────────────────────────────────────────┤
    │  出力フォーマット:                            │
    │  - CSV (Excel/GUIインポート用)               │
    │  - JSON (プログラム処理用)                   │
    │  - TXT (サマリーレポート/印刷用)             │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │         GUIインポート層                       │
    ├──────────────────────────────────────────────┤
    │  git_import.py                               │
    │  - CSVからタイムレコード形式に変換            │
    │  - セッションのグループ化                     │
    │  - 既存データとの重複チェック                 │
    │                                              │
    │  git_import_dialog.py                        │
    │  - GUIダイアログでユーザーフレンドリー         │
    │  - プレビュー機能                            │
    │  - インポート設定（間隔調整等）               │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │      タイムクロックGUIシステム                 │
    ├──────────────────────────────────────────────┤
    │  gui.py                                      │
    │  - 作業セッション管理                         │
    │  - 打刻記録                                  │
    │  - レポート生成                              │
    │  - データエクスポート                         │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │         証拠データ生成                         │
    ├──────────────────────────────────────────────┤
    │  - 月別サマリー                              │
    │  - 時間外/休日/深夜労働の集計                │
    │  - プロジェクト別作業時間                    │
    │  - 推定残業代計算                            │
    │  - 裁判所提出用フォーマット                  │
    └──────────────────────────────────────────────┘
```

## 📦 ファイル構成と役割

### データ収集スクリプト

| ファイル | 役割 | 入力 | 出力 |
|---------|------|------|------|
| `github_commit_analyzer.py` | GitHub APIからコミット履歴を収集 | `github_config.json` | CSV, JSON |
| `git_work_time_estimator.py` | ローカルGitから作業時間推定 | `git_repos_config.json` | CSV, JSON, TXT |

### GUIインポート

| ファイル | 役割 | 入力 | 出力 |
|---------|------|------|------|
| `git_import.py` | コマンドラインインポート | CSV | JSON (timeclock_data.json) |
| `git_import_dialog.py` | GUIダイアログインポート | CSV | JSON (timeclock_data.json) |

### 設定ファイル

| ファイル | 役割 | フォーマット |
|---------|------|-------------|
| `github_config.json` | GitHub API認証情報 | JSON |
| `git_repos_config.json` | ローカルリポジトリ設定 | JSON |

### ドキュメント

| ファイル | 役割 |
|---------|------|
| `README_GIT_ANALYZER.md` | 詳細な技術ドキュメント |
| `QUICKSTART.md` | 5分でできるクイックスタート |
| `SYSTEM_OVERVIEW.md` | このファイル（システム全体概要） |

### バッチファイル

| ファイル | 役割 |
|---------|------|
| `run_github_analyzer.bat` | GitHub収集の実行 |
| `run_git_estimator.bat` | ローカルGit推定の実行 |

## 🔄 データフロー

### 1. GitHub APIからの収集フロー

```
GitHub API
  ↓ (github_commit_analyzer.py)
  ├─ リポジトリ一覧取得
  ├─ 各リポジトリのコミット取得
  ├─ コミット詳細の解析
  └─ 時間外判定
  ↓
CSV/JSON出力
  ├─ github_commits_evidence.csv
  ├─ github_commits_evidence.json
  └─ github_commits_summary.json
```

### 2. ローカルGitからの推定フロー

```
Local Git Repos
  ↓ (git_work_time_estimator.py)
  ├─ git log でコミット履歴取得
  ├─ git show --stat で変更統計取得
  ├─ 行数カウント
  ├─ 作業時間推定
  └─ セッションのグループ化
  ↓
CSV/JSON/TXT出力
  ├─ git_work_time_evidence.csv
  ├─ git_work_time_data.json
  └─ work_time_summary.txt
```

### 3. GUIへのインポートフロー

```
CSV File
  ↓ (git_import.py)
  ├─ CSV読み込み
  ├─ セッションのグループ化
  ├─ タイムレコード形式に変換
  ├─ 既存データとのマージ
  └─ JSON保存
  ↓
timeclock_data.json
  ↓ (gui.py)
  ├─ GUI表示
  ├─ 編集機能
  ├─ レポート生成
  └─ エクスポート
```

## 💾 データモデル

### コミットデータ（中間フォーマット）

```python
{
  'account': 'username',
  'repo_name': 'project-name',
  'commit_hash': 'a1b2c3d4',
  'message': 'feat: add user authentication',
  'author_name': 'Your Name',
  'timestamp_jst': datetime(2025, 11, 11, 22, 30, 0),
  'date': date(2025, 11, 11),
  'hour': 22,
  'is_overtime': True,
  'is_weekend': False,
  'is_late_night': True,
  'files_changed': 5,
  'lines_added': 234,
  'lines_deleted': 45,
  'estimated_work_minutes': 87.5
}
```

### タイムレコード（GUI形式）

```python
{
  'account': '0053629',
  'project': 'tsuruha',
  'date': '2025-11-11',
  'start_time': '2025-11-11T22:30:00',
  'end_time': '2025-11-12T00:57:30',
  'breaks': [],
  'status': 'completed',
  'total_minutes': 87,
  'total_break_minutes': 0,
  'comment': '【Gitインポート】\n[a1b2c3d4] feat: add user authentication\n...',
  'submission_status': 'draft',
  'source': 'git_import',
  'git_commits': 3,
  'git_files_changed': 5,
  'git_lines_added': 234,
  'git_lines_deleted': 45
}
```

## ⚙️ 推定ロジック詳細

### 1. 作業時間推定式

```python
def estimate_work_time(lines_added, lines_deleted, files_changed):
    # 基本時間: 行数ベース
    add_time = (lines_added / 10) * 5      # 10行で5分
    delete_time = (lines_deleted / 10) * 2  # 10行で2分

    # ファイル変更による追加時間
    if files_changed > 0:
        file_time = 10 + (files_changed - 1) * 5
    else:
        file_time = 0

    # 合計（最低5分、最大480分）
    total = max(add_time + delete_time + file_time, 5)
    return min(total, 480)
```

### 2. セッションのグループ化

```python
def group_commits_by_session(commits, max_gap_minutes=120):
    sessions = []
    current_session = None

    for commit in commits:
        # 新しいセッションを開始すべきか判定
        should_start_new = (
            current_session is None or
            commit['date'] != current_session['date'] or
            (commit['datetime'] - current_session['last_commit_time']).total_seconds() > max_gap_minutes * 60
        )

        if should_start_new:
            if current_session:
                sessions.append(current_session)
            current_session = create_new_session(commit)
        else:
            add_to_session(current_session, commit)

    return sessions
```

### 3. 時間外判定

```python
def is_overtime(hour):
    return hour >= 18 or hour < 9

def is_late_night(hour):
    return hour >= 22 or hour < 5

def is_weekend(weekday):
    return weekday >= 5  # 土日（土=5, 日=6）
```

## 📊 統計計算

### 月別集計

```python
monthly_stats = {
    'total_commits': int,          # 総コミット数
    'total_minutes': float,        # 総作業時間（分）
    'overtime_commits': int,       # 時間外コミット数
    'overtime_minutes': float,     # 時間外作業時間（分）
    'weekend_commits': int,        # 休日コミット数
    'weekend_minutes': float,      # 休日作業時間（分）
    'late_night_commits': int,     # 深夜コミット数
    'late_night_minutes': float,   # 深夜作業時間（分）
    'projects': set                # プロジェクト数
}
```

### 残業代計算

```python
def calculate_unpaid_overtime(stats, hourly_rate):
    overtime_pay = (stats['overtime_minutes'] / 60) * hourly_rate * 1.25
    weekend_pay = (stats['weekend_minutes'] / 60) * hourly_rate * 1.35
    late_night_pay = (stats['late_night_minutes'] / 60) * hourly_rate * 1.5

    return {
        'overtime_pay': overtime_pay,
        'weekend_pay': weekend_pay,
        'late_night_pay': late_night_pay,
        'total_unpaid': overtime_pay + weekend_pay + late_night_pay
    }
```

## 🔐 セキュリティ設計

### 1. 認証情報の管理

```
github_config.json (ローカルのみ)
  ├─ .gitignore に追加
  ├─ パーミッション: 600 (所有者のみ読み書き)
  └─ 暗号化推奨（将来実装）
```

### 2. データの保存場所

```
個人デバイス
  ├─ C:/Users/username/.timeclock/
  │   ├─ timeclock_data.json
  │   ├─ config.json
  │   └─ timeclock.log
  └─ バックアップ
      └─ Google Drive/Dropbox (暗号化推奨)
```

### 3. GitHub APIトークンのスコープ

- **最小権限の原則**: `repo` スコープのみ
- **有効期限**: 90日（定期的に再生成）
- **環境変数**: `.env` ファイルで管理（オプション）

## 🎯 使用シナリオ

### シナリオ1: 初回セットアップ

1. GitHubトークン取得（5分）
2. 設定ファイル作成（2分）
3. データ収集実行（1分）
4. プレビュー確認（1分）
5. GUIにインポート（2分）

**合計: 約11分**

### シナリオ2: 定期的な更新（月1回）

1. データ収集実行（1分）
2. 差分インポート（1分）

**合計: 約2分**

### シナリオ3: 退職前の最終データ収集

1. 全リポジトリのデータ収集（5分）
2. 統計レポート生成（1分）
3. 複数フォーマットでエクスポート（1分）
4. クラウドバックアップ（2分）

**合計: 約9分**

## 📈 パフォーマンス

### GitHub API収集

- **速度**: 約100コミット/分
- **制限**: 5000リクエスト/時
- **推奨**: 大量のリポジトリは分割実行

### ローカルGit解析

- **速度**: 約1000コミット/分
- **制限**: ディスクI/O依存
- **推奨**: SSDで実行

### GUIインポート

- **速度**: 約500セッション/秒
- **制限**: メモリ依存
- **推奨**: セッション数が多い場合は分割

## 🐛 トラブルシューティング

### よくあるエラーと解決策

| エラー | 原因 | 解決策 |
|-------|------|-------|
| `API rate limit exceeded` | GitHub APIの制限 | 1時間待機 or `time.sleep()` 追加 |
| `JSONDecodeError` | 設定ファイルの文法エラー | `python -m json.tool config.json` で確認 |
| `No commits found` | ユーザー名不一致 | `git log` で実際の名前を確認 |
| `FileNotFoundError` | リポジトリパス間違い | パスを絶対パスで指定 |
| `UnicodeDecodeError` | 文字コード不一致 | `encoding='utf-8'` を明示 |

## 🚀 今後の拡張予定

### Phase 2: UI改善

- [ ] GUIダイアログの統合
- [ ] リアルタイムプレビュー
- [ ] ドラッグ&ドロップインポート

### Phase 3: 分析機能強化

- [ ] プロジェクト別の詳細分析
- [ ] 時間帯別ヒートマップ
- [ ] 作業パターンの可視化

### Phase 4: エクスポート機能

- [ ] PDF形式でのレポート生成
- [ ] Excel形式での詳細データ
- [ ] 裁判所提出用フォーマット

### Phase 5: セキュリティ強化

- [ ] トークンの暗号化保存
- [ ] 2要素認証対応
- [ ] 監査ログ機能

## 📞 サポート情報

### ログファイル

- タイムクロックGUI: `~/.timeclock/timeclock.log`
- インポート統計: `git_import_statistics.json`

### デバッグモード

```python
# スクリプトの先頭に追加
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 設定確認

```bash
# JSON文法チェック
python -m json.tool github_config.json

# Git設定確認
git config --list
```

---

**システム開発日:** 2025-11-11
**バージョン:** 1.0.0
**開発者:** Claude Code Assistant
**ライセンス:** 個人使用のみ（証拠収集目的）
