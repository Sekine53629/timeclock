#!/usr/bin/env python3
"""
打刻システム CLI インターフェース
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from timeclock import TimeClock
from storage import Storage
from export import save_html_report

def format_time(minutes: int) -> str:
    """分を時間:分形式に変換"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}時間{mins:02d}分"

def format_datetime(iso_string: str) -> str:
    """ISO形式の日時を読みやすい形式に変換"""
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def cmd_start(args):
    """作業開始"""
    tc = TimeClock()
    try:
        session = tc.start_work(args.account, args.project)
        print(f"✓ 作業開始: {session['account']} - {session['project']}")
        print(f"  開始時刻: {format_datetime(session['start_time'])}")
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_break(args):
    """休憩開始"""
    tc = TimeClock()
    try:
        session = tc.start_break()
        print(f"✓ 休憩開始: {session['account']} - {session['project']}")
        print(f"  休憩回数: {len(session['breaks'])}回目")
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_resume(args):
    """休憩終了・作業再開"""
    tc = TimeClock()
    try:
        session = tc.end_break()
        print(f"✓ 作業再開: {session['account']} - {session['project']}")
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_end(args):
    """作業終了"""
    tc = TimeClock()
    try:
        session = tc.end_work()
        print(f"✓ 作業終了: {session['account']} - {session['project']}")
        print(f"  開始時刻: {format_datetime(session['start_time'])}")
        print(f"  終了時刻: {format_datetime(session['end_time'])}")
        print(f"  休憩回数: {len(session['breaks'])}回")
        print(f"  作業時間: {format_time(session['total_minutes'])}")
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_status(args):
    """現在の状態を表示"""
    tc = TimeClock()
    session = tc.get_current_status()

    if not session:
        print("作業セッションなし")
        return

    print(f"現在の作業: {session['account']} - {session['project']}")
    print(f"開始時刻: {format_datetime(session['start_time'])}")
    print(f"状態: {'休憩中' if session['status'] == 'on_break' else '作業中'}")
    print(f"休憩回数: {len(session['breaks'])}回")
    print(f"現在までの作業時間: {format_time(session['current_work_minutes'])}")

    if session['breaks']:
        print("\n休憩履歴:")
        for i, brk in enumerate(session['breaks'], 1):
            start = format_datetime(brk['start'])
            end = format_datetime(brk['end']) if brk['end'] else '(休憩中)'
            print(f"  {i}. {start} - {end}")

def cmd_report_daily(args):
    """日別レポート"""
    tc = TimeClock()
    summary = tc.get_daily_summary(args.account, args.date)

    print(f"\n【日別レポート】")
    print(f"アカウント: {summary['account']}")
    print(f"日付: {summary['date']}")
    print(f"合計作業時間: {format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")

    if summary['projects']:
        print("\nプロジェクト別内訳:")
        for project, minutes in sorted(summary['projects'].items()):
            print(f"  - {project}: {format_time(minutes)}")

    # 標準労働時間との比較
    standard_hours = args.standard_hours or 8
    standard_minutes = standard_hours * 60
    overtime_minutes = summary['total_minutes'] - standard_minutes

    print(f"\n標準労働時間: {standard_hours}時間 ({standard_minutes}分)")
    if overtime_minutes > 0:
        print(f"残業時間: {format_time(overtime_minutes)} ⚠️")
    elif overtime_minutes < 0:
        print(f"不足時間: {format_time(abs(overtime_minutes))}")
    else:
        print("定時ぴったり ✓")

    if args.verbose and summary['records']:
        print("\n詳細:")
        for i, record in enumerate(summary['records'], 1):
            print(f"\n  セッション {i}:")
            print(f"    プロジェクト: {record['project']}")
            print(f"    開始: {format_datetime(record['start_time'])}")
            print(f"    終了: {format_datetime(record['end_time'])}")
            print(f"    休憩: {len(record['breaks'])}回")
            print(f"    作業時間: {format_time(record['total_minutes'])}")

def cmd_report_project(args):
    """プロジェクト別レポート"""
    tc = TimeClock()
    summary = tc.get_project_summary(args.account, args.project,
                                     args.start_date, args.end_date)

    print(f"\n【プロジェクト別レポート】")
    print(f"アカウント: {summary['account']}")
    print(f"プロジェクト: {summary['project']}")
    print(f"レコード数: {summary['record_count']}セッション")
    print(f"合計作業時間: {format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")

    if summary['days']:
        print("\n日別内訳:")
        for date, minutes in sorted(summary['days'].items()):
            print(f"  {date}: {format_time(minutes)}")

def cmd_list_accounts(args):
    """アカウント一覧"""
    tc = TimeClock()
    accounts = tc.list_accounts()

    if not accounts:
        print("登録されているアカウントはありません")
        return

    print("登録アカウント:")
    for account in accounts:
        projects = tc.list_projects(account)
        print(f"  - {account} ({len(projects)}プロジェクト)")

def cmd_list_projects(args):
    """プロジェクト一覧"""
    tc = TimeClock()
    projects = tc.list_projects(args.account)

    if not projects:
        print(f"{args.account}: プロジェクトなし")
        return

    print(f"{args.account} のプロジェクト:")
    for project in projects:
        print(f"  - {project}")

def cmd_report_monthly(args):
    """月次レポート（プロジェクト別残業時間含む）"""
    tc = TimeClock()

    # 年月の指定がない場合は今月
    if args.year_month:
        try:
            year, month = map(int, args.year_month.split('-'))
        except ValueError:
            print("エラー: 年月は YYYY-MM 形式で指定してください", file=sys.stderr)
            sys.exit(1)
    else:
        now = datetime.now()
        year = now.year
        month = now.month

    summary = tc.get_monthly_summary(args.account, year, month)

    # 締め日の表示
    closing_day_text = "月末締め" if summary['closing_day'] == 31 else "15日締め"

    print(f"\n{'='*60}")
    print(f"【月次レポート - {summary['year']}年{summary['month']}月】({closing_day_text})")
    print(f"{'='*60}")
    print(f"アカウント: {summary['account']}")
    print(f"集計期間: {summary['start_date']} ～ {summary['end_date']}")
    print(f"稼働日数: {summary['working_days']}日")
    print(f"\n総作業時間: {format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")
    print(f"標準労働時間: {format_time(summary['standard_total_minutes'])} ({summary['standard_total_hours']:.2f}時間)")

    if summary['total_overtime_minutes'] > 0:
        print(f"総残業時間: {format_time(summary['total_overtime_minutes'])} ({summary['total_overtime_hours']:.2f}時間) ⚠️")
    else:
        print(f"総残業時間: なし ✓")

    # プロジェクト別統計
    if summary['project_stats']:
        print(f"\n{'='*60}")
        print("【プロジェクト別内訳】")
        print(f"{'='*60}")

        for project, stats in sorted(summary['project_stats'].items()):
            print(f"\n■ {project}")
            print(f"  稼働日数: {stats['days_worked_count']}日")
            print(f"  作業時間: {format_time(stats['total_minutes'])} ({stats['total_hours']:.2f}時間)")
            print(f"  残業時間: {format_time(stats['overtime_minutes'])} ({stats['overtime_hours']:.2f}時間)", end='')

            if stats['overtime_minutes'] > 0:
                print(" ⚠️")
            else:
                print(" ✓")

            if args.verbose:
                print(f"\n  日別内訳:")
                for date, minutes in sorted(stats['daily_breakdown'].items()):
                    overtime = stats['overtime_by_day'].get(date, 0)
                    print(f"    {date}: {format_time(minutes)} (残業: {format_time(overtime)})")

    # 日別サマリー（詳細モード）
    if args.verbose and summary['daily_stats']:
        print(f"\n{'='*60}")
        print("【日別詳細】")
        print(f"{'='*60}")

        standard_minutes = summary['standard_hours_per_day'] * 60

        for date, day_data in sorted(summary['daily_stats'].items()):
            total = day_data['total_minutes']
            overtime = max(0, total - standard_minutes)

            print(f"\n{date}")
            print(f"  合計: {format_time(total)}", end='')
            if overtime > 0:
                print(f" (残業: {format_time(overtime)}) ⚠️")
            else:
                print()

            print(f"  プロジェクト:")
            for proj, mins in sorted(day_data['projects'].items()):
                print(f"    - {proj}: {format_time(mins)}")

    print(f"\n{'='*60}\n")

    # HTML出力オプション
    if args.output:
        output_path = Path(args.output)
        save_html_report(summary, str(output_path))
        print(f"✓ HTMLレポートを出力しました: {output_path}")
        print(f"  ブラウザで開く、または印刷してご利用ください")

def cmd_config(args):
    """アカウント設定"""
    tc = TimeClock()

    if args.config_action == 'show':
        # 設定表示
        config = tc.get_account_config(args.account)
        closing_day_text = "月末締め" if config['closing_day'] == 31 else "15日締め"

        print(f"\n{args.account} の設定:")
        print(f"  締め日: {config['closing_day']}日 ({closing_day_text})")
        print(f"  標準労働時間: {config['standard_hours_per_day']}時間/日")

    elif args.config_action == 'set':
        # 設定変更
        try:
            tc.set_account_config(args.account, args.closing_day,
                                 args.standard_hours)
            closing_day_text = "月末締め" if args.closing_day == 31 else "15日締め"

            print(f"✓ {args.account} の設定を更新しました:")
            print(f"  締め日: {args.closing_day}日 ({closing_day_text})")
            print(f"  標準労働時間: {args.standard_hours}時間/日")
        except ValueError as e:
            print(f"エラー: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='打刻システム - プロジェクト別作業時間管理',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='コマンド')

    # start コマンド
    parser_start = subparsers.add_parser('start', help='作業開始')
    parser_start.add_argument('account', help='アカウント名')
    parser_start.add_argument('project', help='プロジェクト名')
    parser_start.set_defaults(func=cmd_start)

    # break コマンド
    parser_break = subparsers.add_parser('break', help='休憩開始')
    parser_break.set_defaults(func=cmd_break)

    # resume コマンド
    parser_resume = subparsers.add_parser('resume', help='休憩終了・作業再開')
    parser_resume.set_defaults(func=cmd_resume)

    # end コマンド
    parser_end = subparsers.add_parser('end', help='作業終了')
    parser_end.set_defaults(func=cmd_end)

    # status コマンド
    parser_status = subparsers.add_parser('status', help='現在の状態を表示')
    parser_status.set_defaults(func=cmd_status)

    # report コマンド
    parser_report = subparsers.add_parser('report', help='レポート表示')
    report_subparsers = parser_report.add_subparsers(dest='report_type')

    # report daily
    parser_daily = report_subparsers.add_parser('daily', help='日別レポート')
    parser_daily.add_argument('account', help='アカウント名')
    parser_daily.add_argument('--date', help='日付 (YYYY-MM-DD、省略時は今日)')
    parser_daily.add_argument('--standard-hours', type=int, default=8,
                             help='標準労働時間 (デフォルト: 8)')
    parser_daily.add_argument('-v', '--verbose', action='store_true',
                             help='詳細表示')
    parser_daily.set_defaults(func=cmd_report_daily)

    # report project
    parser_project = report_subparsers.add_parser('project', help='プロジェクト別レポート')
    parser_project.add_argument('account', help='アカウント名')
    parser_project.add_argument('project', help='プロジェクト名')
    parser_project.add_argument('--start-date', help='開始日 (YYYY-MM-DD)')
    parser_project.add_argument('--end-date', help='終了日 (YYYY-MM-DD)')
    parser_project.set_defaults(func=cmd_report_project)

    # report monthly
    parser_monthly = report_subparsers.add_parser('monthly', help='月次レポート（プロジェクト別残業時間含む）')
    parser_monthly.add_argument('account', help='アカウント名')
    parser_monthly.add_argument('year_month', nargs='?', help='年月 (YYYY-MM、省略時は今月)')
    parser_monthly.add_argument('-v', '--verbose', action='store_true',
                               help='詳細表示（日別・プロジェクト別内訳）')
    parser_monthly.add_argument('-o', '--output', help='HTMLファイルに出力（ファイルパス指定）')
    parser_monthly.set_defaults(func=cmd_report_monthly)

    # list コマンド
    parser_list = subparsers.add_parser('list', help='一覧表示')
    list_subparsers = parser_list.add_subparsers(dest='list_type')

    # list accounts
    parser_list_accounts = list_subparsers.add_parser('accounts', help='アカウント一覧')
    parser_list_accounts.set_defaults(func=cmd_list_accounts)

    # list projects
    parser_list_projects = list_subparsers.add_parser('projects', help='プロジェクト一覧')
    parser_list_projects.add_argument('account', help='アカウント名')
    parser_list_projects.set_defaults(func=cmd_list_projects)

    # config コマンド
    parser_config = subparsers.add_parser('config', help='アカウント設定')
    config_subparsers = parser_config.add_subparsers(dest='config_action')

    # config show
    parser_config_show = config_subparsers.add_parser('show', help='設定を表示')
    parser_config_show.add_argument('account', help='アカウント名')
    parser_config_show.set_defaults(func=cmd_config)

    # config set
    parser_config_set = config_subparsers.add_parser('set', help='設定を変更')
    parser_config_set.add_argument('account', help='アカウント名')
    parser_config_set.add_argument('--closing-day', type=int, required=True,
                                   choices=[15, 31],
                                   help='締め日 (15 or 31)')
    parser_config_set.add_argument('--standard-hours', type=int, default=8,
                                   help='標準労働時間/日 (デフォルト: 8)')
    parser_config_set.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
