"""
打刻システムのコアロジック
作業開始、休憩、作業終了を管理
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from storage import Storage

class TimeClock:
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()

    def start_work(self, account: str, project: str) -> Dict:
        """
        作業開始

        Args:
            account: アカウント名
            project: プロジェクト名

        Returns:
            開始したセッション情報
        """
        current = self.storage.get_current_session()
        if current and not current.get('end_time'):
            raise ValueError(
                f"既に作業中です: {current['account']} - {current['project']}\n"
                f"先に作業を終了してください (timeclock end)"
            )

        now = datetime.now()
        session = {
            'account': account,
            'project': project,
            'date': now.strftime('%Y-%m-%d'),
            'start_time': now.isoformat(),
            'breaks': [],
            'end_time': None,
            'status': 'working'
        }

        self.storage.set_current_session(session)
        return session

    def start_break(self) -> Dict:
        """
        休憩開始

        Returns:
            更新されたセッション情報
        """
        session = self.storage.get_current_session()
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

        self.storage.set_current_session(session)
        return session

    def end_break(self) -> Dict:
        """
        休憩終了

        Returns:
            更新されたセッション情報
        """
        session = self.storage.get_current_session()
        if not session:
            raise ValueError("作業セッションが開始されていません")

        if session['status'] != 'on_break':
            raise ValueError("休憩中ではありません")

        now = datetime.now()
        # 最後の休憩の終了時刻を設定
        session['breaks'][-1]['end'] = now.isoformat()
        session['status'] = 'working'

        self.storage.set_current_session(session)
        return session

    def end_work(self) -> Dict:
        """
        作業終了

        Returns:
            完了したセッション情報
        """
        session = self.storage.get_current_session()
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

        # レコードとして保存
        self.storage.add_record(session['account'], session)

        # 現在のセッションをクリア
        self.storage.set_current_session(None)

        return session

    def get_current_status(self) -> Optional[Dict]:
        """現在の作業状況を取得"""
        session = self.storage.get_current_session()
        if not session:
            return None

        # 現在までの作業時間を計算
        work_duration = self._calculate_work_duration(session, up_to_now=True)
        session['current_work_minutes'] = work_duration

        return session

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
