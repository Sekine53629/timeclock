# 📚 Git作業時間推定システム - ドキュメント索引

## 🚀 まず最初に読むべきドキュメント

1. **[QUICKSTART.md](QUICKSTART.md)** - 5分でできる！クイックスタートガイド
   - 初めての方はここから
   - 実行までの最短手順
   - よくある質問と解決策

## 📖 詳細ドキュメント

2. **[README_GIT_ANALYZER.md](README_GIT_ANALYZER.md)** - 完全な技術ドキュメント
   - ファイル構成の詳細
   - 使い方の全手順
   - 推定ロジックの説明
   - 法的証拠としての利用方法
   - トラブルシューティング

3. **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - システム全体概要
   - アーキテクチャ図
   - データフロー
   - データモデル詳細
   - セキュリティ設計
   - 今後の拡張予定

## 📁 ファイル一覧

### 実行ファイル

| ファイル名 | 説明 | 用途 |
|-----------|------|------|
| `github_commit_analyzer.py` | GitHub APIからコミット履歴を収集 | 複数GitHubアカウント対応 |
| `git_work_time_estimator.py` | ローカルGitリポジトリから作業時間推定 | プライベートリポジトリ対応 |
| `../timeclock/git_import.py` | GUIへのインポートツール | コマンドライン実行 |
| `../timeclock/git_import_dialog.py` | GUIダイアログ | GUI統合用 |

### 設定ファイル（サンプル）

| ファイル名 | 説明 | 作成方法 |
|-----------|------|---------|
| `github_config.json.sample` | GitHub API設定のサンプル | `copy github_config.json.sample github_config.json` |
| `git_repos_config.json.sample` | ローカルGit設定のサンプル | `copy git_repos_config.json.sample git_repos_config.json` |

### バッチファイル

| ファイル名 | 説明 | 実行方法 |
|-----------|------|---------|
| `run_github_analyzer.bat` | GitHub収集の実行 | ダブルクリック |
| `run_git_estimator.bat` | ローカルGit推定の実行 | ダブルクリック |

### ドキュメント

| ファイル名 | 対象読者 | 内容 |
|-----------|---------|------|
| `QUICKSTART.md` | 初心者 | 5分でできる最短手順 |
| `README_GIT_ANALYZER.md` | 全ユーザー | 完全な技術ドキュメント |
| `SYSTEM_OVERVIEW.md` | 開発者・上級者 | システム設計と内部構造 |
| `INDEX.md` | 全ユーザー | このファイル（ドキュメント索引） |

## 🎯 目的別ガイド

### 初めて使う方

1. [QUICKSTART.md](QUICKSTART.md) を読む
2. GitHubトークンを取得
3. 設定ファイルを作成
4. `run_github_analyzer.bat` を実行
5. GUIにインポート

### すでに設定済みの方

1. `run_github_analyzer.bat` を実行
2. 生成されたCSVを確認
3. 必要に応じてGUIにインポート

### トラブルが発生した方

1. [README_GIT_ANALYZER.md#トラブルシューティング](README_GIT_ANALYZER.md#トラブルシューティング) を確認
2. ログファイルを確認
3. 設定ファイルの文法チェック

### システムを理解したい方

1. [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) でアーキテクチャを理解
2. データフローを確認
3. 推定ロジックを理解

## 📊 出力ファイル一覧

### GitHub収集の出力

| ファイル名 | フォーマット | 用途 |
|-----------|------------|------|
| `github_commits_evidence.csv` | CSV | Excel/GUIインポート用 |
| `github_commits_evidence.json` | JSON | プログラム処理用 |
| `github_commits_summary.json` | JSON | サマリーレポート |

### ローカルGit推定の出力

| ファイル名 | フォーマット | 用途 |
|-----------|------------|------|
| `git_work_time_evidence.csv` | CSV | Excel/GUIインポート用 |
| `git_work_time_data.json` | JSON | プログラム処理用 |
| `work_time_summary.txt` | TXT | サマリーレポート（印刷用） |

### GUIインポートの出力

| ファイル名 | フォーマット | 用途 |
|-----------|------------|------|
| `git_import_statistics.json` | JSON | インポート統計 |
| `~/.timeclock/timeclock_data.json` | JSON | GUIデータベース |

## 🔄 典型的なワークフロー

### ワークフロー1: GitHub中心

```
1. run_github_analyzer.bat
   ↓
2. github_commits_evidence.csv 生成
   ↓
3. cd ../timeclock && python git_import.py ... --preview
   ↓
4. python git_import.py ... (実際にインポート)
   ↓
5. python gui.py (GUI起動して確認)
```

### ワークフロー2: ローカルGit中心

```
1. run_git_estimator.bat
   ↓
2. work_time_summary.txt で内容確認
   ↓
3. git_work_time_evidence.csv をExcelで確認
   ↓
4. cd ../timeclock && python git_import.py ... (インポート)
   ↓
5. python gui.py (GUI起動して確認)
```

### ワークフロー3: 両方統合

```
1. GitHub収集: run_github_analyzer.bat
   ↓
2. ローカルGit推定: run_git_estimator.bat
   ↓
3. 両方のCSVをExcelで結合
   ↓
4. 統合CSVをGUIにインポート
   ↓
5. レポート生成・エクスポート
```

## 📞 サポート情報

### ログファイルの場所

- **タイムクロックGUI**: `~/.timeclock/timeclock.log`
- **インポート統計**: `git_import_statistics.json`
- **エラーログ**: `error.log` (実行時に生成される場合)

### 設定ファイルの確認

```bash
# JSON文法チェック
python -m json.tool github_config.json
python -m json.tool git_repos_config.json

# Git設定の確認
git config user.name
git config user.email
```

### デバッグモード

スクリプトの先頭に以下を追加:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ⚖️ 法的利用時の注意

このシステムで生成されたデータを法的証拠として使用する場合:

1. **複数のバックアップを作成**
   - ローカル
   - クラウド（Google Drive等）
   - 外付けHDD

2. **タイムスタンプの保全**
   - コミットハッシュは改ざん不可
   - GitHubサーバーのタイムスタンプが証明

3. **弁護士への相談**
   - 労働問題に強い弁護士に相談
   - 法テラスの利用も検討

4. **他の証拠との併用**
   - Zoom記録
   - メール送信履歴
   - 社内システムログ

## 🔐 セキュリティチェックリスト

- [ ] `github_config.json` を `.gitignore` に追加
- [ ] `git_repos_config.json` を `.gitignore` に追加
- [ ] GitHubトークンを定期的に再生成（90日ごと）
- [ ] 個人デバイスで実行（会社PCは使わない）
- [ ] 生成データをクラウドにバックアップ
- [ ] トークンを環境変数で管理（オプション）

## 📈 バージョン履歴

### v1.0.0 (2025-11-11)

- ✅ GitHub API収集機能
- ✅ ローカルGit推定機能
- ✅ GUIインポート機能
- ✅ 作業時間推定エンジン
- ✅ セッションのグループ化
- ✅ 時間外/休日/深夜判定
- ✅ CSV/JSON/TXTエクスポート
- ✅ 完全なドキュメント

### 今後の予定

- [ ] GUIダイアログ統合
- [ ] PDFレポート生成
- [ ] 視覚化ダッシュボード
- [ ] トークン暗号化保存

## 🎓 学習リソース

### Python基礎

- [Python公式ドキュメント](https://docs.python.org/ja/3/)
- [Git コマンドリファレンス](https://git-scm.com/docs)

### GitHub API

- [GitHub REST API ドキュメント](https://docs.github.com/ja/rest)
- [Personal Access Tokens](https://github.com/settings/tokens)

### 労働法

- [労働基準法](https://elaws.e-gov.go.jp/document?lawid=322AC0000000049)
- [法テラス](https://www.houterasu.or.jp/)
- [日本労働弁護団](http://roudou-bengodan.org/)

## 💬 よくある質問（FAQ）

### Q1: GitHubとローカルGit、どちらを使うべき？

**A:** 両方使うのが理想ですが、優先順位は:
1. **GitHub**: 改ざん不可能な証拠として最強
2. **ローカルGit**: プライベートリポジトリの補完

### Q2: 2つのGitHubアカウントのデータを統合できる？

**A:** はい。`github_config.json` に両方のトークンとユーザー名を設定すれば、自動的に統合されます。

### Q3: 推定作業時間の精度は？

**A:** コミットの粒度に依存します。こまめにコミットするほど精度が上がります。

### Q4: 会社にバレる可能性は？

**A:** 個人デバイスで実行し、個人のGitHubアカウントを使用する限り、ほぼゼロです。

### Q5: 法的証拠として使える？

**A:** はい。ただし弁護士に相談し、他の証拠（メール、Zoom記録等）と併用することを推奨します。

## 📝 免責事項

このシステムは証拠収集のサポートツールであり、法的助言を提供するものではありません。
実際の訴訟や労働審判には、必ず労働問題に強い弁護士にご相談ください。

---

**最終更新:** 2025-11-11
**バージョン:** 1.0.0
**開発:** Claude Code Assistant

## 🎉 セットアップ完了後は

1. [QUICKSTART.md](QUICKSTART.md) で実行
2. データを確認
3. 定期的に更新（月1回推奨）
4. 退職前に最終データ収集
5. 弁護士に相談

**あなたの正当な権利を守るために、このツールをご活用ください。** 💪
