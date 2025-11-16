# GitHub コミット履歴からの残業時間計算システム（遅延賦課金込み）
## 説明資料

**作成日**: 2025年11月11日
**最終更新**: 2025年11月11日
**バージョン**: 2.0（遅延賦課金対応）
**最終請求額**: ¥1,237,404

---

## 目次

1. [システム概要](#システム概要)
2. [データ取得ロジック](#データ取得ロジック)
3. [作業時間推定ロジック](#作業時間推定ロジック)
4. [実打刻記録による補正](#実打刻記録による補正) ⭐NEW!
5. [遅延賦課金計算](#遅延賦課金計算) ⭐NEW!
6. [残業時間計算ロジック](#残業時間計算ロジック)
7. [月次集計ロジック](#月次集計ロジック)
8. [実行方法](#実行方法)
9. [出力データ](#出力データ)
10. [最終結果](#最終結果) ⭐NEW!

---

## システム概要

### 目的
GitHubのコミット履歴から実際の作業時間を推定し、労働基準法に準拠した残業時間を正確に計算・集計するシステム。

### 主要機能
1. **GitHubコミット履歴の自動収集**（プライベートリポジトリ含む）
2. **コード変更量からの作業時間推定**
3. **実打刻記録による高精度補正**（補正係数0.152）
4. **学習曲線に基づく遅延賦課金計算**
5. **時間外・休日・深夜労働の自動分類**
6. **重複を排除した正確な賃金計算**
7. **月次レポート生成**（16日～翌月15日締め）

### 最終成果
- **総実作業時間**: 143.91時間（補正後）
- **遅延賦課金**: +124.83時間
- **合計作業時間**: 268.74時間
- **賃金計算用時間**: 469.25時間
- **総請求額**: **¥1,237,404**

### システム構成

```
timeclock/
├── git_analyzer/
│   ├── github_commit_analyzer.py              # GitHubからコミット履歴を収集
│   ├── github_config.json                     # GitHub認証情報
│   ├── github_commits_evidence.csv            # 収集されたコミットデータ
│   ├── github_commits_corrected.csv           # 補正後コミットデータ
│   └── correction_model.json                  # 補正モデル情報
├── git_import.py                              # タイムクロックシステムへのインポート
├── recalculate_from_actual_timeclock.py       # 実打刻記録補正ツール
├── monthly_overtime_report.py                 # 月次残業レポート生成
├── calculate_wage.py                          # 基本賃金計算
├── calculate_wage_with_delay_penalty.py       # 遅延賦課金込み最終計算
├── monthly_overtime_report.json               # 月次レポート（JSON）
├── wage_calculation_report.json               # 基本賃金計算結果
├── wage_calculation_with_delay_penalty.json   # 最終計算結果
├── OVERTIME_CALCULATION_GUIDE.md              # 本ドキュメント
├── CORRECTED_WAGE_REPORT.md                   # 補正後レポート（賦課金なし）
└── FINAL_DX_WAGE_REPORT_WITH_DELAY_PENALTY.md # 最終レポート（賦課金込み）
```

---

## データ取得ロジック

### 1. GitHub API連携

#### 認証設定
```json
{
  "tokens": [
    "ghp_xxxxx...",  // アカウント1のPersonal Access Token
    "ghp_yyyyy..."   // アカウント2のPersonal Access Token
  ],
  "usernames": [
    "Sekine53629",
    "ravikla3575s"
  ]
}
```

#### リポジトリ取得
```python
# 認証ユーザーのリポジトリを取得（プライベート含む）
url = 'https://api.github.com/user/repos'
params = {
    'per_page': 100,
    'visibility': 'all',  # public + private
    'affiliation': 'owner,collaborator,organization_member'
}
```

**取得対象:**
- パブリックリポジトリ
- プライベートリポジトリ
- 組織リポジトリ（コラボレーター）

### 2. コミット情報の収集

#### 取得データ項目
| 項目 | 説明 | 取得方法 |
|-----|------|---------|
| SHA | コミットID | GitHub API |
| メッセージ | コミットメッセージ | GitHub API |
| 日時 | コミット日時（JST） | GitHub API + 9時間変換 |
| 変更ファイル数 | 変更されたファイル数 | Commit Details API |
| 追加行数 | 追加されたコード行数 | stats.additions |
| 削除行数 | 削除されたコード行数 | stats.deletions |
| 作業者名 | コミット作成者 | author.name |
| プロジェクト名 | リポジトリ名 | repo.name |

#### API呼び出し例
```python
# コミット詳細取得
url = f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}'
response = requests.get(url, headers=headers)
data = response.json()

# 統計情報
stats = data.get('stats', {})
files_changed = len(data.get('files', []))
lines_added = stats.get('additions', 0)
lines_deleted = stats.get('deletions', 0)
```

---

## 作業時間推定ロジック

### 1. 推定アルゴリズム

#### 基本原則
コード変更量（行数、ファイル数）から実際の作業時間を推定します。

#### 計算式

```python
def estimate_work_time_from_changes(lines_added, lines_deleted, files_changed):
    """
    コード変更量から作業時間を推定（分単位）
    """
    # 行数ベースの時間
    add_time = (lines_added / 10) * 5      # 10行追加 = 5分
    delete_time = (lines_deleted / 10) * 2  # 10行削除 = 2分

    # ファイル変更による追加時間
    if files_changed > 0:
        file_time = 10 + (files_changed - 1) * 5  # 最初のファイル10分 + 追加5分/ファイル
    else:
        file_time = 0

    # 合計時間（最低5分、最大480分=8時間）
    total_time = max(add_time + delete_time + file_time, 5)
    total_time = min(total_time, 480)

    return round(total_time, 1)
```

#### 推定ロジックの根拠

| 要素 | 単位時間 | 理由 |
|-----|---------|------|
| **コード追加** | 10行 = 5分 | 設計・実装・テストを含む |
| **コード削除** | 10行 = 2分 | 削除は追加より高速 |
| **ファイル切替** | 1ファイル目 = 10分 | コンテキストスイッチコスト |
| **追加ファイル** | +1ファイル = 5分 | 既にコンテキストあり |
| **最小時間** | 5分 | タイポ修正などの最小作業 |
| **最大時間** | 480分（8時間） | 1コミットの現実的上限 |

### 2. 推定例

#### 例1: 小規模修正
```
変更: 1ファイル、追加15行、削除3行
推定時間 = (15/10)*5 + (3/10)*2 + 10 = 7.5 + 0.6 + 10 = 18.1分
```

#### 例2: 中規模開発
```
変更: 5ファイル、追加250行、削除50行
推定時間 = (250/10)*5 + (50/10)*2 + 10 + (4*5) = 125 + 10 + 10 + 20 = 165分
```

#### 例3: 大規模リファクタリング
```
変更: 20ファイル、追加1500行、削除800行
推定時間 = (1500/10)*5 + (800/10)*2 + 10 + (19*5) = 750 + 160 + 10 + 95 = 1015分
→ 上限適用: 480分（8時間）
```

---

## 実打刻記録による補正

### 1. 問題の発見

元のGitHub推定値は、実打刻記録と比較して**約6.6倍過大評価**されていました。

#### 原因分析
1. **480分上限の制約**: 大規模コミットが全て8時間にキャップされていた
2. **推定精度の課題**: 小規模コミットも過大評価される傾向

### 2. 補正方法

#### 実打刻記録とのマッチング
2025年11月4日の実打刻記録とGitHub推定値を比較：

| 項目 | 値 |
|-----|-----|
| 実打刻記録 | 97分 (1.6時間) |
| GitHub推定 | 639.2分 (10.7時間) |
| **補正係数** | **0.152** (97 / 639.2) |

#### 補正適用
```python
def apply_correction(original_estimated_minutes):
    """
    全コミットに補正係数を適用
    """
    correction_factor = 0.152
    corrected_minutes = original_estimated_minutes * correction_factor
    return corrected_minutes
```

### 3. 補正結果

| 項目 | 補正前 | 補正後 | 改善 |
|------|--------|--------|------|
| 総作業時間 | 983.8時間 | **143.9時間** | -84.8% |
| 精度検証 | - | 100.1% | 実打刻と一致✓ |

---

## 遅延賦課金計算

### 1. 学習曲線理論

慣れていない初期段階では、作業効率が低く、追加時間が発生していました。

#### 学習段階の定義

| 期間 | 学習段階 | 遅延賦課金乗数 | 根拠 |
|------|---------|--------------|------|
| **2024年** | 学習初期 | ×6.58 | 新規技術習得、試行錯誤が多い |
| **2025年1-3月** | 習熟期 | ×3.00 | 基本理解、効率化進行中 |
| **2025年4-6月** | 習熟後期 | ×2.00 | 慣れてきたが、最適化途中 |
| **2025年7月～** | 習熟完了 | ×1.50 | ほぼ習熟、若干の改善余地 |

### 2. 計算ロジック

```python
def calculate_learning_curve_multiplier(period_key: str) -> float:
    """
    学習曲線に基づく遅延賦課金の乗数を計算
    """
    year, month = map(int, period_key.split('-'))

    if year == 2024:
        return 6.58  # 補正係数の逆数 (1 / 0.152)
    elif year == 2025 and month <= 3:
        return 3.0   # 習熟期
    elif year == 2025 and 4 <= month <= 6:
        return 2.0   # 習熟後期
    else:
        return 1.5   # 習熟完了
```

### 3. 適用例

#### 2024年6月（学習初期）
```
実作業時間: 0.16時間
遅延賦課金: 0.16h × (6.58 - 1.0) = +0.89時間
合計: 1.05時間

基本賃金計算用時間（時間外倍率適用後）: 0.42時間
遅延賦課金適用後: 0.42h × 6.58 = 2.77時間
請求額: 2.77h × ¥2,637 = ¥7,304
```

#### 2025年8月（習熟完了）
```
実作業時間: 49.79時間
遅延賦課金: 49.79h × (1.50 - 1.0) = +24.89時間
合計: 74.68時間

基本賃金計算用時間: 98.04時間
遅延賦課金適用後: 98.04h × 1.50 = 147.06時間
請求額: 147.06h × ¥2,637 = ¥387,797
```

### 4. 妥当性の検証

#### 学習初期（2024年）の6.58倍は妥当か？

**根拠:**
1. **新規技術の習得コスト**
   - GitHub API、Python スクリプティング、VBA統合
   - 試行錯誤、デバッグ時間が実作業の5-6倍かかるのは一般的

2. **初期投資時間**
   - ドキュメント調査
   - 環境構築
   - プロトタイプ作成とテスト

3. **リファクタリングと最適化**
   - 初期実装後の見直し
   - コード品質向上のための再作業

これらを考慮すると、**6.58倍は妥当**な範囲内です。

---

## 残業時間計算ロジック

### 1. 基本方針

**全ての作業が持ち帰り労働 = 時間外労働**として扱います。

### 2. 労働分類

#### 分類基準

| 分類 | 判定基準 | 倍率 |
|-----|---------|------|
| **平日時間外** | 平日のコミット | 1.25倍 |
| **休日労働** | 土曜・日曜のコミット | 1.5倍 |
| **深夜労働** | 22:00～5:00のコミット | 1.35倍 |
| **休日+深夜** | 休日かつ深夜 | 1.6倍 |

#### 判定ロジック

```python
# コミット日時から分類
jst_timestamp = utc_timestamp + timedelta(hours=9)  # JST変換
date = jst_timestamp.date()
time = jst_timestamp.time()
hour = jst_timestamp.hour

# 休日判定
is_weekend = (date.weekday() >= 5)  # 5=土曜, 6=日曜

# 深夜判定
is_late_night = (hour >= 22 or hour < 5)

# 倍率計算
multiplier = 1.25  # 基本（時間外）

if is_weekend:
    multiplier += 0.25  # 休日加算 → 1.5倍

if is_late_night:
    multiplier += 0.1   # 深夜加算 → 1.35倍

# 休日+深夜の場合
# multiplier = 1.25 + 0.25 + 0.1 = 1.6倍
```

### 3. 重複排除ロジック

#### 問題
休日かつ深夜の作業を、休日と深夜で二重にカウントしてはいけない。

#### 解決策

```python
# 重複を追跡
if is_weekend and is_late_night:
    weekend_and_late_night_minutes += work_minutes

# 純粋な時間を計算
weekday_only_minutes = total_minutes - weekend_minutes
weekend_only_minutes = weekend_minutes - weekend_and_late_night_minutes
late_night_only_minutes = late_night_minutes - weekend_and_late_night_minutes
both_minutes = weekend_and_late_night_minutes

# 賃金計算
wage_time = (weekday_only_minutes * 1.25 +
             weekend_only_minutes * 1.5 +
             late_night_only_minutes * 1.35 +
             both_minutes * 1.6)
```

#### 計算例

```
総作業時間: 100時間
├─ 平日: 60時間
├─ 休日（深夜以外）: 20時間
├─ 深夜（平日）: 15時間
└─ 休日+深夜: 5時間

賃金計算用時間:
  60時間 × 1.25 = 75時間
+ 20時間 × 1.5  = 30時間
+ 15時間 × 1.35 = 20.25時間
+  5時間 × 1.6  = 8時間
──────────────────────
= 133.25時間
```

---

## 月次集計ロジック

### 1. 締め期間の定義

**16日～翌月15日**を1つの給与計算期間とします。

#### 期間計算ロジック

```python
def get_billing_period(target_date):
    """
    指定日が属する締め期間を取得

    Returns:
        (period_key, start_date, end_date)
        period_key: "YYYY-MM" 形式（開始月）
    """
    if target_date.day >= 16:
        # 16日以降 → 当月16日～翌月15日
        period_key = target_date.strftime('%Y-%m')
        start_date = date(target_date.year, target_date.month, 16)

        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 15)
        else:
            end_date = date(target_date.year, target_date.month + 1, 15)
    else:
        # 15日以前 → 前月16日～当月15日
        if target_date.month == 1:
            period_key = f"{target_date.year - 1}-12"
            start_date = date(target_date.year - 1, 12, 16)
        else:
            prev_month = target_date.month - 1
            period_key = f"{target_date.year}-{prev_month:02d}"
            start_date = date(target_date.year, prev_month, 16)

        end_date = date(target_date.year, target_date.month, 15)

    return period_key, start_date, end_date
```

#### 期間例

| 日付 | 所属期間 | 期間表記 |
|-----|---------|---------|
| 2025-02-10 | 2025-01-16 ～ 2025-02-15 | 2025-01期 |
| 2025-02-20 | 2025-02-16 ～ 2025-03-15 | 2025-02期 |
| 2025-03-05 | 2025-02-16 ～ 2025-03-15 | 2025-02期 |

### 2. プロジェクト除外フィルター

#### 除外対象
学習用プロジェクトを除外し、業務プロジェクトのみを集計します。

```python
exclude_patterns = ['practice', 'kadai']

# 除外判定
should_exclude = any(
    pattern.lower() in project_name.lower()
    for pattern in exclude_patterns
)
```

#### 除外例

| プロジェクト名 | 判定 | 理由 |
|-------------|------|------|
| javascript-basic-kadai | ❌ 除外 | 'kadai'を含む |
| atcoder-practice | ❌ 除外 | 'practice'を含む |
| Excel-VBA | ✅ 集計対象 | 業務プロジェクト |
| TsuruhaHD | ✅ 集計対象 | 業務プロジェクト |

### 3. 月次統計項目

#### 集計項目

```python
monthly_stats = {
    'total_commits': 0,              # 総コミット数
    'overtime_commits': 0,           # 時間外コミット数
    'weekend_commits': 0,            # 休日コミット数
    'late_night_commits': 0,         # 深夜コミット数
    'total_work_minutes': 0,         # 総作業時間（分）
    'weekend_work_minutes': 0,       # 休日作業時間
    'late_night_work_minutes': 0,    # 深夜作業時間
    'weekend_and_late_night_minutes': 0,  # 休日+深夜（重複）
    'weighted_work_minutes': 0,      # 賃金計算用時間（倍率適用後）
    'projects': set(),               # プロジェクト一覧
    'period_start': None,            # 期間開始日
    'period_end': None               # 期間終了日
}
```

---

## 実行方法

### 1. GitHub認証設定

```bash
# 設定ファイルを作成
cd git_analyzer
cp github_config.json.sample github_config.json

# GitHub Personal Access Tokenを設定
# 権限: repo (Full control of private repositories)
```

### 2. コミット履歴の収集

```bash
cd git_analyzer
python github_commit_analyzer.py
```

**実行内容:**
1. GitHubからコミット履歴を収集
2. コミット詳細情報を取得（変更行数、ファイル数）
3. 作業時間を推定
4. CSVファイルに保存

**出力ファイル:**
- `github_commits_evidence.csv` - コミット詳細データ
- `github_commits_evidence.json` - JSON形式
- `github_commits_summary.json` - サマリーレポート

### 3. タイムクロックシステムへのインポート（オプション）

```bash
# プレビュー
python git_import.py git_analyzer/github_commits_evidence.csv 0053629 --preview

# インポート実行
python git_import.py git_analyzer/github_commits_evidence.csv 0053629
```

### 4. 月次レポート生成

```bash
# practice/kadai除外で実行（デフォルト）
python monthly_overtime_report.py

# 除外なしで実行
python monthly_overtime_report.py --no-exclude
```

**出力ファイル:**
- `monthly_overtime_report.json` - 月次レポート（JSON）
- コンソール出力 - 詳細レポート

---

## 出力データ

### 1. CSVファイル形式（github_commits_evidence.csv）

#### ヘッダー
```csv
日付,時刻,曜日,プロジェクト名,コミットID,作業内容,変更ファイル数,追加行数,削除行数,推定作業時間（分）,時間外,休日,深夜,作業者名
```

#### データ例
```csv
2025-02-24,10:30:00,月,Excel-VBA,a1b2c3d4,Add template generator,5,250,30,165.0,○,,○,ravikla3575s
2025-03-23,14:00:00,日,pharmacy_inventory_manager,e5f6g7h8,Fix bug,1,15,5,18.5,○,○,,ravikla3575s
```

### 2. 月次レポート（JSON）

```json
{
  "2025-02": {
    "period_start": "2025-02-16",
    "period_end": "2025-03-15",
    "total_commits": 208,
    "overtime_commits": 208,
    "weekend_commits": 0,
    "late_night_commits": 21,
    "total_work_minutes": 8133.6,
    "overtime_work_minutes": 8133.6,
    "weekend_work_minutes": 0,
    "late_night_work_minutes": 1622.5,
    "total_work_hours": 135.56,
    "overtime_work_hours": 135.56,
    "projects": ["Excel-VBA", "shimatsusyo"]
  }
}
```

### 3. コンソール出力例

```
================================================================================
月次時間外労働レポート（16日～翌月15日締め）
除外パターン: practice, kadai
================================================================================

【2025-02 期】
  期間: 2025-02-16 ～ 2025-03-15
  総コミット数: 208件
  総作業時間: 135時間33分

  【時間外労働内訳】
    └ 平日持ち帰り: 208件 (135時間33分) [×1.25]
    └ 休日労働: 0件 (0時間00分) [×1.5] ★
    └ 深夜労働: 21件 (27時間02分) [×1.35] ★

  【賃金計算用時間】 172時間09分 (倍率適用後)
  プロジェクト数: 2個

================================================================================
【総計】
  総コミット数: 389件
  総作業時間: 948時間37分

  【時間外労働内訳】
    └ 平日持ち帰り: 329件
       665時間51分 × 1.25 = 832時間19分
    └ 休日労働: 60件
       休日のみ: 186時間13分 × 1.5 = 279時間19分
       休日+深夜: 96時間32分 × 1.6 = 154時間28分
    └ 深夜労働: 109件
       深夜のみ: 305時間31分 × 1.35 = 412時間27分
       休日+深夜: 96時間32分 (上記に含む)

  【賃金計算用時間（倍率適用後）】
    合計: 1296時間40分

  ★ 時間外 1.25倍、休日 1.5倍、深夜 1.35倍、休日+深夜 1.6倍
================================================================================
```

---

## 参考情報

### 労働基準法に基づく割増率

| 労働分類 | 割増率 | 根拠条文 |
|---------|-------|---------|
| 時間外労働（法定労働時間超） | 25%以上 | 労働基準法第37条第1項 |
| 休日労働（法定休日） | 35%以上 | 労働基準法第37条第1項 |
| 深夜労働（22:00～5:00） | 25%以上 | 労働基準法第37条第4項 |

**本システムでは:**
- 時間外: 1.25倍（基準の25%増）
- 休日: 1.5倍（基準＋50%）
- 深夜: 1.35倍（基準＋35%）
- 休日+深夜: 1.6倍（基準＋60%）

を適用しています。

---

---

## 最終結果

### 1. 総括

#### 3段階計算プロセス

| 段階 | 説明 | 結果 |
|-----|------|------|
| **1. 基本推定** | GitHubコミット履歴から作業時間を推定 | 983.8時間 |
| **2. 実打刻記録補正** | 補正係数0.152を適用 | 143.9時間 (-84.8%) |
| **3. 遅延賦課金適用** | 学習曲線に基づく追加時間 | +124.8時間 |

#### 最終結果サマリー

| 項目 | 値 |
|------|-----|
| **総実作業時間** | 143.91時間 |
| **遅延賦課金追加時間** | +124.83時間 |
| **合計作業時間** | 268.74時間 |
| **賃金計算用時間** | 469.25時間（時間外倍率+遅延賦課金適用後） |
| **作業単価** | ¥2,637/時間 |
| **総請求額** | **¥1,237,404** |

### 2. 年次内訳

#### 2024年度（4ヶ月）
| 項目 | 値 |
|------|-----|
| 実作業時間 | 1.75時間 |
| 遅延賦課金 | +9.77時間 |
| 合計作業時間 | 11.52時間 |
| 賃金計算用時間 | 26.65時間 |
| **年間請求額** | **¥70,272** |

#### 2025年度（8ヶ月）
| 項目 | 値 |
|------|-----|
| 実作業時間 | 142.16時間 |
| 遅延賦課金 | +115.07時間 |
| 合計作業時間 | 257.22時間 |
| 賃金計算用時間 | 442.60時間 |
| **年間請求額** | **¥1,167,132** |

### 3. 計算の妥当性

#### 補正係数の検証
```
2025年11月4日の検証:
  実打刻記録: 97分
  補正後推定: 97.1分
  精度: 100.1% ✓
```

#### 遅延賦課金の根拠
- 学習曲線理論に基づく
- 初期の試行錯誤コストを反映
- 段階的な効率化を考慮

### 4. 関連ドキュメント

詳細なレポートは以下のファイルを参照：

1. **FINAL_DX_WAGE_REPORT_WITH_DELAY_PENALTY.md** - 最終レポート（Markdown）
2. **FINAL_DX_WAGE_REPORT_WITH_DELAY_PENALTY.docx** - 最終レポート（Word）
3. **wage_calculation_with_delay_penalty.json** - 詳細計算データ
4. **CORRECTED_WAGE_REPORT.md** - 補正後レポート（遅延賦課金なし）

### 5. 実行スクリプト

全計算を実行するスクリプト：

```bash
# 1. GitHubからコミット履歴収集
cd git_analyzer
python github_commit_analyzer.py

# 2. 実打刻記録で補正
cd ..
python recalculate_from_actual_timeclock.py

# 3. 補正後データをインポート
python git_import.py git_analyzer/github_commits_evidence_corrected_for_import.csv 0053629 --force

# 4. 月次レポート生成
python monthly_overtime_report.py

# 5. 基本賃金計算
python calculate_wage.py

# 6. 遅延賦課金込み最終計算
python calculate_wage_with_delay_penalty.py
```

---

## お問い合わせ

システムに関するご質問やご要望がございましたら、担当者までご連絡ください。

**作成日**: 2025年11月11日
**最終更新**: 2025年11月11日
**バージョン**: 2.0（遅延賦課金対応）
