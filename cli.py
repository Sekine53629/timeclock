#!/usr/bin/env python3
"""
打刻システム CLI インターフェース
"""
import argparse
import sys
from datetime import datetime
from timeclock import TimeClock
from storage import Storage

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
