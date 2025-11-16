#!/usr/bin/env python3
"""
PC操作監視モジュール
ユーザーのアイドル時間を監視し、指定時間以上未操作の場合にコールバックを実行
"""

import ctypes
import time
import platform
from datetime import datetime
from typing import Callable, Optional
import threading


class IdleMonitor:
    """PCのアイドル時間を監視するクラス"""

    def __init__(self, idle_threshold_minutes: int = 15,
                 check_interval_seconds: int = 30):
        """
        初期化

        Args:
            idle_threshold_minutes: アイドル判定の閾値（分）
            check_interval_seconds: チェック間隔（秒）
        """
        self.idle_threshold_minutes = idle_threshold_minutes
        self.check_interval_seconds = check_interval_seconds
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.on_idle_detected: Optional[Callable] = None
        self.last_idle_time: Optional[datetime] = None

        # プラットフォームチェック（Windows専用機能）
        self.is_windows = platform.system() == 'Windows'
        if not self.is_windows:
            print(f"[IdleMonitor] Warning: Idle monitoring is only supported on Windows. Current platform: {platform.system()}")

    def get_idle_time_seconds(self) -> float:
        """
        PCのアイドル時間を秒単位で取得

        Returns:
            アイドル時間（秒）
        """
        # Windows以外では常に0を返す（監視無効）
        if not self.is_windows:
            return 0

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', ctypes.c_uint),
                ('dwTime', ctypes.c_uint),
            ]

        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)

        # GetLastInputInfo APIを呼び出し
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
            millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
        else:
            return 0

    def get_idle_time_minutes(self) -> float:
        """
        PCのアイドル時間を分単位で取得

        Returns:
            アイドル時間（分）
        """
        return self.get_idle_time_seconds() / 60.0

    def start_monitoring(self, callback: Callable[[float], None]):
        """
        監視を開始

        Args:
            callback: アイドル検出時に呼び出される関数
                     引数: アイドル時間（分）
        """
        # Windows以外では監視を開始しない
        if not self.is_windows:
            print("[IdleMonitor] Idle monitoring is disabled on non-Windows platforms")
            return

        if self.is_monitoring:
            return

        self.on_idle_detected = callback
        self.is_monitoring = True
        self.last_idle_time = None

        # 監視スレッドを開始
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """監視を停止"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            self.monitor_thread = None

    def _monitor_loop(self):
        """監視ループ（別スレッドで実行）"""
        idle_detected = False

        while self.is_monitoring:
            try:
                idle_minutes = self.get_idle_time_minutes()

                # アイドル閾値を超えた場合
                if idle_minutes >= self.idle_threshold_minutes:
                    # まだアイドル検出を通知していない場合のみ通知
                    if not idle_detected:
                        idle_detected = True
                        self.last_idle_time = datetime.now()
                        if self.on_idle_detected:
                            self.on_idle_detected(idle_minutes)
                else:
                    # アイドルから復帰した場合、フラグをリセット
                    if idle_detected:
                        idle_detected = False

                time.sleep(self.check_interval_seconds)

            except Exception as e:
                print(f"[IdleMonitor] Error in monitor loop: {e}")
                time.sleep(self.check_interval_seconds)

    def set_idle_threshold(self, minutes: int):
        """
        アイドル閾値を設定

        Args:
            minutes: 閾値（分）
        """
        self.idle_threshold_minutes = minutes

    def get_status(self) -> dict:
        """
        現在の監視状態を取得

        Returns:
            状態情報の辞書
        """
        return {
            'is_monitoring': self.is_monitoring,
            'idle_threshold_minutes': self.idle_threshold_minutes,
            'current_idle_minutes': self.get_idle_time_minutes(),
            'last_idle_time': self.last_idle_time
        }


def test_idle_monitor():
    """テスト用の関数"""
    print("=== Idle Monitor Test ===")
    print("15秒間アイドル状態（マウス/キーボード操作なし）になると通知されます")
    print("Ctrl+Cで終了\n")

    def on_idle(idle_minutes):
        print(f"\n[IDLE DETECTED] {idle_minutes:.1f}分間アイドル状態です！")
        print(f"時刻: {datetime.now().strftime('%H:%M:%S')}")

    # テスト用: 閾値0.25分（15秒）、チェック間隔5秒
    monitor = IdleMonitor(idle_threshold_minutes=0.25, check_interval_seconds=5)
    monitor.start_monitoring(on_idle)

    try:
        while True:
            status = monitor.get_status()
            print(f"\r現在のアイドル時間: {status['current_idle_minutes']:.2f}分 "
                  f"(閾値: {status['idle_threshold_minutes']}分)", end='', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n監視を停止します...")
        monitor.stop_monitoring()
        print("終了しました")


if __name__ == '__main__':
    test_idle_monitor()
