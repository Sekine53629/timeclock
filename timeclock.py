"""
打刻システムのコアロジック
作業開始、休憩、作業終了を管理
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from storage import Storage
from config_manager import ConfigManager

class TimeClock:
    def __init__(self, storage: Optional[Storage] = None, config_manager: Optional[ConfigManager] = None):
        """
        Args:
            storage: Storageインスタンス（指定なしの場合は設定ファイルから自動取得）
            config_manager: ConfigManagerインスタンス
        """
        self.config_manager = config_manager or ConfigManager()

        if storage is None:
            # 設定ファイルからDB保存先を取得
            db_path = self.config_manager.get_db_path()
            storage = Storage(data_dir=db_path)

        self.storage = storage

    def start_work(self, account: str, project: str, comment: str = "") -> Dict:
        """
        作業開始

        Args:
            account: アカウント名
            project: プロジェクト名
            comment: 作業内容コメント（20字以内）

        Returns:
            開始したセッション情報
        """
        # 指定アカウントのセッションのみチェック
        current = self.storage.get_current_session(account)
        if current and not current.get('end_time'):
            raise ValueError(
                f"既に作業中です: {current['account']} - {current['project']}\n"
                f"先に作業を終了してください (timeclock end)"
            )

        # コメントは20字以内に制限
        if len(comment) > 20:
            comment = comment[:20]

        now = datetime.now()
        session = {
            'account': account,
            'project': project,
            'date': now.strftime('%Y-%m-%d'),
            'start_time': now.isoformat(),
            'breaks': [],
            'end_time': None,
            'status': 'working',
            'comment': comment
        }

        self.storage.set_current_session(session, account)
        return session

    def start_break(self, account: Optional[str] = None) -> Dict:
        """
        休憩開始

        Args:
            account: アカウント名（指定しない場合は互換性のため最初のセッション）

        Returns:
            更新されたセッション情報
        """
        session = self.storage.get_current_session(account)
        if not session:
            raise ValueError("作業セッションが開始されていません")

        if session['status'] == 'on_break':
            raise ValueError("既に休憩中です")

        now = datetime.now()
        session['breaks'].append({
            'start': now.isoformat(),
            'end': None
        })
        session['status'] = 'on_break'

        self.storage.set_current_session(session, session['account'])
        return session

    def end_break(self, account: Optional[str] = None) -> Dict:
        """
        休憩終了

        Args:
            account: アカウント名（指定しない場合は互換性のため最初のセッション）

        Returns:
            更新されたセッション情報
        """
        session = self.storage.get_current_session(account)
        if not session:
            raise ValueError("作業セッションが開始されていません")

        if session['status'] != 'on_break':
            raise ValueError("休憩中ではありません")

        now = datetime.now()
        # 最後の休憩の終了時刻を設定
        session['breaks'][-1]['end'] = now.isoformat()
        session['status'] = 'working'

        self.storage.set_current_session(session, session['account'])
        return session

    def end_work(self, account: Optional[str] = None, is_holiday: bool = False,
                 is_legal_holiday: bool = False) -> Dict:
        """
        作業終了

        Args:
            account: アカウント名（指定しない場合は互換性のため最初のセッション）
            is_holiday: 休日かどうか
            is_legal_holiday: 法定休日かどうか

        Returns:
            完了したセッション情報
        """
        session = self.storage.get_current_session(account)
        if not session:
            raise ValueError("作業セッションが開始されていません")

        if session['status'] == 'on_break':
            raise ValueError("休憩中です。先に休憩を終了してください (timeclock resume)")

        now = datetime.now()
        session['end_time'] = now.isoformat()
        session['status'] = 'completed'

        # 作業時間を計算
        work_duration = self._calculate_work_duration(session)
        session['total_minutes'] = work_duration

        # 深夜労働時間を計算
        night_work_minutes = self._calculate_night_work_minutes(session)
        session['night_work_minutes'] = night_work_minutes

        # 休日情報を記録
        session['is_holiday'] = is_holiday
        session['is_legal_holiday'] = is_legal_holiday

        # レコードとして保存
        self.storage.add_record(session['account'], session)

        # 現在のセッションをクリア（そのアカウントのみ）
        self.storage.set_current_session(None, session['account'])

        return session

    def get_current_status(self, account: Optional[str] = None) -> Optional[Dict]:
        """
        現在の作業状況を取得

        Args:
            account: アカウント名（指定しない場合は互換性のため最初のセッション）

        Returns:
            セッション情報
        """
        session = self.storage.get_current_session(account)
        if not session:
            return None

        # 現在までの作業時間を計算
        work_duration = self._calculate_work_duration(session, up_to_now=True)
        session['current_work_minutes'] = work_duration

        return session

    def get_all_current_statuses(self) -> Dict[str, Dict]:
        """全アカウントの現在の作業状況を取得"""
        all_sessions = self.storage.get_all_current_sessions()
        result = {}

        for account, session in all_sessions.items():
            # 現在までの作業時間を計算
            work_duration = self._calculate_work_duration(session, up_to_now=True)
            session['current_work_minutes'] = work_duration
            result[account] = session

        return result

    def _calculate_work_duration(self, session: Dict, up_to_now: bool = False) -> int:
        """
        作業時間を計算（分単位）

        Args:
            session: セッション情報
            up_to_now: Trueの場合は現在時刻まで計算

        Returns:
            作業時間（分）
        """
        start = datetime.fromisoformat(session['start_time'])

        if up_to_now or not session.get('end_time'):
            end = datetime.now()
        else:
            end = datetime.fromisoformat(session['end_time'])

        # 総時間
        total_duration = (end - start).total_seconds() / 60

        # 休憩時間を差し引く
        break_duration = 0
        for brk in session.get('breaks', []):
            break_start = datetime.fromisoformat(brk['start'])
            if brk['end']:
                break_end = datetime.fromisoformat(brk['end'])
            elif up_to_now:
                break_end = datetime.now()
            else:
                continue

            break_duration += (break_end - break_start).total_seconds() / 60

        work_duration = total_duration - break_duration
        return int(work_duration)

    def get_daily_summary(self, account: str, date: Optional[str] = None) -> Dict:
        """
        日別のサマリーを取得

        Args:
            account: アカウント名
            date: 日付（YYYY-MM-DD形式、Noneの場合は今日）

        Returns:
            サマリー情報
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        records = self.storage.get_records(account, date=date)

        total_minutes = sum(r.get('total_minutes', 0) for r in records)
        project_breakdown = {}

        for record in records:
            project = record.get('project', 'unknown')
            minutes = record.get('total_minutes', 0)
            if project not in project_breakdown:
                project_breakdown[project] = 0
            project_breakdown[project] += minutes

        return {
            'account': account,
            'date': date,
            'total_minutes': total_minutes,
            'total_hours': total_minutes / 60,
            'projects': project_breakdown,
            'records': records
        }

    def get_project_summary(self, account: str, project: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict:
        """
        プロジェクト別のサマリーを取得

        Args:
            account: アカウント名
            project: プロジェクト名
            start_date: 開始日（YYYY-MM-DD形式）
            end_date: 終了日（YYYY-MM-DD形式）

        Returns:
            サマリー情報
        """
        records = self.storage.get_records(account, project=project)

        # 日付フィルタ
        if start_date:
            records = [r for r in records if r.get('date', '') >= start_date]
        if end_date:
            records = [r for r in records if r.get('date', '') <= end_date]

        total_minutes = sum(r.get('total_minutes', 0) for r in records)
        daily_breakdown = {}

        for record in records:
            date = record.get('date', 'unknown')
            minutes = record.get('total_minutes', 0)
            if date not in daily_breakdown:
                daily_breakdown[date] = 0
            daily_breakdown[date] += minutes

        return {
            'account': account,
            'project': project,
            'total_minutes': total_minutes,
            'total_hours': total_minutes / 60,
            'days': daily_breakdown,
            'record_count': len(records)
        }

    def list_accounts(self) -> List[str]:
        """全アカウントのリストを取得"""
        return self.storage.list_accounts()

    def list_projects(self, account: str) -> List[str]:
        """指定アカウントの全プロジェクトのリストを取得"""
        return self.storage.list_projects(account)

    def get_monthly_summary(self, account: str, year: int, month: int,
                           standard_hours_per_day: Optional[int] = None) -> Dict:
        """
        月次サマリーを取得（プロジェクト別の残業時間含む）
        締め日設定に基づいて集計期間を計算

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月）
            standard_hours_per_day: 1日の標準労働時間（未指定時は設定値を使用）

        Returns:
            月次サマリー情報
        """
        # アカウント設定を取得
        account_config = self.storage.get_account_config(account)
        closing_day = account_config['closing_day']

        if standard_hours_per_day is None:
            standard_hours_per_day = account_config['standard_hours_per_day']

        # 締め日に基づいて集計期間を計算
        if closing_day == 31:
            # 月末締め: 1日～月末
            start_date = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end_year = year + 1
                end_month = 1
            else:
                end_year = year
                end_month = month + 1
            end_date_obj = datetime(end_year, end_month, 1) - timedelta(days=1)
            end_date = end_date_obj.strftime('%Y-%m-%d')
        else:
            # 15日締め: 前月16日～当月15日
            # YYYY年MM月期 = YYYY年MM-1月16日 ～ YYYY年MM月15日
            end_date = f"{year:04d}-{month:02d}-15"

            # 開始日を前月16日に設定
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1
            start_date = f"{prev_year:04d}-{prev_month:02d}-16"

        # 月内の全レコードを取得
        all_records = self.storage.get_records(account)
        records = [r for r in all_records
                  if start_date <= r.get('date', '') <= end_date]

        # プロジェクト別・日別の集計
        project_stats = {}
        daily_stats = {}

        for record in records:
            project = record.get('project', 'unknown')
            date = record.get('date', 'unknown')
            minutes = record.get('total_minutes', 0)

            # プロジェクト別統計
            if project not in project_stats:
                project_stats[project] = {
                    'total_minutes': 0,
                    'days_worked': set(),
                    'daily_breakdown': {}
                }

            project_stats[project]['total_minutes'] += minutes
            project_stats[project]['days_worked'].add(date)

            if date not in project_stats[project]['daily_breakdown']:
                project_stats[project]['daily_breakdown'][date] = 0
            project_stats[project]['daily_breakdown'][date] += minutes

            # 日別統計
            if date not in daily_stats:
                daily_stats[date] = {
                    'total_minutes': 0,
                    'projects': {}
                }
            daily_stats[date]['total_minutes'] += minutes
            if project not in daily_stats[date]['projects']:
                daily_stats[date]['projects'][project] = 0
            daily_stats[date]['projects'][project] += minutes

        # プロジェクト別の残業時間を計算
        standard_minutes_per_day = standard_hours_per_day * 60

        for project, stats in project_stats.items():
            stats['days_worked_count'] = len(stats['days_worked'])
            stats['total_hours'] = stats['total_minutes'] / 60

            # 各プロジェクトの日別残業時間を計算
            stats['overtime_minutes'] = 0
            stats['overtime_by_day'] = {}

            for date, minutes in stats['daily_breakdown'].items():
                # その日の総作業時間を取得
                day_total = daily_stats[date]['total_minutes']
                # その日の残業時間
                day_overtime = max(0, day_total - standard_minutes_per_day)

                # プロジェクトごとの割合で残業時間を按分
                if day_total > 0:
                    project_ratio = minutes / day_total
                    project_overtime = int(day_overtime * project_ratio)
                else:
                    project_overtime = 0

                stats['overtime_by_day'][date] = project_overtime
                stats['overtime_minutes'] += project_overtime

            stats['overtime_hours'] = stats['overtime_minutes'] / 60

        # 月全体の統計
        total_minutes = sum(r.get('total_minutes', 0) for r in records)
        working_days = len(daily_stats)
        standard_total_minutes = working_days * standard_minutes_per_day

        # 総残業時間は日ごとの残業時間の合計
        # 日曜日の作業は別集計
        total_overtime_minutes = 0
        sunday_work_minutes = 0
        sunday_days = []

        for date, day_data in daily_stats.items():
            # 日付から曜日を判定（0=月曜, 6=日曜）
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            is_sunday = (date_obj.weekday() == 6)

            if is_sunday:
                # 日曜日の作業は全て別集計
                sunday_work_minutes += day_data['total_minutes']
                sunday_days.append(date)
            else:
                # 平日・土曜の残業時間を集計
                day_overtime = max(0, day_data['total_minutes'] - standard_minutes_per_day)
                total_overtime_minutes += day_overtime

        return {
            'account': account,
            'year': year,
            'month': month,
            'closing_day': closing_day,
            'start_date': start_date,
            'end_date': end_date,
            'working_days': working_days,
            'total_minutes': total_minutes,
            'total_hours': total_minutes / 60,
            'standard_hours_per_day': standard_hours_per_day,
            'standard_total_minutes': standard_total_minutes,
            'standard_total_hours': standard_total_minutes / 60,
            'total_overtime_minutes': total_overtime_minutes,
            'total_overtime_hours': total_overtime_minutes / 60,
            'sunday_work_minutes': sunday_work_minutes,
            'sunday_work_hours': sunday_work_minutes / 60,
            'sunday_days_count': len(sunday_days),
            'sunday_days': sunday_days,
            'project_stats': project_stats,
            'daily_stats': daily_stats,
            'record_count': len(records)
        }

    def set_account_config(self, account: str, closing_day: int,
                          standard_hours_per_day: int = 8):
        """
        アカウントの設定を保存

        Args:
            account: アカウント名
            closing_day: 締め日（15 or 31）
            standard_hours_per_day: 1日の標準労働時間
        """
        self.storage.set_account_config(account, closing_day, standard_hours_per_day)

    def get_account_config(self, account: str) -> Dict:
        """アカウントの設定を取得"""
        return self.storage.get_account_config(account)

    def update_record(self, account: str, record_index: int, updated_record: Dict,
                     reason: str = "", editor: Optional[str] = None) -> bool:
        """
        レコードを更新

        Args:
            account: アカウント名
            record_index: レコードのインデックス
            updated_record: 更新後のレコード
            reason: 変更理由
            editor: 編集者

        Returns:
            成功した場合True
        """
        # コメントは20字以内に制限
        if 'comment' in updated_record and len(updated_record['comment']) > 20:
            updated_record['comment'] = updated_record['comment'][:20]

        return self.storage.update_record(account, record_index, updated_record, reason, editor)

    def delete_record(self, account: str, record_index: int,
                     reason: str = "", editor: Optional[str] = None) -> bool:
        """
        レコードを削除

        Args:
            account: アカウント名
            record_index: レコードのインデックス
            reason: 削除理由
            editor: 編集者

        Returns:
            成功した場合True
        """
        return self.storage.delete_record(account, record_index, reason, editor)

    def submit_records(self, account: str, start_date: str, end_date: str,
                      reason: str = "", editor: Optional[str] = None) -> int:
        """
        指定期間のレコードを申請

        Args:
            account: アカウント名
            start_date: 開始日（YYYY-MM-DD形式）
            end_date: 終了日（YYYY-MM-DD形式）
            reason: 申請理由
            editor: 申請者

        Returns:
            申請したレコード数
        """
        return self.storage.submit_records(account, start_date, end_date, reason, editor)

    def get_edit_logs(self, account: Optional[str] = None,
                     record_id: Optional[str] = None,
                     limit: int = 50) -> List[Dict]:
        """
        編集ログを取得

        Args:
            account: アカウント名
            record_id: レコードID
            limit: 取得件数

        Returns:
            編集ログのリスト
        """
        return self.storage.get_edit_logs(account, record_id, limit)

    def _calculate_night_work_minutes(self, session: Dict) -> int:
        """
        深夜労働時間を計算（22:00～5:00の時間帯）

        Args:
            session: セッション情報

        Returns:
            深夜労働時間（分）
        """
        start = datetime.fromisoformat(session['start_time'])
        end = datetime.fromisoformat(session['end_time'])

        total_night_minutes = 0

        # 開始から終了までの各時刻をチェック
        current = start
        while current < end:
            # 次の分まで進む
            next_time = current + timedelta(minutes=1)
            if next_time > end:
                next_time = end

            # 現在の時刻が深夜時間帯（22:00～5:00）かチェック
            hour = current.hour
            if hour >= 22 or hour < 5:
                # 休憩時間を除外
                is_break = False
                for brk in session.get('breaks', []):
                    break_start = datetime.fromisoformat(brk['start'])
                    if brk['end']:
                        break_end = datetime.fromisoformat(brk['end'])
                        if break_start <= current < break_end:
                            is_break = True
                            break

                if not is_break:
                    total_night_minutes += 1

            current = next_time

        return total_night_minutes

    def get_monthly_overtime_hours(self, account: str, target_date: Optional[str] = None) -> Dict:
        """
        月間の時間外労働時間を取得（16日～翌月15日の期間）
        会社での打刻実績と合算して60時間判定

        Args:
            account: アカウント名
            target_date: 対象日付（YYYY-MM-DD形式、Noneの場合は今日）

        Returns:
            {
                'period_start': 期間開始日,
                'period_end': 期間終了日,
                'year': 年,
                'month': 月（締め日基準）,
                'total_overtime_minutes': 総時間外労働時間（分）,
                'total_overtime_hours': 総時間外労働時間（時間）,
                'legal_holiday_work_minutes': 法定休日労働時間（分）,
                'legal_holiday_work_hours': 法定休日労働時間（時間）,
                'total_for_60h_calc_minutes': 60時間計算用の合計（分）,
                'total_for_60h_calc_hours': 60時間計算用の合計（時間）,
                'company_overtime_hours': 会社打刻実績（時間）,
                'combined_overtime_hours': アプリ+会社の合算（時間）,
                'over_60_hours': 60時間超過分,
                'records': レコード一覧
            }
        """
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')

        target_dt = datetime.strptime(target_date, '%Y-%m-%d')

        # 16日～翌月15日の期間を計算
        # 締め日基準の年月も計算
        # YYYY年MM月期 = YYYY年MM-1月16日 ～ YYYY年MM月15日
        if target_dt.day >= 16:
            # 16日以降なら、当月16日～翌月15日
            # これは「翌月期」になる
            if target_dt.month == 12:
                period_year = target_dt.year + 1
                period_month = 1
            else:
                period_year = target_dt.year
                period_month = target_dt.month + 1
            start_date = target_dt.replace(day=16).strftime('%Y-%m-%d')
            end_date = datetime(period_year, period_month, 15).strftime('%Y-%m-%d')
        else:
            # 15日以前なら、前月16日～当月15日
            # これは「当月期」になる
            period_year = target_dt.year
            period_month = target_dt.month
            end_date = target_dt.replace(day=15).strftime('%Y-%m-%d')
            if target_dt.month == 1:
                start_date = datetime(target_dt.year - 1, 12, 16).strftime('%Y-%m-%d')
            else:
                start_date = datetime(target_dt.year, target_dt.month - 1, 16).strftime('%Y-%m-%d')

        # 期間内の全レコードを取得
        all_records = self.storage.get_records(account)
        records = [r for r in all_records
                  if start_date <= r.get('date', '') <= end_date]

        print(f"[DEBUG timeclock] get_monthly_overtime_hours: account={account}, period={start_date}～{end_date}")
        print(f"[DEBUG timeclock] レコード数: {len(records)}")

        # アカウント設定から標準労働時間を取得
        account_config = self.storage.get_account_config(account)
        standard_hours_per_day = account_config.get('standard_hours_per_day', 8)
        standard_minutes_per_day = standard_hours_per_day * 60

        # 日別に集計
        daily_totals = {}
        for record in records:
            date = record.get('date', 'unknown')
            minutes = record.get('total_minutes', 0)
            is_legal_holiday = record.get('is_legal_holiday', False)
            print(f"[DEBUG timeclock]   {date}: {minutes}分, is_legal_holiday={is_legal_holiday}")

            if date not in daily_totals:
                daily_totals[date] = {
                    'total_minutes': 0,
                    'is_legal_holiday': is_legal_holiday
                }
            daily_totals[date]['total_minutes'] += minutes

        # 時間外労働を計算
        total_overtime_minutes = 0
        legal_holiday_work_minutes = 0  # 法定休日労働時間（日曜日）
        overtime_minutes_for_60h_calc = 0  # 60時間計算用の時間外労働

        print(f"[DEBUG timeclock] 日別詳細:")
        for date, day_data in daily_totals.items():
            day_total = day_data['total_minutes']
            is_legal_holiday = day_data['is_legal_holiday']

            # is_legal_holidayフラグがない古いデータの場合、曜日で判定
            if not is_legal_holiday and date != 'unknown':
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    is_sunday = (date_obj.weekday() == 6)
                    if is_sunday:
                        is_legal_holiday = True
                except ValueError:
                    pass

            if is_legal_holiday:
                # 法定休日（日曜日）の労働時間は全て別計上
                legal_holiday_work_minutes += day_total
                print(f"[DEBUG timeclock]   {date}: {day_total}分 [日曜日] → 法定休日労働")
            else:
                # 平日・土曜の時間外労働 = 総労働時間 - 標準労働時間
                overtime = max(0, day_total - standard_minutes_per_day)
                total_overtime_minutes += overtime
                overtime_minutes_for_60h_calc += overtime
                print(f"[DEBUG timeclock]   {date}: {day_total}分 (残業{overtime}分) [平日・土曜]")

        # 60時間計算用：法定時間外労働 + 法定休日労働（アプリで記録した分）
        total_for_60h_calc = overtime_minutes_for_60h_calc + legal_holiday_work_minutes

        print(f"[DEBUG timeclock] 集計結果:")
        print(f"[DEBUG timeclock]   法定時間外労働: {overtime_minutes_for_60h_calc}分 ({overtime_minutes_for_60h_calc/60:.1f}時間)")
        print(f"[DEBUG timeclock]   法定休日労働: {legal_holiday_work_minutes}分 ({legal_holiday_work_minutes/60:.1f}時間)")
        print(f"[DEBUG timeclock]   合計（アプリ記録）: {total_for_60h_calc}分 ({total_for_60h_calc/60:.1f}時間)")

        # 会社での打刻実績を取得（時間単位）
        company_overtime_hours = self.storage.get_company_overtime(account, period_year, period_month)

        # アプリの時間外労働と会社打刻実績を合算
        app_overtime_hours = total_for_60h_calc / 60
        combined_overtime_hours = app_overtime_hours + company_overtime_hours

        # 合算後の60時間超過分を計算
        over_60_hours = max(0, combined_overtime_hours - 60)

        return {
            'period_start': start_date,
            'period_end': end_date,
            'year': period_year,
            'month': period_month,
            'total_overtime_minutes': total_overtime_minutes,
            'total_overtime_hours': total_overtime_minutes / 60,
            'legal_holiday_work_minutes': legal_holiday_work_minutes,
            'legal_holiday_work_hours': legal_holiday_work_minutes / 60,
            'total_for_60h_calc_minutes': total_for_60h_calc,
            'total_for_60h_calc_hours': app_overtime_hours,
            'company_overtime_hours': company_overtime_hours,
            'combined_overtime_hours': combined_overtime_hours,
            'over_60_hours': over_60_hours,
            'records': records
        }

    def calculate_overtime_rate(self, is_night_work: bool, monthly_overtime_hours: float,
                                is_holiday: bool, is_legal_holiday: bool) -> float:
        """
        割増率を計算

        Args:
            is_night_work: 深夜労働かどうか（22:00～5:00）
            monthly_overtime_hours: 月間時間外労働時間（会社打刻実績との合算後）
            is_holiday: 休日かどうか
            is_legal_holiday: 法定休日かどうか

        Returns:
            割増率（0.25 = 25%, 0.5 = 50%, など）
        """
        rate = 0.0

        if is_legal_holiday:
            # 法定休日労働: 35%
            rate = 0.35
        elif is_holiday:
            # 法定外休日労働: 通常の時間外労働と同じ扱い
            if monthly_overtime_hours > 60:
                rate = 0.5  # 60時間超過: 50%
            else:
                rate = 0.25  # 通常の時間外: 25%
        else:
            # 平日の時間外労働
            if monthly_overtime_hours > 60:
                rate = 0.5  # 60時間超過: 50%
            else:
                rate = 0.25  # 通常の時間外: 25%

        # 深夜労働の場合は25%追加
        if is_night_work:
            rate += 0.25

        return rate

    def set_company_overtime(self, account: str, year: int, month: int, hours: float):
        """
        会社での打刻実績（時間外労働時間）を設定

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月）
            hours: 会社打刻実績の時間外労働時間
        """
        self.storage.set_company_overtime(account, year, month, hours)

    def get_company_overtime(self, account: str, year: int, month: int) -> float:
        """
        会社での打刻実績（時間外労働時間）を取得

        Args:
            account: アカウント名
            year: 年
            month: 月（締め日基準の月）

        Returns:
            会社打刻実績の時間外労働時間（時間単位）
        """
        return self.storage.get_company_overtime(account, year, month)

    def get_all_company_overtime(self, account: str) -> Dict[str, float]:
        """
        指定アカウントの全ての会社打刻実績を取得

        Args:
            account: アカウント名

        Returns:
            {"YYYY-MM": hours, ...} の辞書
        """
        return self.storage.get_all_company_overtime(account)
