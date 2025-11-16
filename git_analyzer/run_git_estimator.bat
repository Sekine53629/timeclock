@echo off
chcp 65001 > nul
echo ========================================
echo Git Work Time Estimator
echo ========================================
echo.

REM 設定ファイルのチェック
if not exist git_repos_config.json (
    echo エラー: git_repos_config.json が見つかりません
    echo サンプルから作成してください:
    echo   copy git_repos_config.json.sample git_repos_config.json
    echo   メモ帳で git_repos_config.json を開いて編集
    echo.
    pause
    exit /b 1
)

echo ローカルGitリポジトリから作業時間を推定中...
python git_work_time_estimator.py

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
echo   - git_work_time_evidence.csv
echo   - git_work_time_data.json
echo   - work_time_summary.txt
echo.
echo 次のステップ:
echo   1. work_time_summary.txt で内容確認
echo   2. GUIシステムにインポート:
echo      cd ..
echo      python git_import.py git_analyzer/git_work_time_evidence.csv 0053629 --preview
echo.
pause
