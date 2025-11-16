@echo off
chcp 65001 > nul
echo ========================================
echo GitHub Commit Analyzer
echo ========================================
echo.

REM 設定ファイルのチェック
if not exist github_config.json (
    echo エラー: github_config.json が見つかりません
    echo サンプルから作成してください:
    echo   copy github_config.json.sample github_config.json
    echo   メモ帳で github_config.json を開いて編集
    echo.
    pause
    exit /b 1
)

echo GitHub APIからコミット履歴を収集中...
python github_commit_analyzer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo エラーが発生しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo 完了！
echo ========================================
echo.
echo 生成されたファイル:
echo   - github_commits_evidence.csv
echo   - github_commits_evidence.json
echo   - github_commits_summary.json
echo.
echo 次のステップ:
echo   1. CSVファイルをExcelで確認
echo   2. GUIシステムにインポート:
echo      cd ..
echo      python git_import.py git_analyzer/github_commits_evidence.csv 0053629 --preview
echo.
pause
