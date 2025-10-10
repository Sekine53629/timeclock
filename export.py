"""
レポート出力モジュール
HTML/PDF形式でのレポート生成
"""
from datetime import datetime
from typing import Dict
import html

def format_time_html(minutes: int) -> str:
    """分を時間:分形式に変換"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}時間{mins:02d}分"

def generate_monthly_report_html(summary: Dict) -> str:
    """
    月次レポートをHTML形式で生成

    Args:
        summary: get_monthly_summary() の戻り値

    Returns:
        HTML文字列
    """
    closing_day_text = "月末締め" if summary['closing_day'] == 31 else "15日締め"

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>月次レポート - {summary['year']}年{summary['month']}月</title>
    <style>
        body {{
            font-family: 'Segoe UI', 'Yu Gothic', 'Meiryo', sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 10px;
            margin-top: 30px;
        }}
        .summary-box {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary-item {{
            margin: 10px 0;
            font-size: 16px;
        }}
        .label {{
            font-weight: bold;
            display: inline-block;
            width: 150px;
        }}
        .value {{
            color: #2980b9;
        }}
        .overtime {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .normal {{
            color: #27ae60;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .project-name {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        @media print {{
            body {{
                background-color: white;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>月次勤怠レポート - {summary['year']}年{summary['month']}月 ({closing_day_text})</h1>

        <div class="summary-box">
            <div class="summary-item">
                <span class="label">アカウント:</span>
                <span class="value">{html.escape(summary['account'])}</span>
            </div>
            <div class="summary-item">
                <span class="label">集計期間:</span>
                <span class="value">{summary['start_date']} ～ {summary['end_date']}</span>
            </div>
            <div class="summary-item">
                <span class="label">稼働日数:</span>
                <span class="value">{summary['working_days']}日</span>
            </div>
        </div>

        <div class="summary-box">
            <div class="summary-item">
                <span class="label">総作業時間:</span>
                <span class="value">{format_time_html(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)</span>
            </div>
            <div class="summary-item">
                <span class="label">標準労働時間:</span>
                <span class="value">{format_time_html(summary['standard_total_minutes'])} ({summary['standard_total_hours']:.2f}時間)</span>
            </div>
            <div class="summary-item">
                <span class="label">総残業時間:</span>
"""

    if summary['total_overtime_minutes'] > 0:
        html_content += f"""                <span class="overtime">{format_time_html(summary['total_overtime_minutes'])} ({summary['total_overtime_hours']:.2f}時間) ⚠️</span>
"""
    else:
        html_content += f"""                <span class="normal">なし ✓</span>
"""

    html_content += """            </div>
        </div>
"""

    # プロジェクト別統計
    if summary['project_stats']:
        html_content += """
        <h2>プロジェクト別内訳</h2>
        <table>
            <thead>
                <tr>
                    <th>プロジェクト</th>
                    <th>稼働日数</th>
                    <th>作業時間</th>
                    <th>残業時間</th>
                </tr>
            </thead>
            <tbody>
"""

        for project, stats in sorted(summary['project_stats'].items()):
            overtime_class = "overtime" if stats['overtime_minutes'] > 0 else "normal"
            overtime_icon = "⚠️" if stats['overtime_minutes'] > 0 else "✓"

            html_content += f"""                <tr>
                    <td class="project-name">{html.escape(project)}</td>
                    <td>{stats['days_worked_count']}日</td>
                    <td>{format_time_html(stats['total_minutes'])} ({stats['total_hours']:.2f}h)</td>
                    <td class="{overtime_class}">{format_time_html(stats['overtime_minutes'])} ({stats['overtime_hours']:.2f}h) {overtime_icon}</td>
                </tr>
"""

        html_content += """            </tbody>
        </table>
"""

    # 日別サマリー
    if summary['daily_stats']:
        html_content += """
        <h2>日別サマリー</h2>
        <table>
            <thead>
                <tr>
                    <th>日付</th>
                    <th>作業時間</th>
                    <th>残業時間</th>
                    <th>主なプロジェクト</th>
                </tr>
            </thead>
            <tbody>
"""

        standard_minutes = summary['standard_hours_per_day'] * 60

        for date, day_data in sorted(summary['daily_stats'].items()):
            total = day_data['total_minutes']
            overtime = max(0, total - standard_minutes)
            overtime_class = "overtime" if overtime > 0 else "normal"
            overtime_icon = "⚠️" if overtime > 0 else ""

            # プロジェクトを最大3つまで表示
            projects = sorted(day_data['projects'].items(), key=lambda x: x[1], reverse=True)[:3]
            projects_text = ", ".join([f"{p}" for p, _ in projects])

            html_content += f"""                <tr>
                    <td>{date}</td>
                    <td>{format_time_html(total)} ({total/60:.2f}h)</td>
                    <td class="{overtime_class}">{format_time_html(overtime)} {overtime_icon}</td>
                    <td>{html.escape(projects_text)}</td>
                </tr>
"""

        html_content += """            </tbody>
        </table>
"""

    # フッター
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content += f"""
        <div class="footer">
            <p>出力日時: {now}</p>
            <p>TimeClock - プロジェクト別作業時間管理システム</p>
        </div>
    </div>
</body>
</html>
"""

    return html_content

def save_html_report(summary: Dict, output_path: str):
    """
    月次レポートをHTMLファイルとして保存

    Args:
        summary: get_monthly_summary() の戻り値
        output_path: 出力先ファイルパス
    """
    html_content = generate_monthly_report_html(summary)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
