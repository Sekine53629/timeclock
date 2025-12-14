#!/usr/bin/env python3
"""
打刻システム GUI アプリケーション
"""
import os
import platform
# macOS の Tk 非推奨警告を抑制
os.environ['TK_SILENCE_DEPRECATION'] = '1'
# macOS でダークモードの自動適用を無効化
if platform.system() == 'Darwin':
    try:
        from tkinter import _tkinter
        _tkinter.setappearance('aqua')
    except:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
from pathlib import Path
from timeclock import TimeClock
from config_manager import ConfigManager
from idle_monitor import IdleMonitor
from logger import get_logger, log_exception
from git_auto_sync import GitAutoSync
import sys
import threading

# ロガーの初期化
logger = get_logger(__name__)


class TimeClockGUI:
    def __init__(self, root):
        try:
            logger.info("GUI初期化開始")
            self.root = root
            self.root.title("打刻システム")
            self.root.geometry("900x650")  # コンパクトなサイズ
            logger.info("ウィンドウ設定完了")

            # 最小サイズを設定
            self.root.minsize(800, 600)
            logger.info("最小サイズ設定完了")

            # ライトモードの色設定（macOS互換性のため最小限の設定）
            logger.info("カラー設定開始")
            self.setup_colors_only()
            logger.info("カラー設定完了")

            logger.info("TimeClock初期化開始")
            self.tc = TimeClock()
            logger.info("TimeClock初期化完了")

            logger.info("ConfigManager初期化開始")
            self.config_manager = ConfigManager()
            logger.info("ConfigManager初期化完了")

            # 設定の読み込み
            logger.info("自動休憩設定読み込み開始")
            self.load_auto_break_config()
            logger.info("自動休憩設定読み込み完了")

            # アイドル監視機能の初期化
            logger.info("IdleMonitor初期化開始")
            self.idle_monitor = IdleMonitor(
                idle_threshold_minutes=self.auto_break_threshold,
                check_interval_seconds=30
            )
            logger.info("IdleMonitor初期化完了")

            # Git自動同期の初期化
            logger.info("GitAutoSync初期化開始")
            self.git_sync = GitAutoSync()
            logger.info("GitAutoSync初期化完了")

            # メインフレームの作成
            logger.info("ウィジェット作成開始")
            self.create_widgets()
            logger.info("ウィジェット作成完了")

            # 初期状態の更新
            logger.info("ステータス更新開始")
            self.update_status()
            logger.info("ステータス更新完了")

            # 定期的にステータスを更新（30秒ごと）
            self.schedule_status_update()

            # ウィンドウクローズ時のクリーンアップ
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            logger.info("GUI初期化完了")

        except Exception as e:
            log_exception(logger, "GUI初期化エラー", e)
            messagebox.showerror(
                "起動エラー",
                f"アプリケーションの初期化に失敗しました。\n\n"
                f"エラー: {str(e)}\n\n"
                f"ログファイル: {Path.home() / '.timeclock' / 'timeclock.log'}"
            )
            raise

    def setup_colors_only(self):
        """色定義のみ設定（macOS互換性のため、ttkスタイル設定を削除）"""
        # ライトモードの色定義
        self.colors = {
            'bg': '#f0f0f0',           # 背景色（明るいグレー）
            'fg': '#000000',           # 文字色（黒）
            'bg_light': '#ffffff',     # より明るい背景（白）
            'bg_dark': '#e0e0e0',      # 少し暗い背景
            'accent': '#007acc',       # アクセントカラー（青）
            'accent_hover': '#005a9e', # ホバー時のアクセント
            'success': '#00a000',      # 成功（緑）
            'warning': '#ff8c00',      # 警告（オレンジ）
            'error': '#d00000',        # エラー（赤）
            'border': '#c0c0c0',       # ボーダー色
        }

        # 最小限のスタイル設定
        self.root.configure(bg=self.colors['bg'])
        logger.info("色設定を適用しました（ttkスタイルは未適用）")


    def create_widgets(self):
        """ウィジェットの作成"""
        # ノートブック（タブ）の作成
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # タブの作成
        self.create_main_tab()
        self.create_report_tab()
        self.create_edit_tab()
        self.create_config_tab()

    def create_main_tab(self):
        """メインタブ（作業開始/終了）の作成"""
        # macOS互換性のため、通常のtkフレームを使用
        main_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(main_frame, text="打刻")

        # 現在の状態表示エリア
        status_group = tk.LabelFrame(main_frame, text="現在の状態",
                                     bg=self.colors['bg'], fg=self.colors['fg'],
                                     padx=10, pady=10)
        status_group.pack(fill=tk.X, padx=10, pady=10)

        self.status_text = scrolledtext.ScrolledText(
            status_group, height=8, width=70,
            bg=self.colors['bg_light'],
            fg=self.colors['fg']
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state=tk.DISABLED)

        # 作業開始エリア
        start_group = ttk.LabelFrame(main_frame, text="作業開始", padding=10)
        start_group.pack(fill=tk.X, padx=10, pady=10)

        # アカウント選択
        ttk.Label(start_group, text="アカウント:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(start_group, textvariable=self.account_var, width=30)
        self.account_combo.grid(row=0, column=1, padx=5, pady=5)
        self.account_combo.bind('<<ComboboxSelected>>', self.on_account_selected)

        # プロジェクト選択（自由入力可能）
        ttk.Label(start_group, text="プロジェクト:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(start_group, textvariable=self.project_var, width=30)
        self.project_combo.grid(row=1, column=1, padx=5, pady=5)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)

        # プロジェクトリフレッシュボタン（GitHubリポジトリ名を検出）
        ttk.Button(start_group, text="Git検出", command=self.detect_git_project).grid(row=1, column=2, padx=5)

        # 作業内容コメント入力
        ttk.Label(start_group, text="作業内容:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.comment_var = tk.StringVar()
        comment_entry = ttk.Entry(start_group, textvariable=self.comment_var, width=32)
        comment_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(start_group, text="(20字以内)").grid(row=2, column=2, sticky=tk.W, padx=5)

        # リフレッシュボタン
        ttk.Button(start_group, text="更新", command=self.refresh_accounts).grid(row=0, column=2, padx=5)

        # アカウント一覧を更新
        self.refresh_accounts()

        # ボタンエリア
        button_frame = ttk.Frame(main_frame, padding=10)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_button = ttk.Button(button_frame, text="作業開始", command=self.start_work)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.break_button = ttk.Button(button_frame, text="休憩開始", command=self.start_break, state=tk.DISABLED)
        self.break_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = ttk.Button(button_frame, text="作業再開", command=self.end_break, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.end_button = ttk.Button(button_frame, text="作業終了", command=self.end_work, state=tk.DISABLED)
        self.end_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="状態更新", command=self.update_status).pack(side=tk.RIGHT, padx=5)

    def create_report_tab(self):
        """レポートタブの作成"""
        report_frame = ttk.Frame(self.notebook)
        self.notebook.add(report_frame, text="レポート")

        # レポート種類選択
        type_group = ttk.LabelFrame(report_frame, text="レポート種類", padding=10)
        type_group.pack(fill=tk.X, padx=10, pady=10)

        self.report_type_var = tk.StringVar(value="daily")
        ttk.Radiobutton(type_group, text="日別レポート", variable=self.report_type_var,
                       value="daily", command=self.on_report_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_group, text="月次レポート", variable=self.report_type_var,
                       value="monthly", command=self.on_report_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_group, text="プロジェクト別レポート", variable=self.report_type_var,
                       value="project", command=self.on_report_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_group, text="会社打刻実績管理", variable=self.report_type_var,
                       value="company_overtime", command=self.on_report_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_group, text="シフト総労働時間管理", variable=self.report_type_var,
                       value="shift_hours", command=self.on_report_type_changed).pack(anchor=tk.W)

        # レポート設定
        setting_group = ttk.LabelFrame(report_frame, text="レポート設定", padding=10)
        setting_group.pack(fill=tk.X, padx=10, pady=10)

        # アカウント
        ttk.Label(setting_group, text="アカウント:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.report_account_var = tk.StringVar()
        self.report_account_combo = ttk.Combobox(setting_group, textvariable=self.report_account_var, width=30)
        self.report_account_combo.grid(row=0, column=1, padx=5, pady=5)
        self.report_account_combo.bind('<<ComboboxSelected>>', self.on_report_account_selected)

        # 日付/年月
        ttk.Label(setting_group, text="日付/年月:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.report_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ttk.Entry(setting_group, textvariable=self.report_date_var, width=32).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(setting_group, text="(日別: YYYY-MM-DD, 月次: YYYY-MM)").grid(row=1, column=2, sticky=tk.W, padx=5)

        # プロジェクト（プロジェクト別レポート用）
        self.project_label = ttk.Label(setting_group, text="プロジェクト:")
        self.report_project_var = tk.StringVar()
        self.report_project_combo = ttk.Combobox(setting_group, textvariable=self.report_project_var, width=30)

        # ボタン
        ttk.Button(setting_group, text="レポート表示", command=self.show_report).grid(row=3, column=0, columnspan=2, pady=10)

        # レポート表示エリア
        result_group = ttk.LabelFrame(report_frame, text="レポート結果", padding=10)
        result_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text = scrolledtext.ScrolledText(
            result_group, height=15, width=70,
            bg=self.colors['bg_light'],
            fg=self.colors['fg']
        )
        self.report_text.pack(fill=tk.BOTH, expand=True)
        self.report_text.config(state=tk.DISABLED)

        # 月次レポート用の会社打刻実績入力フォーム（初期は非表示）
        self.monthly_company_overtime_frame = ttk.LabelFrame(result_group, text="会社打刻実績", padding=10)

        # 対象期間
        self.monthly_period_label = ttk.Label(self.monthly_company_overtime_frame, text="対象期間: -")
        self.monthly_period_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

        # アプリ記録
        ttk.Label(self.monthly_company_overtime_frame, text="アプリ記録:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.monthly_app_hours_label = ttk.Label(self.monthly_company_overtime_frame, text="0.0時間")
        self.monthly_app_hours_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self.monthly_company_overtime_frame, text="(法定時間外労働 + 法定休日労働)",
                  foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # 会社打刻実績
        ttk.Label(self.monthly_company_overtime_frame, text="会社打刻実績:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.monthly_company_hours_var = tk.StringVar(value="0.0")
        self.monthly_company_hours_entry = ttk.Entry(
            self.monthly_company_overtime_frame,
            textvariable=self.monthly_company_hours_var,
            width=15
        )
        self.monthly_company_hours_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self.monthly_company_overtime_frame, text="時間").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # 合計
        ttk.Label(self.monthly_company_overtime_frame, text="合計:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.monthly_combined_hours_label = ttk.Label(
            self.monthly_company_overtime_frame,
            text="0.0時間",
            font=("TkDefaultFont", 10, "bold")
        )
        self.monthly_combined_hours_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # 60時間超過分
        ttk.Label(self.monthly_company_overtime_frame, text="60時間超過分:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.monthly_over_60_label = ttk.Label(self.monthly_company_overtime_frame, text="-")
        self.monthly_over_60_label.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)

        # 保存ボタン
        ttk.Button(
            self.monthly_company_overtime_frame,
            text="保存",
            command=self.save_monthly_company_overtime
        ).grid(row=5, column=0, columnspan=3, pady=10)

        # 会社打刻実績の変更時に合計を更新
        self.monthly_company_hours_var.trace_add('write', self.update_monthly_overtime_display)

        # 月次レポート用の時間外労働情報を保持
        self.current_monthly_overtime_info = None

        # 会社打刻実績管理用のTreeview（初期は非表示）
        self.company_overtime_frame = ttk.Frame(result_group)

        # Treeview - 統合版（シフト時間も含む）
        columns = ('period', 'shift_hours', 'company_overtime', 'app_main_job', 'total_hours', 'over_60', 'night_hours', 'unpaid')
        self.company_overtime_tree = ttk.Treeview(
            self.company_overtime_frame,
            columns=columns,
            show='headings',
            height=12
        )

        self.company_overtime_tree.heading('period', text='対象月')
        self.company_overtime_tree.heading('shift_hours', text='シフト総時間')
        self.company_overtime_tree.heading('company_overtime', text='会社時間外')
        self.company_overtime_tree.heading('app_main_job', text='本アプリ本職')
        self.company_overtime_tree.heading('total_hours', text='総労働時間')
        self.company_overtime_tree.heading('over_60', text='60h超過分')
        self.company_overtime_tree.heading('night_hours', text='深夜労働')
        self.company_overtime_tree.heading('unpaid', text='未払い分')

        self.company_overtime_tree.column('period', width=100)
        self.company_overtime_tree.column('shift_hours', width=90)
        self.company_overtime_tree.column('company_overtime', width=90)
        self.company_overtime_tree.column('app_main_job', width=100)
        self.company_overtime_tree.column('total_hours', width=100)
        self.company_overtime_tree.column('over_60', width=90)
        self.company_overtime_tree.column('night_hours', width=80)
        self.company_overtime_tree.column('unpaid', width=80)

        # スクロールバー
        overtime_scrollbar = ttk.Scrollbar(
            self.company_overtime_frame,
            orient=tk.VERTICAL,
            command=self.company_overtime_tree.yview
        )
        self.company_overtime_tree.configure(yscrollcommand=overtime_scrollbar.set)

        self.company_overtime_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        overtime_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ダブルクリックで編集
        self.company_overtime_tree.bind('<Double-1>', self.edit_company_overtime_from_tree)

        # ボタンフレーム
        self.overtime_button_frame = ttk.Frame(result_group)
        ttk.Button(
            self.overtime_button_frame,
            text="新しい月を追加",
            command=self.add_integrated_work_hours_period
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.overtime_button_frame,
            text="シフト時間編集",
            command=self.edit_shift_hours_from_integrated
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.overtime_button_frame,
            text="会社時間外編集",
            command=self.edit_company_overtime_from_integrated
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.overtime_button_frame,
            text="更新",
            command=self.show_report
        ).pack(side=tk.LEFT, padx=5)

        # シフト総労働時間管理用のTreeview（初期は非表示）
        self.shift_hours_frame = ttk.Frame(result_group)

        # Treeview
        shift_columns = ('period', 'shift_hours')
        self.shift_hours_tree = ttk.Treeview(
            self.shift_hours_frame,
            columns=shift_columns,
            show='headings',
            height=12
        )

        self.shift_hours_tree.heading('period', text='対象月')
        self.shift_hours_tree.heading('shift_hours', text='シフト総労働時間')

        self.shift_hours_tree.column('period', width=200)
        self.shift_hours_tree.column('shift_hours', width=200)

        # スクロールバー
        shift_scrollbar = ttk.Scrollbar(
            self.shift_hours_frame,
            orient=tk.VERTICAL,
            command=self.shift_hours_tree.yview
        )
        self.shift_hours_tree.configure(yscrollcommand=shift_scrollbar.set)

        self.shift_hours_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shift_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ダブルクリックで編集
        self.shift_hours_tree.bind('<Double-1>', self.edit_shift_hours_from_tree)

        # ボタンフレーム
        self.shift_button_frame = ttk.Frame(result_group)
        ttk.Button(
            self.shift_button_frame,
            text="新しい月を追加",
            command=self.add_shift_hours_period
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.shift_button_frame,
            text="選択した月を編集",
            command=self.edit_selected_shift_hours
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.shift_button_frame,
            text="更新",
            command=self.show_report
        ).pack(side=tk.LEFT, padx=5)

        # 初期化
        self.refresh_report_accounts()
        self.on_report_type_changed()

    def create_edit_tab(self):
        """編集・申請タブの作成"""
        edit_frame = ttk.Frame(self.notebook)
        self.notebook.add(edit_frame, text="編集・申請")

        # アカウント選択
        account_group = ttk.LabelFrame(edit_frame, text="アカウント選択", padding=10)
        account_group.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(account_group, text="アカウント:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.edit_account_var = tk.StringVar()
        self.edit_account_combo = ttk.Combobox(account_group, textvariable=self.edit_account_var, width=30)
        self.edit_account_combo.grid(row=0, column=1, padx=5, pady=5)
        self.edit_account_combo.bind('<<ComboboxSelected>>', self.on_edit_account_selected)

        ttk.Button(account_group, text="レコード取得", command=self.load_records).grid(row=0, column=2, padx=5)

        # レコード一覧
        records_group = ttk.LabelFrame(edit_frame, text="打刻レコード一覧", padding=10)
        records_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ツリービュー
        columns = ('date', 'project', 'start', 'end', 'minutes', 'comment', 'status')
        self.records_tree = ttk.Treeview(records_group, columns=columns, show='headings', height=10)

        self.records_tree.heading('date', text='日付')
        self.records_tree.heading('project', text='プロジェクト')
        self.records_tree.heading('start', text='開始')
        self.records_tree.heading('end', text='終了')
        self.records_tree.heading('minutes', text='時間(分)')
        self.records_tree.heading('comment', text='作業内容')
        self.records_tree.heading('status', text='申請状態')

        self.records_tree.column('date', width=100)
        self.records_tree.column('project', width=120)
        self.records_tree.column('start', width=80)
        self.records_tree.column('end', width=80)
        self.records_tree.column('minutes', width=80)
        self.records_tree.column('comment', width=150)
        self.records_tree.column('status', width=80)

        # スクロールバー
        scrollbar = ttk.Scrollbar(records_group, orient=tk.VERTICAL, command=self.records_tree.yview)
        self.records_tree.configure(yscroll=scrollbar.set)

        self.records_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 操作ボタン
        button_group = ttk.LabelFrame(edit_frame, text="操作", padding=10)
        button_group.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_group, text="選択レコードを編集", command=self.edit_selected_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_group, text="選択レコードを削除", command=self.delete_selected_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_group, text="期間指定で申請", command=self.submit_records_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_group, text="編集ログ表示", command=self.show_edit_logs).pack(side=tk.LEFT, padx=5)

        # 初期化
        self.refresh_edit_accounts()

    def create_config_tab(self):
        """設定タブの作成"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="設定")

        # 左側：ユーザー管理
        left_frame = ttk.Frame(config_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 右側：設定
        right_frame = ttk.Frame(config_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        # ユーザー管理グループ
        user_mgmt_group = ttk.LabelFrame(left_frame, text="ユーザー管理", padding=10)
        user_mgmt_group.pack(fill=tk.BOTH, expand=True)

        # 上部：ユーザー追加
        add_frame = ttk.Frame(user_mgmt_group)
        add_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(add_frame, text="新規ユーザー:").pack(side=tk.LEFT, padx=5)
        self.new_user_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_user_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="追加", command=self.add_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="削除", command=self.remove_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="更新", command=self.refresh_user_list).pack(side=tk.LEFT, padx=5)

        # 中部：ユーザーリスト表示
        list_frame = ttk.Frame(user_mgmt_group)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # ユーザーリストのツリービュー
        columns = ('username', 'status', 'projects', 'records', 'closing_day', 'hours')
        self.user_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)

        self.user_tree.heading('username', text='ユーザー名')
        self.user_tree.heading('status', text='状態')
        self.user_tree.heading('projects', text='プロジェクト数')
        self.user_tree.heading('records', text='レコード数')
        self.user_tree.heading('closing_day', text='締め日')
        self.user_tree.heading('hours', text='標準時間')

        self.user_tree.column('username', width=120)
        self.user_tree.column('status', width=100)
        self.user_tree.column('projects', width=100)
        self.user_tree.column('records', width=100)
        self.user_tree.column('closing_day', width=80)
        self.user_tree.column('hours', width=80)

        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.user_tree.yview)
        self.user_tree.configure(yscroll=scrollbar.set)

        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ユーザーを選択した時のイベント
        self.user_tree.bind('<<TreeviewSelect>>', self.on_user_tree_select)

        # 下部：選択ユーザーの契約設定
        config_group = ttk.LabelFrame(user_mgmt_group, text="選択ユーザーの契約設定", padding=10)
        config_group.pack(fill=tk.X, pady=(10, 0))

        # ユーザー名表示
        user_frame = ttk.Frame(config_group)
        user_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(user_frame, text="対象ユーザー:", font=('', 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.selected_user_label = ttk.Label(user_frame, text="（未選択）", font=('', 10, 'bold'), foreground='blue')
        self.selected_user_label.pack(side=tk.LEFT)

        # セパレーター
        ttk.Separator(config_group, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky='ew', pady=10)

        # 締め日設定
        ttk.Label(config_group, text="締め日設定:", font=('', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=5, pady=(0, 5))

        self.closing_day_var = tk.IntVar(value=31)
        closing_frame = ttk.Frame(config_group)
        closing_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5)

        ttk.Radiobutton(closing_frame, text="15日締め（前月16日～当月15日）",
                       variable=self.closing_day_var, value=15).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(closing_frame, text="月末締め（1日～月末）",
                       variable=self.closing_day_var, value=31).pack(anchor=tk.W, pady=2)

        # 標準労働時間設定
        ttk.Label(config_group, text="標準労働時間:", font=('', 9, 'bold')).grid(row=4, column=0, sticky=tk.W, padx=5, pady=(10, 5))

        hours_frame = ttk.Frame(config_group)
        hours_frame.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5)

        self.standard_hours_var = tk.IntVar(value=8)
        ttk.Spinbox(hours_frame, from_=1, to=12, textvariable=self.standard_hours_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(hours_frame, text="時間/日").pack(side=tk.LEFT)
        ttk.Label(hours_frame, text="（残業時間計算の基準）", font=('', 8), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))

        # 保存ボタン
        button_frame = ttk.Frame(config_group)
        button_frame.grid(row=6, column=0, columnspan=3, pady=15)
        ttk.Button(button_frame, text="設定を保存", command=self.save_user_config, width=20).pack()

        # データベース設定（右側）
        db_group = ttk.LabelFrame(right_frame, text="データベース設定", padding=10)
        db_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(db_group, text="保存先パス:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.db_path_var = tk.StringVar(value=self.config_manager.get_db_path())
        ttk.Entry(db_group, textvariable=self.db_path_var, width=50).grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(db_group, text="パスを保存", command=self.save_db_path).grid(row=1, column=0, columnspan=2, pady=10)

        # 自動休憩設定（右側）
        auto_break_group = ttk.LabelFrame(right_frame, text="自動休憩設定", padding=10)
        auto_break_group.pack(fill=tk.X)

        # 説明ラベル
        desc_label = ttk.Label(auto_break_group,
                              text="PCの未操作時間を監視し、一定時間経過後に自動的に休憩打刻します。\n"
                                   "作業中のアカウントが自動的に休憩状態になります。",
                              foreground='gray', font=('', 9))
        desc_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(0, 10))

        # 有効/無効チェックボックス（設定から初期値を読み込み）
        self.auto_break_var = tk.BooleanVar(value=self.auto_break_enabled)
        auto_break_check = ttk.Checkbutton(auto_break_group,
                                          text="自動休憩機能を有効にする",
                                          variable=self.auto_break_var,
                                          command=self.toggle_auto_break)
        auto_break_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # アイドル時間閾値設定（設定から初期値を読み込み）
        threshold_frame = ttk.Frame(auto_break_group)
        threshold_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5)

        ttk.Label(threshold_frame, text="未操作時間の閾値:").pack(side=tk.LEFT, padx=(0, 5))
        self.idle_threshold_var = tk.IntVar(value=self.auto_break_threshold)
        ttk.Spinbox(threshold_frame, from_=5, to=60, textvariable=self.idle_threshold_var,
                   width=10, command=self.update_idle_threshold).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(threshold_frame, text="分").pack(side=tk.LEFT)

        # 状態表示
        self.auto_break_status_label = ttk.Label(auto_break_group,
                                                 text="状態: 無効",
                                                 foreground='gray', font=('', 9))
        self.auto_break_status_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 0))

        # プロジェクト設定（右側）
        project_settings_group = ttk.LabelFrame(right_frame, text="プロジェクト設定", padding=10)
        project_settings_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 説明ラベル
        desc_label = ttk.Label(project_settings_group,
                              text="各プロジェクトが本職の勤務時間に含まれるかを設定します。\n"
                                   "副業のプロジェクトは「含めない」に設定してください。",
                              foreground='gray', font=('', 9))
        desc_label.pack(fill=tk.X, padx=5, pady=(0, 10))

        # アカウント選択
        account_frame = ttk.Frame(project_settings_group)
        account_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(account_frame, text="アカウント:").pack(side=tk.LEFT, padx=(0, 5))
        self.project_settings_account_var = tk.StringVar()
        self.project_settings_account_combo = ttk.Combobox(
            account_frame,
            textvariable=self.project_settings_account_var,
            width=20,
            state='readonly'
        )
        self.project_settings_account_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.project_settings_account_combo.bind('<<ComboboxSelected>>', self.on_project_settings_account_selected)
        ttk.Button(account_frame, text="更新", command=self.refresh_project_settings).pack(side=tk.LEFT, padx=5)

        # プロジェクト一覧
        project_list_frame = ttk.Frame(project_settings_group)
        project_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('project', 'is_main_job', 'git_repo_path')
        self.project_settings_tree = ttk.Treeview(
            project_list_frame,
            columns=columns,
            show='headings',
            height=8
        )

        self.project_settings_tree.heading('project', text='プロジェクト名')
        self.project_settings_tree.heading('is_main_job', text='本職に含める')
        self.project_settings_tree.heading('git_repo_path', text='Gitリポジトリパス')

        self.project_settings_tree.column('project', width=150)
        self.project_settings_tree.column('is_main_job', width=100)
        self.project_settings_tree.column('git_repo_path', width=250)

        # スクロールバー
        project_scrollbar = ttk.Scrollbar(
            project_list_frame,
            orient=tk.VERTICAL,
            command=self.project_settings_tree.yview
        )
        self.project_settings_tree.configure(yscrollcommand=project_scrollbar.set)

        self.project_settings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        project_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ダブルクリックで設定切り替え（本職フラグ）
        self.project_settings_tree.bind('<Double-1>', self.toggle_project_main_job_flag)

        # 右クリックでGitリポジトリパス編集
        self.project_settings_tree.bind('<Button-3>', self.edit_project_git_path)

        # 初期化
        self.refresh_user_list()

        # 自動休憩の初期状態を設定
        if self.auto_break_enabled:
            self.idle_monitor.start_monitoring(self.on_idle_detected)
            self.auto_break_status_label.config(
                text=f"状態: 有効 (閾値: {self.auto_break_threshold}分)",
                foreground='green'
            )
            logger.info(f"自動休憩機能が有効で起動: 閾値={self.auto_break_threshold}分")

    def refresh_accounts(self):
        """アカウント一覧を更新"""
        accounts = self.tc.list_accounts()
        self.account_combo['values'] = accounts
        if accounts and not self.account_var.get():
            self.account_combo.current(0)
            self.on_account_selected()

    def on_account_selected(self, event=None):
        """アカウント選択時の処理"""
        account = self.account_var.get()
        if account:
            projects = self.tc.list_projects(account)
            self.project_combo['values'] = projects
            if projects:
                self.project_combo.current(0)
        # アカウント変更時にボタン状態を更新
        self.update_status()

    def on_project_selected(self, event=None):
        """プロジェクト選択時の処理"""
        # プロジェクト変更時にボタン状態を更新
        self.update_status()

    def detect_git_project(self):
        """GitHubリポジトリ名を検出してプロジェクトに設定"""
        try:
            repo_name = self.git_sync.get_repo_name()
            if repo_name:
                # プロジェクト候補に追加
                account = self.account_var.get()
                if account:
                    current_projects = list(self.project_combo['values'])
                    if repo_name not in current_projects:
                        current_projects.insert(0, repo_name)
                        self.project_combo['values'] = current_projects

                # プロジェクト名を設定
                self.project_var.set(repo_name)
                messagebox.showinfo("Git検出", f"リポジトリ名を検出しました:\n{repo_name}")
                logger.info(f"Gitリポジトリ名を検出: {repo_name}")
            else:
                messagebox.showwarning("Git検出", "Gitリポジトリが見つかりませんでした。\n\nこのディレクトリはGitリポジトリではないか、\nリモートが設定されていない可能性があります。")
        except Exception as e:
            log_exception(logger, "Git検出エラー", e)
            messagebox.showerror("エラー", f"Git検出中にエラーが発生しました:\n{str(e)}")

    def refresh_report_accounts(self):
        """レポート用アカウント一覧を更新"""
        accounts = self.tc.list_accounts()
        self.report_account_combo['values'] = accounts
        if accounts and not self.report_account_var.get():
            self.report_account_combo.current(0)
            self.on_report_account_selected()

    def on_report_account_selected(self, event=None):
        """レポートタブでアカウント選択時の処理"""
        account = self.report_account_var.get()
        if account:
            # 選択されたアカウントのプロジェクト一覧を取得
            projects = self.tc.list_projects(account)
            self.report_project_combo['values'] = projects
            if projects:
                self.report_project_combo.current(0)

    def refresh_user_list(self, keep_selection=False):
        """
        ユーザーリストを更新

        Args:
            keep_selection: 選択状態を維持するかどうか
        """
        # 現在の選択を保存
        selected_username = None
        if keep_selection:
            selection = self.user_tree.selection()
            if selection:
                item = self.user_tree.item(selection[0])
                selected_username = item['values'][0]

        # ツリーをクリア
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)

        # 全ユーザーを取得
        all_users = self.tc.list_accounts()

        # 各ユーザーの情報を取得して表示
        inserted_items = {}
        for username in all_users:
            # 文字列として確実に扱う
            username_str = str(username)

            # 最新の情報を取得（キャッシュを避ける）
            user_info = self.tc.storage.get_user_info(username_str)

            # 状態の判定
            if user_info['is_working']:
                status = "作業中"
            elif user_info['has_records']:
                status = "稼働履歴あり"
            elif user_info['is_registered']:
                status = "登録済み"
            else:
                status = "未登録"

            # 締め日表示
            closing_day = f"{user_info['closing_day']}日"
            if user_info['closing_day'] == 31:
                closing_day = "月末"
            elif user_info['closing_day'] == 15:
                closing_day = "15日"

            # ツリーに追加（textパラメータに元の文字列を保存）
            item_id = self.user_tree.insert('', 'end', text=username_str, values=(
                username_str,
                status,
                user_info['project_count'],
                user_info['record_count'],
                closing_day,
                f"{user_info['standard_hours_per_day']}時間"
            ))
            inserted_items[username_str] = item_id

        # 選択状態を復元
        if selected_username and selected_username in inserted_items:
            item_id = inserted_items[selected_username]
            self.user_tree.selection_set(item_id)
            self.user_tree.see(item_id)
            # 選択イベントを手動でトリガー
            self.on_user_tree_select()

        # アカウント選択肢も更新
        self.refresh_accounts()
        self.refresh_report_accounts()

    def on_user_tree_select(self, event=None):
        """ユーザーリストで選択時の処理"""
        selection = self.user_tree.selection()
        if selection:
            item = self.user_tree.item(selection[0])
            # textパラメータから取得（文字列として保存されている）
            # values[0]だと数値変換される可能性があるため、textを優先
            username = item['text'] if item['text'] else str(item['values'][0])

            self.selected_user_label.config(text=username)

            # 設定を読み込み
            user_info = self.tc.storage.get_user_info(username)
            self.closing_day_var.set(user_info['closing_day'])
            self.standard_hours_var.set(user_info['standard_hours_per_day'])

    def add_user(self):
        """ユーザーを追加"""
        username = self.new_user_var.get().strip()
        if not username:
            messagebox.showerror("エラー", "ユーザー名を入力してください")
            return

        try:
            self.tc.storage.add_user(username)
            self.new_user_var.set("")
            messagebox.showinfo("成功", f"ユーザー '{username}' を追加しました")
            self.refresh_user_list()
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def remove_user(self):
        """選択したユーザーを削除"""
        selection = self.user_tree.selection()
        if not selection:
            messagebox.showerror("エラー", "削除するユーザーを選択してください")
            return

        item = self.user_tree.item(selection[0])
        username = item['values'][0]

        # 確認ダイアログ
        result = messagebox.askyesno("確認", f"ユーザー '{username}' を削除しますか？\n（稼働履歴は削除されません）")
        if result:
            try:
                self.tc.storage.remove_user(username)
                messagebox.showinfo("成功", f"ユーザー '{username}' を削除しました")
                self.refresh_user_list()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def save_user_config(self):
        """選択ユーザーの設定を保存"""
        username = self.selected_user_label.cget("text")
        if username == "（未選択）":
            messagebox.showerror("エラー", "ユーザーを選択してください")
            return

        try:
            closing_day = self.closing_day_var.get()
            standard_hours = self.standard_hours_var.get()

            # 設定を保存
            self.tc.set_account_config(username, closing_day, standard_hours)

            # 保存されたことを確認（JSONから再読み込み）
            saved_config = self.tc.get_account_config(username)

            # 保存確認メッセージ
            closing_day_text = "15日締め" if saved_config['closing_day'] == 15 else "月末締め"
            messagebox.showinfo("設定保存",
                f"{username} の設定を保存しました\n\n"
                f"【保存した内容】\n"
                f"締め日: {saved_config['closing_day']}日 ({closing_day_text})\n"
                f"標準労働時間: {saved_config['standard_hours_per_day']}時間/日\n\n"
                f"※ レポート画面で月次レポートを表示している場合は、\n"
                f"  「レポート表示」ボタンを再度押すと更新されます。")

            # 選択状態を維持してリストを更新
            self.refresh_user_list(keep_selection=True)

            # レポートタブで月次レポートを表示中の場合、自動更新を提案
            if (self.report_type_var.get() == "monthly" and
                self.report_account_var.get() == username and
                self.report_text.get(1.0, tk.END).strip()):
                # レポートが表示されているので自動更新
                self.show_report()
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def on_report_type_changed(self):
        """レポート種類変更時の処理"""
        report_type = self.report_type_var.get()

        # 日付フォーマットの自動変換
        current_date = self.report_date_var.get()
        if report_type == "monthly":
            # 月次レポート: YYYY-MM-DD → YYYY-MM
            if len(current_date) == 10 and current_date.count('-') == 2:
                # YYYY-MM-DD形式ならYYYY-MMに変換
                self.report_date_var.set(current_date[:7])
        elif report_type == "daily":
            # 日別レポート: YYYY-MM → YYYY-MM-DD
            if len(current_date) == 7 and current_date.count('-') == 1:
                # YYYY-MM形式ならYYYY-MM-DDに変換（当月1日）
                self.report_date_var.set(f"{current_date}-01")

        # プロジェクト選択の表示/非表示
        if report_type == "project":
            self.project_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
            self.report_project_combo.grid(row=2, column=1, padx=5, pady=5)
        else:
            self.project_label.grid_forget()
            self.report_project_combo.grid_forget()

        # レポート表示エリアの切り替え
        if report_type == "company_overtime":
            # 会社打刻実績管理：Treeviewを表示
            self.report_text.pack_forget()
            self.monthly_company_overtime_frame.pack_forget()
            self.shift_hours_frame.pack_forget()
            self.shift_button_frame.pack_forget()
            self.company_overtime_frame.pack(fill=tk.BOTH, expand=True)
            self.overtime_button_frame.pack(fill=tk.X, pady=5)
        elif report_type == "shift_hours":
            # シフト総労働時間管理：Treeviewを表示
            self.report_text.pack_forget()
            self.monthly_company_overtime_frame.pack_forget()
            self.company_overtime_frame.pack_forget()
            self.overtime_button_frame.pack_forget()
            self.shift_hours_frame.pack(fill=tk.BOTH, expand=True)
            self.shift_button_frame.pack(fill=tk.X, pady=5)
        elif report_type == "monthly":
            # 月次レポート：report_textと会社打刻実績フォームを表示
            self.company_overtime_frame.pack_forget()
            self.overtime_button_frame.pack_forget()
            self.shift_hours_frame.pack_forget()
            self.shift_button_frame.pack_forget()
            self.report_text.pack(fill=tk.BOTH, expand=True)
            self.monthly_company_overtime_frame.pack(fill=tk.X, padx=10, pady=10)
        else:
            # その他のレポート：report_textのみ表示
            self.company_overtime_frame.pack_forget()
            self.overtime_button_frame.pack_forget()
            self.shift_hours_frame.pack_forget()
            self.shift_button_frame.pack_forget()
            self.monthly_company_overtime_frame.pack_forget()
            self.report_text.pack(fill=tk.BOTH, expand=True)

    def start_work(self):
        """作業開始"""
        account = self.account_var.get()
        project = self.project_var.get()
        comment = self.comment_var.get()

        if not account or not project:
            messagebox.showerror("エラー", "アカウントとプロジェクトを選択してください")
            return

        try:
            session = self.tc.start_work(account, project, comment)
            messagebox.showinfo("作業開始", f"作業を開始しました\n{account} - {project}")
            self.comment_var.set("")  # コメントをクリア
            self.update_status()
            self.refresh_accounts()  # アカウント一覧を更新
        except ValueError as e:
            messagebox.showerror("エラー", str(e))

    def start_break(self):
        """休憩開始"""
        account = self.account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        try:
            session = self.tc.start_break(account)
            messagebox.showinfo("休憩開始", "休憩を開始しました")
            self.update_status()
        except ValueError as e:
            messagebox.showerror("エラー", str(e))

    def end_break(self):
        """作業再開"""
        account = self.account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        try:
            session = self.tc.end_break(account)
            messagebox.showinfo("作業再開", "作業を再開しました")
            self.update_status()
        except ValueError as e:
            messagebox.showerror("エラー", str(e))

    def end_work(self):
        """作業終了"""
        account = self.account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        try:
            # 月間時間外労働の累計を取得
            overtime_info = self.tc.get_monthly_overtime_hours(account)

            # 休日情報を入力するダイアログを表示
            dialog = HolidayInputDialog(
                self.root,
                overtime_info,
                self.tc,
                account
            )
            self.root.wait_window(dialog.top)

            if dialog.result is None:
                # キャンセルされた
                return

            is_holiday = dialog.result['is_holiday']
            is_legal_holiday = dialog.result['is_legal_holiday']

            # 作業終了
            session = self.tc.end_work(account, is_holiday, is_legal_holiday)
            total_hours = session['total_minutes'] / 60
            night_hours = session.get('night_work_minutes', 0) / 60

            # 結果メッセージ
            msg = (f"作業を終了しました\n"
                  f"{session['account']} - {session['project']}\n"
                  f"作業時間: {session['total_minutes']}分 ({total_hours:.2f}時間)")

            if night_hours > 0:
                msg += f"\n深夜労働: {session['night_work_minutes']}分 ({night_hours:.2f}時間)"

            if is_legal_holiday:
                msg += "\n【法定休日】"
            elif is_holiday:
                msg += "\n【休日】"

            messagebox.showinfo("作業終了", msg)
            self.update_status()

            # Git自動同期を別スレッドで実行
            self.perform_git_sync_async(f"作業終了: {session['project']} - {session['comment'][:50] if session.get('comment') else ''}")

        except ValueError as e:
            messagebox.showerror("エラー", str(e))

    def update_status(self):
        """現在の状態を更新"""
        # 選択中のアカウントとプロジェクトを取得
        selected_account = self.account_var.get()
        selected_project = self.project_var.get()

        # 全アカウントのセッションを取得して表示
        all_sessions = self.tc.get_all_current_statuses()

        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)

        if not all_sessions:
            self.status_text.insert(tk.END, "作業セッションなし\n")
        else:
            # 全アカウントの状態を表示
            for idx, (account, sess) in enumerate(all_sessions.items()):
                if idx > 0:
                    self.status_text.insert(tk.END, "\n" + "="*50 + "\n\n")
                status_str = self.format_status(sess)
                # 選択中のアカウントとプロジェクトの組み合わせを強調
                if account == selected_account and sess['project'] == selected_project:
                    self.status_text.insert(tk.END, ">>> 選択中（アカウント・プロジェクト一致） <<<\n")
                elif account == selected_account:
                    self.status_text.insert(tk.END, ">>> 選択中のアカウント（別プロジェクト） <<<\n")
                self.status_text.insert(tk.END, status_str)

        # ボタン制御：選択中のアカウントとプロジェクトの組み合わせで判定
        self._update_button_states(selected_account, selected_project, all_sessions)

        self.status_text.config(state=tk.DISABLED)

    def _update_button_states(self, selected_account, selected_project, all_sessions):
        """
        ボタンの状態を更新

        Args:
            selected_account: 選択中のアカウント
            selected_project: 選択中のプロジェクト
            all_sessions: 全アカウントのセッション情報
        """
        # ボタンがまだ作成されていない場合はスキップ
        if not hasattr(self, 'start_button'):
            return

        # 選択中のアカウントのセッションを取得
        current_session = all_sessions.get(selected_account)

        if not current_session:
            # 選択中のアカウントは作業していない
            self.start_button.config(state=tk.NORMAL)
            self.break_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.end_button.config(state=tk.DISABLED)
        else:
            # 選択中のアカウントは作業中
            # プロジェクトが一致するかチェック
            if current_session['project'] == selected_project:
                # 同じプロジェクトで作業中
                self.start_button.config(state=tk.DISABLED)
                if current_session['status'] == 'on_break':
                    # 休憩中
                    self.break_button.config(state=tk.DISABLED)
                    self.resume_button.config(state=tk.NORMAL)
                    self.end_button.config(state=tk.DISABLED)
                else:
                    # 作業中
                    self.break_button.config(state=tk.NORMAL)
                    self.resume_button.config(state=tk.DISABLED)
                    self.end_button.config(state=tk.NORMAL)
            else:
                # 別のプロジェクトで作業中
                # 新しいプロジェクトは開始できない（アカウントが作業中のため）
                self.start_button.config(state=tk.DISABLED)
                self.break_button.config(state=tk.DISABLED)
                self.resume_button.config(state=tk.DISABLED)
                self.end_button.config(state=tk.DISABLED)

    def format_status(self, session):
        """セッション情報をフォーマット"""
        lines = []
        lines.append(f"現在の作業: {session['account']} - {session['project']}")
        lines.append(f"開始時刻: {self.format_datetime(session['start_time'])}")
        lines.append(f"状態: {'休憩中' if session['status'] == 'on_break' else '作業中'}")
        lines.append(f"休憩回数: {len(session['breaks'])}回")
        lines.append(f"現在までの作業時間: {self.format_time(session['current_work_minutes'])}")

        if session['breaks']:
            lines.append("\n休憩履歴:")
            for i, brk in enumerate(session['breaks'], 1):
                start = self.format_datetime(brk['start'])
                end = self.format_datetime(brk['end']) if brk['end'] else '(休憩中)'
                lines.append(f"  {i}. {start} - {end}")

        return '\n'.join(lines)

    def format_time(self, minutes):
        """分を時間:分形式に変換"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}時間{mins:02d}分"

    def format_datetime(self, iso_string):
        """ISO形式の日時を読みやすい形式に変換"""
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def show_report(self):
        """レポートを表示"""
        report_type = self.report_type_var.get()
        account = self.report_account_var.get()

        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        try:
            if report_type == "company_overtime":
                # 会社打刻実績管理
                self.show_company_overtime_report(account)
            elif report_type == "shift_hours":
                # シフト総労働時間管理
                self.show_shift_hours_report(account)
            else:
                # 通常のレポート
                self.report_text.config(state=tk.NORMAL)
                self.report_text.delete(1.0, tk.END)

                if report_type == "daily":
                    date = self.report_date_var.get()
                    summary = self.tc.get_daily_summary(account, date)
                    report = self.format_daily_report(summary)
                elif report_type == "monthly":
                    year_month = self.report_date_var.get()
                    try:
                        year, month = map(int, year_month.split('-'))
                    except ValueError:
                        messagebox.showerror("エラー", "年月は YYYY-MM 形式で指定してください")
                        return
                    summary = self.tc.get_monthly_summary(account, year, month)
                    report = self.format_monthly_report(summary)

                    # 会社打刻実績情報を月次サマリーから取得して表示
                    # アプリ記録 = 総労働時間
                    app_hours = summary['total_hours']
                    company_overtime_hours = self.tc.get_company_overtime(account, year, month)
                    combined_overtime_hours = app_hours + company_overtime_hours
                    over_60_hours = max(0, combined_overtime_hours - 60)

                    self.current_monthly_overtime_info = {
                        'period_start': summary['start_date'],
                        'period_end': summary['end_date'],
                        'year': year,
                        'month': month,
                        'total_for_60h_calc_hours': app_hours,
                        'company_overtime_hours': company_overtime_hours,
                        'combined_overtime_hours': combined_overtime_hours,
                        'over_60_hours': over_60_hours
                    }
                    self.update_monthly_company_overtime_form()
                elif report_type == "project":
                    project = self.report_project_var.get()
                    if not project:
                        messagebox.showerror("エラー", "プロジェクトを選択してください")
                        return
                    summary = self.tc.get_project_summary(account, project)
                    report = self.format_project_report(summary)

                self.report_text.insert(tk.END, report)
                self.report_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def format_daily_report(self, summary):
        """日別レポートをフォーマット"""
        lines = []
        lines.append("【日別レポート】")
        lines.append(f"アカウント: {summary['account']}")
        lines.append(f"日付: {summary['date']}")
        lines.append(f"合計作業時間: {self.format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")

        if summary['projects']:
            lines.append("\nプロジェクト別内訳:")
            for project, minutes in sorted(summary['projects'].items()):
                lines.append(f"  - {project}: {self.format_time(minutes)}")

        return '\n'.join(lines)

    def format_monthly_report(self, summary):
        """月次レポートをフォーマット"""
        lines = []
        closing_day_text = "月末締め" if summary['closing_day'] == 31 else "15日締め"
        lines.append(f"【月次レポート - {summary['year']}年{summary['month']}月】({closing_day_text})")
        lines.append(f"アカウント: {summary['account']}")
        lines.append(f"集計期間: {summary['start_date']} ～ {summary['end_date']}")
        lines.append(f"稼働日数: {summary['working_days']}日")

        # 日曜日を除いた作業時間
        weekday_minutes = summary['total_minutes'] - summary.get('sunday_work_minutes', 0)
        weekday_hours = weekday_minutes / 60

        lines.append(f"\n平日・土曜作業時間: {self.format_time(weekday_minutes)} ({weekday_hours:.2f}時間)")

        if summary['total_overtime_minutes'] > 0:
            lines.append(f"  うち残業時間: {self.format_time(summary['total_overtime_minutes'])} ({summary['total_overtime_hours']:.2f}時間)")
        else:
            lines.append("  うち残業時間: なし")

        # 日曜日の作業時間を別表示
        if summary.get('sunday_work_minutes', 0) > 0:
            lines.append(f"\n日曜日作業時間: {self.format_time(summary['sunday_work_minutes'])} ({summary['sunday_work_hours']:.2f}時間)")
            lines.append(f"  日曜日稼働日数: {summary['sunday_days_count']}日")
            lines.append(f"  日曜日: {', '.join(summary['sunday_days'])}")

        lines.append(f"\n総作業時間: {self.format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")

        if summary['project_stats']:
            lines.append("\n【プロジェクト別内訳】")
            for project, stats in sorted(summary['project_stats'].items()):
                lines.append(f"\n■ {project}")
                lines.append(f"  稼働日数: {stats['days_worked_count']}日")
                lines.append(f"  作業時間: {self.format_time(stats['total_minutes'])} ({stats['total_hours']:.2f}時間)")
                lines.append(f"  残業時間: {self.format_time(stats['overtime_minutes'])} ({stats['overtime_hours']:.2f}時間)")

        return '\n'.join(lines)

    def format_project_report(self, summary):
        """プロジェクト別レポートをフォーマット"""
        lines = []
        lines.append("【プロジェクト別レポート】")
        lines.append(f"アカウント: {summary['account']}")
        lines.append(f"プロジェクト: {summary['project']}")
        lines.append(f"レコード数: {summary['record_count']}セッション")
        lines.append(f"合計作業時間: {self.format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")

        if summary['days']:
            lines.append("\n日別内訳:")
            for date, minutes in sorted(summary['days'].items()):
                lines.append(f"  {date}: {self.format_time(minutes)}")

        return '\n'.join(lines)

    def show_company_overtime_report(self, account):
        """会社打刻実績管理レポート（統合ビュー）を表示"""
        # Treeviewをクリア
        for item in self.company_overtime_tree.get_children():
            self.company_overtime_tree.delete(item)

        # シフト総労働時間と会社打刻実績の両方を取得
        all_shift_hours = self.tc.storage.get_all_shift_total_hours(account)
        all_company_overtime = self.tc.get_all_company_overtime(account)

        # 両方の期間キーをマージ
        all_periods = set(all_shift_hours.keys()) | set(all_company_overtime.keys())

        # 各月の情報を取得して表示
        for period_key in sorted(all_periods, reverse=True):
            year, month = map(int, period_key.split('-'))

            # シフト総時間
            shift_hours = all_shift_hours.get(period_key, 0.0)

            # 会社時間外（時間外労働時間のみ）
            company_overtime = all_company_overtime.get(period_key, 0.0)

            # 本アプリ本職実績
            app_main_job = self.tc.get_monthly_main_job_hours(account, year, month)

            # 60時間超過分 = （会社時間外 + 本アプリ本職実績） - 60
            combined_for_60h = company_overtime + app_main_job
            over_60 = max(0, combined_for_60h - 60)

            # 深夜労働時間
            night_hours = self.tc.get_monthly_night_work_hours(account, year, month)

            # 未払い分打刻実績 = 本アプリ本職実績のみ
            unpaid = app_main_job

            # 表示する月の形式
            period_display = f"{year}年{month:02d}月期"

            # 60時間超過分の表示
            if over_60 > 0:
                over_60_display = f"{over_60:.1f}"
            else:
                over_60_display = "-"

            # 危険度判定のためのタグ設定
            tags = []

            # 本職関連総労働時間 = シフト総時間 + 会社時間外 + 本アプリ本職
            total_work_hours = shift_hours + company_overtime + app_main_job

            # 時間外労働時間の合計 = 会社時間外 + 本アプリ本職
            total_overtime = company_overtime + app_main_job

            # 優先度順に判定（複数条件に当てはまる場合、最も危険度の高いタグを適用）
            if total_work_hours > 250:
                # 過労死ライン超過（最優先）
                tags.append("karoshi_line")
            elif total_overtime > 80:
                # 時間外80時間超過
                tags.append("overtime_80")
            elif total_overtime > 45:
                # 時間外45時間超過
                tags.append("overtime_45")

            # Treeviewに追加（8列：対象月、シフト総時間、会社時間外、本アプリ本職、総労働時間、60h超過分、深夜労働、未払い分）
            item_id = self.company_overtime_tree.insert(
                '',
                'end',
                values=(
                    period_display,
                    f"{shift_hours:.1f}",
                    f"{company_overtime:.1f}",
                    f"{app_main_job:.1f}",
                    f"{total_work_hours:.1f}",
                    over_60_display,
                    f"{night_hours:.1f}",
                    f"{unpaid:.1f}"
                ),
                tags=tuple(tags)
            )

        # タグの色設定
        self.company_overtime_tree.tag_configure("karoshi_line", background="#ffcccc", foreground="red")  # 過労死ライン：赤背景＋赤文字
        self.company_overtime_tree.tag_configure("overtime_80", foreground="red")  # 80時間超過：赤文字
        self.company_overtime_tree.tag_configure("overtime_45", foreground="#ff8800")  # 45時間超過：オレンジ（黄色より視認性高い）

    def edit_company_overtime_from_tree(self, event):
        """Treeviewからダブルクリックで編集"""
        selection = self.company_overtime_tree.selection()
        if selection:
            self.edit_selected_company_overtime()

    def edit_selected_company_overtime(self):
        """選択した月の会社打刻実績を編集"""
        selection = self.company_overtime_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "編集する月を選択してください")
            return

        # 選択された行の情報を取得
        item = selection[0]
        values = self.company_overtime_tree.item(item, 'values')
        period_display = values[0]  # "YYYY年MM月期"
        current_value = float(values[2])  # 2列目：会社時間外

        # 年月を抽出
        import re
        match = re.match(r'(\d+)年(\d+)月期', period_display)
        if not match:
            return

        year = int(match.group(1))
        month = int(match.group(2))
        account = self.report_account_var.get()

        # 入力ダイアログ
        new_value = simpledialog.askfloat(
            "会社打刻実績の編集",
            f"{period_display}の会社打刻実績（時間外労働時間）を入力してください。",
            initialvalue=current_value,
            minvalue=0.0,
            maxvalue=500.0
        )

        if new_value is not None:
            # 保存
            self.tc.set_company_overtime(account, year, month, new_value)
            # 表示を更新
            self.show_report()

    def add_integrated_work_hours_period(self):
        """新しい月のシフト時間と会社時間外を追加"""
        account = self.report_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # 年月の入力
        period_str = simpledialog.askstring(
            "新しい月を追加",
            "追加する月を入力してください（YYYY-MM形式）\n例: 2025-11"
        )

        if not period_str:
            return

        try:
            year, month = map(int, period_str.split('-'))
            if month < 1 or month > 12:
                raise ValueError("月は1-12の範囲で指定してください")
        except ValueError as e:
            messagebox.showerror("エラー", f"無効な形式です: {e}")
            return

        # シフト総労働時間の入力
        shift_hours = simpledialog.askfloat(
            "シフト総労働時間の入力",
            f"{year}年{month:02d}月期のシフト総労働時間を入力してください\n\n"
            f"※本職のシフト表に記載された総労働時間を入力してください。\n"
            f"  例：176時間",
            minvalue=0.0,
            maxvalue=1000.0
        )

        if shift_hours is None:
            return

        # 会社時間外労働時間の入力
        company_overtime = simpledialog.askfloat(
            "会社時間外労働時間の入力",
            f"{year}年{month:02d}月期の会社打刻実績（時間外労働時間）を入力してください\n\n"
            f"※休日労働時間を含む時間外労働時間を入力してください。\n"
            f"  例：26.5時間",
            minvalue=0.0,
            maxvalue=500.0
        )

        if company_overtime is None:
            return

        # 両方を保存
        self.tc.storage.set_shift_total_hours(account, year, month, shift_hours)
        self.tc.set_company_overtime(account, year, month, company_overtime)

        # 表示を更新
        self.show_report()
        messagebox.showinfo("完了", f"{year}年{month:02d}月期のデータを追加しました")

    def edit_shift_hours_from_integrated(self):
        """統合ビューからシフト時間を編集"""
        selection = self.company_overtime_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "編集する月を選択してください")
            return

        # 選択された行の情報を取得
        item = selection[0]
        values = self.company_overtime_tree.item(item, 'values')
        period_display = values[0]  # "YYYY年MM月期"
        current_value = float(values[1])  # 1列目：シフト総時間

        # 年月を抽出
        import re
        match = re.match(r'(\d+)年(\d+)月期', period_display)
        if not match:
            return

        year = int(match.group(1))
        month = int(match.group(2))
        account = self.report_account_var.get()

        # 入力ダイアログ
        new_value = simpledialog.askfloat(
            "シフト総労働時間の編集",
            f"{period_display}のシフト総労働時間を入力してください。",
            initialvalue=current_value,
            minvalue=0.0,
            maxvalue=1000.0
        )

        if new_value is not None:
            # 保存
            self.tc.storage.set_shift_total_hours(account, year, month, new_value)
            # 表示を更新
            self.show_report()

    def edit_company_overtime_from_integrated(self):
        """統合ビューから会社時間外を編集"""
        # edit_selected_company_overtime を呼び出すだけ
        self.edit_selected_company_overtime()

    def update_monthly_company_overtime_form(self):
        """月次レポート用の会社打刻実績フォームを更新"""
        if not self.current_monthly_overtime_info:
            return

        info = self.current_monthly_overtime_info

        # 対象期間
        period_text = f"対象期間: {info['period_start']} ～ {info['period_end']} ({info['year']}年{info['month']}月期)"
        self.monthly_period_label.config(text=period_text)

        # アプリ記録
        app_hours = info['total_for_60h_calc_hours']
        app_text = f"{app_hours:.1f}時間"
        self.monthly_app_hours_label.config(text=app_text)

        # 会社打刻実績
        company_hours = info['company_overtime_hours']
        self.monthly_company_hours_var.set(f"{company_hours:.1f}")

        # 合計と60時間超過分を更新
        self.update_monthly_overtime_display()

    def update_monthly_overtime_display(self, *args):
        """月次レポート用の合計と60時間超過分の表示を更新"""
        if not self.current_monthly_overtime_info:
            return

        try:
            company_hours = float(self.monthly_company_hours_var.get())
        except ValueError:
            company_hours = 0.0

        app_hours = self.current_monthly_overtime_info['total_for_60h_calc_hours']
        combined_hours = app_hours + company_hours
        over_60_hours = max(0, combined_hours - 60)

        # 合計表示
        combined_text = f"{combined_hours:.1f}時間"
        if combined_hours > 60:
            self.monthly_combined_hours_label.config(text=combined_text, foreground="red")
        elif combined_hours > 50:
            self.monthly_combined_hours_label.config(text=combined_text, foreground="orange")
        else:
            self.monthly_combined_hours_label.config(text=combined_text, foreground="black")

        # 60時間超過分表示
        if over_60_hours > 0:
            over_60_text = f"{over_60_hours:.1f}時間 超過"
            self.monthly_over_60_label.config(text=over_60_text, foreground="red")
        else:
            self.monthly_over_60_label.config(text="-", foreground="black")

    def save_monthly_company_overtime(self):
        """月次レポートの会社打刻実績を保存"""
        if not self.current_monthly_overtime_info:
            messagebox.showerror("エラー", "月次レポートを表示してから保存してください")
            return

        account = self.report_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        try:
            company_hours = float(self.monthly_company_hours_var.get())
        except ValueError:
            messagebox.showerror("エラー", "有効な数値を入力してください")
            return

        if company_hours < 0:
            messagebox.showerror("エラー", "0以上の数値を入力してください")
            return

        # 保存
        year = self.current_monthly_overtime_info['year']
        month = self.current_monthly_overtime_info['month']
        self.tc.set_company_overtime(account, year, month, company_hours)

        messagebox.showinfo("保存完了", f"{year}年{month}月期の会社打刻実績を保存しました")

        # 表示を更新
        self.show_report()

    def add_company_overtime_period(self):
        """新しい月の会社打刻実績を追加"""
        account = self.report_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # 年月を入力
        year_month = simpledialog.askstring(
            "新しい月を追加",
            "対象月を入力してください（YYYY-MM形式）\n例: 2025-11",
            initialvalue=datetime.now().strftime('%Y-%m')
        )

        if not year_month:
            return

        try:
            year, month = map(int, year_month.split('-'))
        except ValueError:
            messagebox.showerror("エラー", "年月はYYYY-MM形式で入力してください")
            return

        # 時間外労働時間を入力
        hours = simpledialog.askfloat(
            "会社打刻実績の入力",
            f"{year}年{month}月期の会社打刻実績（時間外労働時間）を入力してください。",
            initialvalue=0.0,
            minvalue=0.0,
            maxvalue=500.0
        )

        if hours is not None:
            # 保存
            self.tc.set_company_overtime(account, year, month, hours)
            # 表示を更新
            self.show_report()

    def save_db_path(self):
        """データベースパスを保存"""
        db_path = self.db_path_var.get()
        try:
            self.config_manager.set_db_path(db_path)
            messagebox.showinfo("設定保存", "データベースパスを保存しました\n再起動後に有効になります")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def schedule_status_update(self):
        """定期的にステータスを更新"""
        self.update_status()
        # 30秒後に再度実行
        self.root.after(30000, self.schedule_status_update)

    def toggle_auto_break(self):
        """自動休憩機能のオン/オフを切り替え"""
        try:
            if self.auto_break_var.get():
                # 機能を有効化
                self.auto_break_enabled = True
                self.auto_break_threshold = self.idle_threshold_var.get()
                self.idle_monitor.set_idle_threshold(self.auto_break_threshold)
                self.idle_monitor.start_monitoring(self.on_idle_detected)
                self.auto_break_status_label.config(
                    text=f"状態: 有効 (閾値: {self.auto_break_threshold}分)",
                    foreground='green'
                )
                logger.info(f"自動休憩機能を有効化: 閾値={self.auto_break_threshold}分")
            else:
                # 機能を無効化
                self.auto_break_enabled = False
                self.idle_monitor.stop_monitoring()
                self.auto_break_status_label.config(
                    text="状態: 無効",
                    foreground='gray'
                )
                logger.info("自動休憩機能を無効化")

            # 設定を保存
            self.save_auto_break_config()

        except Exception as e:
            log_exception(logger, "自動休憩切り替えエラー", e)
            messagebox.showerror("エラー", f"自動休憩機能の切り替えに失敗しました: {str(e)}")

    def update_idle_threshold(self):
        """アイドル閾値の更新"""
        try:
            new_threshold = self.idle_threshold_var.get()
            self.auto_break_threshold = new_threshold

            if self.auto_break_enabled:
                self.idle_monitor.set_idle_threshold(new_threshold)
                self.auto_break_status_label.config(
                    text=f"状態: 有効 (閾値: {new_threshold}分)"
                )
                logger.info(f"アイドル閾値を更新: {new_threshold}分")

            # 設定を保存
            self.save_auto_break_config()

        except Exception as e:
            log_exception(logger, "閾値更新エラー", e)

    def on_idle_detected(self, idle_minutes: float):
        """
        アイドル状態検出時のコールバック

        Args:
            idle_minutes: アイドル時間（分）
        """
        try:
            logger.info(f"アイドル検出: {idle_minutes:.1f}分")

            # 現在作業中のアカウントを取得
            all_sessions = self.tc.storage.get_all_current_sessions()

            if not all_sessions:
                logger.info("作業中のアカウントがありません（自動休憩スキップ）")
                return

            # 作業中の全アカウントに対して休憩打刻
            for account, session in all_sessions.items():
                # 既に休憩中の場合はスキップ
                if session.get('status') == 'on_break':
                    logger.info(f"{account} は既に休憩中です（スキップ）")
                    continue

                try:
                    # 休憩開始
                    self.tc.start_break(account)
                    logger.info(f"{account} の自動休憩を開始しました")

                    # Git自動同期を別スレッドで実行
                    self.perform_git_sync_async(f"自動休憩: {account} - アイドル時間 {idle_minutes:.1f}分")

                    # GUIに通知（メインスレッドで実行）
                    self.root.after(0, lambda a=account, m=idle_minutes: self.show_auto_break_notification(a, m))

                except Exception as e:
                    log_exception(logger, f"自動休憩エラー ({account})", e)

            # ステータスを更新
            self.root.after(0, self.update_status)

        except Exception as e:
            log_exception(logger, "アイドル検出処理エラー", e)

    def show_auto_break_notification(self, account: str, idle_minutes: float):
        """
        自動休憩の通知を表示

        Args:
            account: アカウント名
            idle_minutes: アイドル時間（分）
        """
        # 打刻タブに切り替え
        self.notebook.select(0)

        # 通知を表示
        result = messagebox.showinfo(
            "自動休憩",
            f"{account} のアカウントが自動的に休憩状態になりました。\n\n"
            f"PCの未操作時間: {idle_minutes:.1f}分\n"
            f"閾値: {self.idle_threshold_var.get()}分\n\n"
            f"作業を再開する場合は「打刻」タブで\n"
            f"対象アカウントを選択し「作業再開」ボタンを押してください。",
            icon='info'
        )

        # 通知を閉じたら作業再開ボタンを強調
        self.highlight_resume_button()

    def highlight_resume_button(self):
        """作業再開ボタンを一時的に強調表示"""
        try:
            if hasattr(self, 'resume_button'):
                # 元のスタイルを保存
                original_style = self.resume_button.cget('style') if self.resume_button.cget('style') else ''

                # 強調スタイルを適用（点滅効果）
                def blink(count=0):
                    if count < 6:  # 3回点滅
                        if count % 2 == 0:
                            # ボタンを目立たせる（背景色を変更）
                            try:
                                self.resume_button.state(['!disabled'])
                            except:
                                pass
                        self.root.after(500, lambda: blink(count + 1))

                blink()
        except Exception as e:
            logger.warning(f"作業再開ボタン強調エラー: {e}")

    def load_auto_break_config(self):
        """自動休憩設定を読み込み"""
        try:
            config = self.tc.storage.load_config()
            auto_break_config = config.get('auto_break', {})

            self.auto_break_enabled = auto_break_config.get('enabled', False)
            self.auto_break_threshold = auto_break_config.get('threshold_minutes', 15)

            logger.info(f"自動休憩設定を読み込み: enabled={self.auto_break_enabled}, threshold={self.auto_break_threshold}分")
        except Exception as e:
            log_exception(logger, "自動休憩設定の読み込みエラー", e)
            # デフォルト値を使用
            self.auto_break_enabled = False
            self.auto_break_threshold = 15

    def save_auto_break_config(self):
        """自動休憩設定を保存"""
        try:
            config = self.tc.storage.load_config()
            config['auto_break'] = {
                'enabled': self.auto_break_enabled,
                'threshold_minutes': self.auto_break_threshold
            }
            self.tc.storage.save_config(config)
            logger.info(f"自動休憩設定を保存: enabled={self.auto_break_enabled}, threshold={self.auto_break_threshold}分")
        except Exception as e:
            log_exception(logger, "自動休憩設定の保存エラー", e)
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {str(e)}")

    def perform_git_sync_async(self, commit_message=None):
        """
        Git自動同期を非同期で実行

        Args:
            commit_message: コミットメッセージ（Noneの場合は自動生成）
        """
        def git_sync_thread():
            try:
                logger.info(f"Git自動同期開始（非同期）: {commit_message}")
                success, message = self.git_sync.auto_sync(commit_message)

                # 結果をメインスレッドで通知
                def show_result():
                    if success:
                        logger.info(f"Git自動同期成功: {message}")
                        # 成功時は控えめな通知（ステータスバーに表示するなど）
                        # messagebox.showinfo("Git同期", message)
                    else:
                        logger.error(f"Git自動同期失敗: {message}")
                        messagebox.showwarning("Git同期エラー", f"Git同期に失敗しました:\n{message}\n\n手動で確認してください。")

                self.root.after(0, show_result)

            except Exception as e:
                log_exception(logger, "Git自動同期エラー（非同期）", e)

                def show_error():
                    messagebox.showerror("Git同期エラー", f"Git同期中にエラーが発生しました:\n{str(e)}")

                self.root.after(0, show_error)

        # 別スレッドで実行
        thread = threading.Thread(target=git_sync_thread, daemon=True)
        thread.start()

    def refresh_edit_accounts(self):
        """編集タブのアカウント一覧を更新"""
        accounts = self.tc.list_accounts()
        self.edit_account_combo['values'] = accounts
        if accounts and not self.edit_account_var.get():
            self.edit_account_combo.current(0)

    def on_edit_account_selected(self, event=None):
        """編集タブでアカウント選択時の処理"""
        pass

    def load_records(self):
        """レコードを読み込んで表示"""
        account = self.edit_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # ツリービューをクリア
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        # レコードを取得
        records = self.tc.storage.get_records(account)
        self.current_records = records  # 編集用に保存

        # ツリービューに追加
        for record in records:
            date = record.get('date', '')
            project = record.get('project', '')
            start = record.get('start_time', '')[:16] if record.get('start_time') else ''
            end = record.get('end_time', '')[:16] if record.get('end_time') else ''
            minutes = record.get('total_minutes', 0)
            comment = record.get('comment', '')
            status = record.get('submission_status', 'none')

            self.records_tree.insert('', 'end', values=(date, project, start, end, minutes, comment, status))

        messagebox.showinfo("完了", f"{len(records)}件のレコードを読み込みました")

    def edit_selected_record(self):
        """選択したレコードを編集"""
        selection = self.records_tree.selection()
        if not selection:
            messagebox.showerror("エラー", "レコードを選択してください")
            return

        # 選択されたレコードのインデックスを取得
        item = selection[0]
        index = self.records_tree.index(item)
        record = self.current_records[index]

        # 編集ダイアログを表示
        self.show_edit_dialog(record, index)

    def show_edit_dialog(self, record, index):
        """レコード編集ダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title("レコード編集")
        dialog.geometry("500x500")

        # 現在の休憩時間を計算
        current_break_minutes = 0
        for brk in record.get('breaks', []):
            if brk.get('end'):
                from datetime import datetime
                break_start = datetime.fromisoformat(brk['start'])
                break_end = datetime.fromisoformat(brk['end'])
                current_break_minutes += int((break_end - break_start).total_seconds() / 60)

        # 日付
        ttk.Label(dialog, text="日付:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        date_var = tk.StringVar(value=record.get('date', ''))
        ttk.Entry(dialog, textvariable=date_var, width=30).grid(row=0, column=1, padx=10, pady=5)

        # プロジェクト
        ttk.Label(dialog, text="プロジェクト:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        project_var = tk.StringVar(value=record.get('project', ''))
        ttk.Entry(dialog, textvariable=project_var, width=30).grid(row=1, column=1, padx=10, pady=5)

        # 開始時刻
        ttk.Label(dialog, text="開始時刻:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        start_var = tk.StringVar(value=record.get('start_time', ''))
        ttk.Entry(dialog, textvariable=start_var, width=30).grid(row=2, column=1, padx=10, pady=5)

        # 終了時刻
        ttk.Label(dialog, text="終了時刻:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        end_var = tk.StringVar(value=record.get('end_time', ''))
        ttk.Entry(dialog, textvariable=end_var, width=30).grid(row=3, column=1, padx=10, pady=5)

        # 合計休憩時間（分）
        ttk.Label(dialog, text="合計休憩時間(分):").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        break_minutes_var = tk.IntVar(value=current_break_minutes)
        break_entry = ttk.Entry(dialog, textvariable=break_minutes_var, width=30)
        break_entry.grid(row=4, column=1, padx=10, pady=5)
        ttk.Label(dialog, text="※直接編集可能", font=('', 8), foreground='gray').grid(row=4, column=2, sticky=tk.W)

        # 作業内容
        ttk.Label(dialog, text="作業内容:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        comment_var = tk.StringVar(value=record.get('comment', ''))
        ttk.Entry(dialog, textvariable=comment_var, width=30).grid(row=5, column=1, padx=10, pady=5)

        # 変更理由
        ttk.Label(dialog, text="変更理由:").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        reason_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=reason_var, width=30).grid(row=6, column=1, padx=10, pady=5)

        # 計算結果表示
        calc_frame = ttk.LabelFrame(dialog, text="計算結果", padding=10)
        calc_frame.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        calc_label = ttk.Label(calc_frame, text="", font=('', 9))
        calc_label.pack()

        def update_calculation(*args):
            """作業時間の計算結果を更新"""
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_var.get())
                end_dt = datetime.fromisoformat(end_var.get())
                total_minutes = int((end_dt - start_dt).total_seconds() / 60)
                break_mins = break_minutes_var.get()
                work_minutes = total_minutes - break_mins

                calc_text = f"総時間: {total_minutes}分 - 休憩: {break_mins}分 = 作業時間: {work_minutes}分 ({work_minutes/60:.2f}時間)"
                calc_label.config(text=calc_text, foreground='green')
            except:
                calc_label.config(text="時刻形式が正しくありません", foreground='red')

        # 変更時に計算を更新
        start_var.trace('w', update_calculation)
        end_var.trace('w', update_calculation)
        break_minutes_var.trace('w', update_calculation)

        # 初期表示
        update_calculation()

        def save_changes():
            # 更新されたレコードを作成
            updated_record = record.copy()
            updated_record['date'] = date_var.get()
            updated_record['project'] = project_var.get()
            updated_record['start_time'] = start_var.get()
            updated_record['end_time'] = end_var.get()
            updated_record['comment'] = comment_var.get()

            # 作業時間を再計算
            from datetime import datetime
            try:
                start_dt = datetime.fromisoformat(updated_record['start_time'])
                end_dt = datetime.fromisoformat(updated_record['end_time'])
                total_minutes = int((end_dt - start_dt).total_seconds() / 60)

                # ユーザーが入力した休憩時間を使用
                break_mins = break_minutes_var.get()
                work_minutes = total_minutes - break_mins

                if work_minutes < 0:
                    messagebox.showerror("エラー", "休憩時間が総時間を超えています")
                    return

                updated_record['total_minutes'] = work_minutes

                # 休憩時間の情報を更新（元のbreaksデータは保持しつつ、編集した休憩時間を記録）
                # 注: 既存のbreaksデータは保持し、total_break_minutesフィールドを追加
                updated_record['total_break_minutes'] = break_mins

            except Exception as e:
                messagebox.showerror("エラー", f"時刻の形式が正しくありません: {e}")
                return

            # レコードを更新
            account = self.edit_account_var.get()
            success = self.tc.update_record(account, index, updated_record, reason_var.get())

            if success:
                messagebox.showinfo("成功", "レコードを更新しました")
                dialog.destroy()
                self.load_records()
            else:
                messagebox.showerror("エラー", "レコードの更新に失敗しました")

        # ボタン
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=8, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def delete_selected_record(self):
        """選択したレコードを削除"""
        selection = self.records_tree.selection()
        if not selection:
            messagebox.showerror("エラー", "レコードを選択してください")
            return

        # 確認ダイアログ
        if not messagebox.askyesno("確認", "選択したレコードを削除しますか?"):
            return

        # 削除理由を入力
        reason = tk.simpledialog.askstring("削除理由", "削除理由を入力してください:")
        if reason is None:
            return

        # 選択されたレコードのインデックスを取得
        item = selection[0]
        index = self.records_tree.index(item)

        # レコードを削除
        account = self.edit_account_var.get()
        success = self.tc.delete_record(account, index, reason)

        if success:
            messagebox.showinfo("成功", "レコードを削除しました")
            self.load_records()
        else:
            messagebox.showerror("エラー", "レコードの削除に失敗しました")

    def submit_records_dialog(self):
        """期間指定で申請ダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title("期間指定で申請")
        dialog.geometry("400x200")

        # 開始日
        ttk.Label(dialog, text="開始日 (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        start_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=start_var, width=20).grid(row=0, column=1, padx=10, pady=10)

        # 終了日
        ttk.Label(dialog, text="終了日 (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        end_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=end_var, width=20).grid(row=1, column=1, padx=10, pady=10)

        # 申請理由
        ttk.Label(dialog, text="申請理由:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        reason_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=reason_var, width=20).grid(row=2, column=1, padx=10, pady=10)

        def submit():
            account = self.edit_account_var.get()
            if not account:
                messagebox.showerror("エラー", "アカウントを選択してください")
                return

            count = self.tc.submit_records(account, start_var.get(), end_var.get(), reason_var.get())
            messagebox.showinfo("完了", f"{count}件のレコードを申請しました")
            dialog.destroy()
            self.load_records()

        # ボタン
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="申請", command=submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def show_edit_logs(self):
        """編集ログを表示"""
        account = self.edit_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # ログを取得
        logs = self.tc.get_edit_logs(account=account, limit=100)

        # ダイアログを作成
        dialog = tk.Toplevel(self.root)
        dialog.title(f"編集ログ - {account}")
        dialog.geometry("800x500")

        # ツリービュー
        columns = ('timestamp', 'action', 'record_id', 'editor', 'reason')
        tree = ttk.Treeview(dialog, columns=columns, show='headings')

        tree.heading('timestamp', text='日時')
        tree.heading('action', text='操作')
        tree.heading('record_id', text='レコードID')
        tree.heading('editor', text='編集者')
        tree.heading('reason', text='理由')

        tree.column('timestamp', width=150)
        tree.column('action', width=80)
        tree.column('record_id', width=200)
        tree.column('editor', width=100)
        tree.column('reason', width=250)

        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # ログを追加
        for log in logs:
            timestamp = log.get('timestamp', '')[:19]
            action = log.get('action', '')
            record_id = log.get('record_id', '')
            editor = log.get('editor', '')
            reason = log.get('reason', '')

            tree.insert('', 'end', values=(timestamp, action, record_id, editor, reason))

    def on_closing(self):
        """ウィンドウクローズ時の処理"""
        try:
            logger.info("アプリケーション終了処理開始")

            # 自動休憩設定を保存
            self.save_auto_break_config()

            # アイドル監視を停止
            if self.auto_break_enabled:
                self.idle_monitor.stop_monitoring()
                logger.info("アイドル監視を停止しました")

            logger.info("アプリケーション正常終了")
        except Exception as e:
            log_exception(logger, "終了処理エラー", e)
        finally:
            # ウィンドウを閉じる
            self.root.destroy()

    def on_project_settings_account_selected(self, event=None):
        """プロジェクト設定のアカウント選択時の処理"""
        self.refresh_project_settings()

    def refresh_project_settings(self):
        """プロジェクト設定の一覧を更新"""
        account = self.project_settings_account_var.get()
        if not account:
            # アカウント一覧を更新
            accounts = self.tc.list_accounts()
            self.project_settings_account_combo['values'] = accounts
            if accounts:
                self.project_settings_account_var.set(accounts[0])
                account = accounts[0]
            else:
                return

        # Treeviewをクリア
        for item in self.project_settings_tree.get_children():
            self.project_settings_tree.delete(item)

        # プロジェクト一覧を取得
        projects = self.tc.list_projects(account)

        # 各プロジェクトの設定を表示
        for project in projects:
            is_main_job = self.tc.storage.get_project_main_job_flag(account, project)
            git_repo_path = self.tc.storage.get_project_git_repo_path(account, project)
            self.project_settings_tree.insert(
                '',
                'end',
                values=(project, "はい" if is_main_job else "いいえ", git_repo_path or "（未設定）")
            )

    def toggle_project_main_job_flag(self, event=None):
        """プロジェクトの本職フラグを切り替え"""
        selection = self.project_settings_tree.selection()
        if not selection:
            return

        account = self.project_settings_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # 選択された行の情報を取得
        item = selection[0]
        values = self.project_settings_tree.item(item, 'values')
        project = values[0]
        current_is_main_job = values[1] == "はい"
        git_repo_path = values[2] if len(values) > 2 else "（未設定）"

        # フラグを反転
        new_is_main_job = not current_is_main_job

        # 保存
        self.tc.storage.set_project_main_job_flag(account, project, new_is_main_job)

        # 表示を更新
        self.project_settings_tree.item(
            item,
            values=(project, "はい" if new_is_main_job else "いいえ", git_repo_path)
        )

        # メッセージを表示
        status_text = "本職の勤務時間に含める" if new_is_main_job else "本職の勤務時間に含めない"
        messagebox.showinfo(
            "設定を保存しました",
            f"プロジェクト「{project}」を {status_text} に設定しました"
        )

    def edit_project_git_path(self, event=None):
        """プロジェクトのGitリポジトリパスを編集"""
        from tkinter import filedialog

        selection = self.project_settings_tree.selection()
        if not selection:
            return

        account = self.project_settings_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # 選択された行の情報を取得
        item = selection[0]
        values = self.project_settings_tree.item(item, 'values')
        project = values[0]
        is_main_job_text = values[1]
        current_path = values[2] if len(values) > 2 and values[2] != "（未設定）" else ""

        # ダイアログで選択肢を提示
        dialog_result = messagebox.askquestion(
            "Gitリポジトリパスの設定",
            f"プロジェクト「{project}」のGitリポジトリパスを設定します。\n\n"
            f"現在のパス: {current_path or '（未設定）'}\n\n"
            f"ディレクトリを選択しますか？\n"
            f"「いいえ」を選択すると手動でパスを入力できます。",
            icon='question'
        )

        new_path = None
        if dialog_result == 'yes':
            # ディレクトリ選択ダイアログ
            new_path = filedialog.askdirectory(
                title=f"「{project}」のGitリポジトリディレクトリを選択",
                initialdir=current_path or str(Path.home())
            )
        else:
            # 手動入力
            new_path = simpledialog.askstring(
                "Gitリポジトリパスの入力",
                f"プロジェクト「{project}」のGitリポジトリパスを入力してください:\n"
                f"（空欄にすると設定を削除します）",
                initialvalue=current_path
            )

        if new_path is not None:  # キャンセルされていない
            # 空文字列の場合はNoneに変換
            if new_path.strip() == "":
                new_path = None

            # 保存
            self.tc.storage.set_project_git_repo_path(account, project, new_path)

            # 表示を更新
            self.project_settings_tree.item(
                item,
                values=(project, is_main_job_text, new_path or "（未設定）")
            )

            # メッセージを表示
            if new_path:
                messagebox.showinfo(
                    "設定を保存しました",
                    f"プロジェクト「{project}」のGitリポジトリパスを設定しました:\n{new_path}"
                )
            else:
                messagebox.showinfo(
                    "設定を削除しました",
                    f"プロジェクト「{project}」のGitリポジトリパス設定を削除しました"
                )

    def show_shift_hours_report(self, account):
        """シフト総労働時間管理レポートを表示"""
        # Treeviewをクリア
        for item in self.shift_hours_tree.get_children():
            self.shift_hours_tree.delete(item)

        # 全てのシフト総労働時間を取得
        all_shift_hours = self.tc.storage.get_all_shift_total_hours(account)

        # 各月の情報を取得して表示
        for period_key in sorted(all_shift_hours.keys(), reverse=True):
            year, month = map(int, period_key.split('-'))
            shift_hours = all_shift_hours[period_key]

            # 月の表示名
            period_display = f"{year}年{month:02d}月期"

            # Treeviewに追加
            self.shift_hours_tree.insert(
                '',
                'end',
                values=(
                    period_display,
                    f"{shift_hours:.1f}時間"
                )
            )

    def edit_shift_hours_from_tree(self, event):
        """Treeviewからダブルクリックで編集"""
        selection = self.shift_hours_tree.selection()
        if selection:
            self.edit_selected_shift_hours()

    def edit_selected_shift_hours(self):
        """選択した月のシフト総労働時間を編集"""
        selection = self.shift_hours_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "編集する月を選択してください")
            return

        # 選択された行の情報を取得
        item = selection[0]
        values = self.shift_hours_tree.item(item, 'values')
        period_display = values[0]  # "YYYY年MM月期"
        current_value = float(values[1].replace('時間', ''))

        # 年月を抽出
        year = int(period_display[:4])
        month = int(period_display[5:7])

        account = self.report_account_var.get()

        # 入力ダイアログ
        new_value = simpledialog.askfloat(
            "シフト総労働時間の編集",
            f"{period_display}のシフト総労働時間を入力してください（現在値: {current_value}時間）\n\n"
            f"※本職のシフト表に記載された総労働時間を入力してください。\n"
            f"  例：176時間",
            initialvalue=current_value,
            minvalue=0.0,
            maxvalue=1000.0
        )

        if new_value is not None:
            # 保存
            self.tc.storage.set_shift_total_hours(account, year, month, new_value)
            # 表示を更新
            self.show_report()

    def add_shift_hours_period(self):
        """新しい月のシフト総労働時間を追加"""
        account = self.report_account_var.get()
        if not account:
            messagebox.showerror("エラー", "アカウントを選択してください")
            return

        # 年月の入力
        period_str = simpledialog.askstring(
            "新しい月を追加",
            "追加する月を入力してください（YYYY-MM形式）\n例: 2025-11"
        )

        if not period_str:
            return

        try:
            year, month = map(int, period_str.split('-'))
            if month < 1 or month > 12:
                raise ValueError("月は1-12の範囲で指定してください")
        except ValueError as e:
            messagebox.showerror("エラー", f"無効な形式です: {e}")
            return

        # シフト総労働時間の入力
        hours = simpledialog.askfloat(
            "シフト総労働時間の入力",
            f"{year}年{month:02d}月期のシフト総労働時間を入力してください\n\n"
            f"※本職のシフト表に記載された総労働時間を入力してください。\n"
            f"  例：176時間",
            minvalue=0.0,
            maxvalue=1000.0
        )

        if hours is not None:
            # 保存
            self.tc.storage.set_shift_total_hours(account, year, month, hours)
            # 表示を更新
            self.show_report()


class HolidayInputDialog:
    """休日情報入力ダイアログ"""

    def __init__(self, parent, overtime_info, tc, account):
        """
        Args:
            parent: 親ウィンドウ
            overtime_info: 月間時間外労働情報の辞書
            tc: TimeClockインスタンス
            account: アカウント名
        """
        self.result = None
        self.tc = tc
        self.account = account
        self.overtime_info = overtime_info

        self.top = tk.Toplevel(parent)
        self.top.title("作業終了 - 休日情報")
        self.top.geometry("500x400")
        self.top.resizable(False, False)

        # モーダルに設定
        self.top.transient(parent)
        self.top.grab_set()

        # メインフレーム
        main_frame = ttk.Frame(self.top, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 月間時間外労働の情報表示
        info_frame = ttk.LabelFrame(main_frame, text="月間時間外労働（60時間計算用）", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        period_label = ttk.Label(
            info_frame,
            text=f"集計期間: {overtime_info['period_start']} ～ {overtime_info['period_end']}",
            font=("", 10)
        )
        period_label.pack(anchor=tk.W, pady=(0, 5))

        # アプリで記録した時間
        app_hours = overtime_info['total_for_60h_calc_hours']
        app_text = f"アプリ記録: {app_hours:.1f}時間\n"
        app_text += f"  ├ 法定時間外労働: {overtime_info['total_overtime_hours']:.1f}時間\n"
        app_text += f"  └ 法定休日労働: {overtime_info['legal_holiday_work_hours']:.1f}時間"

        app_label = ttk.Label(
            info_frame,
            text=app_text,
            font=("", 9)
        )
        app_label.pack(anchor=tk.W, pady=(0, 5))

        # 会社打刻実績
        company_frame = ttk.Frame(info_frame)
        company_frame.pack(fill=tk.X, pady=(0, 5))

        company_hours = overtime_info['company_overtime_hours']
        company_text = f"会社打刻実績: {company_hours:.1f}時間"
        if company_hours == 0:
            company_text += " （未設定）"

        self.company_label = ttk.Label(
            company_frame,
            text=company_text,
            font=("", 9),
            foreground="blue" if company_hours > 0 else "gray"
        )
        self.company_label.pack(side=tk.LEFT)

        edit_company_button = ttk.Button(
            company_frame,
            text="編集",
            command=self.edit_company_overtime,
            width=6
        )
        edit_company_button.pack(side=tk.LEFT, padx=(10, 0))

        # 合算時間
        combined_hours = overtime_info['combined_overtime_hours']
        combined_text = f"合計: {combined_hours:.1f}時間"
        if combined_hours > 60:
            combined_text += f" （60時間超過: {combined_hours - 60:.1f}時間）"
            combined_color = "red"
        elif combined_hours > 50:
            combined_text += " （60時間に接近中）"
            combined_color = "orange"
        else:
            combined_color = "black"

        self.combined_label = ttk.Label(
            info_frame,
            text=combined_text,
            font=("", 11, "bold"),
            foreground=combined_color
        )
        self.combined_label.pack(anchor=tk.W, pady=(5, 0))

        # 説明
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(0, 15))

        note_label = ttk.Label(
            note_frame,
            text="※ 月60時間を超える時間外労働には50%の割増率が適用されます\n"
                 "※ 深夜労働（22:00～5:00）には25%の割増率が加算されます",
            font=("", 9),
            foreground="gray"
        )
        note_label.pack(anchor=tk.W)

        # 休日チェックボックス
        checkbox_frame = ttk.LabelFrame(main_frame, text="本日の勤務区分", padding="10")
        checkbox_frame.pack(fill=tk.X, pady=(0, 15))

        self.is_holiday_var = tk.BooleanVar(value=False)
        self.is_legal_holiday_var = tk.BooleanVar(value=False)

        holiday_cb = ttk.Checkbutton(
            checkbox_frame,
            text="休日勤務",
            variable=self.is_holiday_var,
            command=self.on_holiday_change
        )
        holiday_cb.pack(anchor=tk.W, pady=(0, 5))

        legal_holiday_cb = ttk.Checkbutton(
            checkbox_frame,
            text="法定休日勤務（35%割増、60時間計算に含まれない）",
            variable=self.is_legal_holiday_var,
            command=self.on_legal_holiday_change
        )
        legal_holiday_cb.pack(anchor=tk.W)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ok_button = ttk.Button(
            button_frame,
            text="確定",
            command=self.ok
        )
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_button = ttk.Button(
            button_frame,
            text="キャンセル",
            command=self.cancel
        )
        cancel_button.pack(side=tk.RIGHT)

        # Enterキーで確定
        self.top.bind('<Return>', lambda e: self.ok())
        # Escapeキーでキャンセル
        self.top.bind('<Escape>', lambda e: self.cancel())

        # ウィンドウを中央に配置
        self.top.update_idletasks()
        x = (self.top.winfo_screenwidth() // 2) - (self.top.winfo_width() // 2)
        y = (self.top.winfo_screenheight() // 2) - (self.top.winfo_height() // 2)
        self.top.geometry(f"+{x}+{y}")

    def edit_company_overtime(self):
        """会社打刻実績を編集"""
        current_value = self.overtime_info['company_overtime_hours']

        # 入力ダイアログ
        new_value = simpledialog.askfloat(
            "会社打刻実績の編集",
            f"会社での打刻実績（時間外労働時間）を入力してください。\n"
            f"対象期間: {self.overtime_info['period_start']} ～ {self.overtime_info['period_end']}\n"
            f"（{self.overtime_info['year']}年{self.overtime_info['month']}月期）",
            initialvalue=current_value,
            minvalue=0.0,
            maxvalue=500.0,
            parent=self.top
        )

        if new_value is not None:
            # 会社打刻実績を保存
            self.tc.set_company_overtime(
                self.account,
                self.overtime_info['year'],
                self.overtime_info['month'],
                new_value
            )

            # overtime_infoを更新
            self.overtime_info = self.tc.get_monthly_overtime_hours(self.account)

            # 表示を更新
            self.update_overtime_display()

    def update_overtime_display(self):
        """時間外労働表示を更新"""
        # 会社打刻実績の表示を更新
        company_hours = self.overtime_info['company_overtime_hours']
        company_text = f"会社打刻実績: {company_hours:.1f}時間"
        if company_hours == 0:
            company_text += " （未設定）"

        self.company_label.config(
            text=company_text,
            foreground="blue" if company_hours > 0 else "gray"
        )

        # 合算時間の表示を更新
        combined_hours = self.overtime_info['combined_overtime_hours']
        combined_text = f"合計: {combined_hours:.1f}時間"
        if combined_hours > 60:
            combined_text += f" （60時間超過: {combined_hours - 60:.1f}時間）"
            combined_color = "red"
        elif combined_hours > 50:
            combined_text += " （60時間に接近中）"
            combined_color = "orange"
        else:
            combined_color = "black"

        self.combined_label.config(
            text=combined_text,
            foreground=combined_color
        )

    def on_holiday_change(self):
        """休日チェックボックスの変更時"""
        if self.is_holiday_var.get():
            # 休日にチェックを入れたら、法定休日を解除
            pass
        else:
            # 休日のチェックを外したら、法定休日も解除
            self.is_legal_holiday_var.set(False)

    def on_legal_holiday_change(self):
        """法定休日チェックボックスの変更時"""
        if self.is_legal_holiday_var.get():
            # 法定休日にチェックを入れたら、休日も自動的にチェック
            self.is_holiday_var.set(True)

    def ok(self):
        """確定ボタン"""
        self.result = {
            'is_holiday': self.is_holiday_var.get(),
            'is_legal_holiday': self.is_legal_holiday_var.get()
        }
        self.top.destroy()

    def cancel(self):
        """キャンセルボタン"""
        self.result = None
        self.top.destroy()


def main():
    logger.info("main() 関数開始")
    root = tk.Tk()
    app = TimeClockGUI(root)
    logger.info("mainloop() 開始")
    root.mainloop()


if __name__ == '__main__':
    main()
