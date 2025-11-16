#!/usr/bin/env python3
"""
打刻システム GUI アプリケーション
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
from pathlib import Path
from timeclock import TimeClock
from config_manager import ConfigManager
from idle_monitor import IdleMonitor
from logger import get_logger, log_exception
import sys

# ロガーの初期化
logger = get_logger(__name__)


class TimeClockGUI:
    def __init__(self, root):
        try:
            logger.info("GUI初期化開始")
            self.root = root
            self.root.title("打刻システム")
            self.root.geometry("900x650")  # コンパクトなサイズ

            # 最小サイズを設定
            self.root.minsize(800, 600)

            # ダークモードの色設定
            self.setup_dark_theme()

            self.tc = TimeClock()
            self.config_manager = ConfigManager()

            # 設定の読み込み
            self.load_auto_break_config()

            # アイドル監視機能の初期化
            self.idle_monitor = IdleMonitor(
                idle_threshold_minutes=self.auto_break_threshold,
                check_interval_seconds=30
            )

            # メインフレームの作成
            self.create_widgets()

            # 初期状態の更新
            self.update_status()

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

    def setup_dark_theme(self):
        """ダークモードのテーマを設定"""
        # ダークモードの色定義
        self.colors = {
            'bg': '#1e1e1e',           # 背景色（濃いグレー）
            'fg': '#e0e0e0',           # 文字色（明るいグレー）
            'bg_light': '#2d2d2d',     # 少し明るい背景
            'bg_dark': '#181818',      # より暗い背景
            'accent': '#007acc',       # アクセントカラー（青）
            'accent_hover': '#005a9e', # ホバー時のアクセント
            'success': '#4ec9b0',      # 成功（緑がかった青）
            'warning': '#ce9178',      # 警告（オレンジ）
            'error': '#f48771',        # エラー（赤）
            'border': '#3e3e3e',       # ボーダー色
        }

        # tkinterのスタイル設定
        self.root.configure(bg=self.colors['bg'])

        # ttkスタイルの設定
        style = ttk.Style()
        style.theme_use('clam')  # clamテーマをベースに

        # 全体の背景色とフォント
        style.configure('.',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       fieldbackground=self.colors['bg_light'],
                       bordercolor=self.colors['border'],
                       darkcolor=self.colors['bg_dark'],
                       lightcolor=self.colors['bg_light'])

        # Notebookのスタイル
        style.configure('TNotebook',
                       background=self.colors['bg'],
                       borderwidth=0,
                       tabmargins=0)

        # タブのレイアウトを設定して、選択時のサイズ変更を防ぐ
        style.layout('TNotebook.Tab', [
            ('Notebook.tab', {
                'sticky': 'nswe',
                'children': [
                    ('Notebook.padding', {
                        'side': 'top',
                        'sticky': 'nswe',
                        'children': [
                            ('Notebook.label', {'side': 'top', 'sticky': ''})
                        ]
                    })
                ]
            })
        ])

        # タブのスタイル（自然なバランスのサイズに固定）
        style.configure('TNotebook.Tab',
                       background=self.colors['bg_light'],
                       foreground=self.colors['fg'],
                       padding=[20, 6],  # 横20、縦6で自然なバランス
                       borderwidth=0)

        # 選択状態でも同じパディングを維持（色だけ変更）
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['accent']), ('!selected', self.colors['bg_light'])],
                 foreground=[('selected', '#ffffff'), ('!selected', self.colors['fg'])],
                 padding=[('selected', [20, 6]), ('!selected', [20, 6])])

        # Frameのスタイル
        style.configure('TFrame', background=self.colors['bg'])

        # LabelFrameのスタイル
        style.configure('TLabelframe',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       bordercolor=self.colors['border'])
        style.configure('TLabelframe.Label',
                       background=self.colors['bg'],
                       foreground=self.colors['accent'])

        # Labelのスタイル
        style.configure('TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'])

        # Buttonのスタイル
        style.configure('TButton',
                       background=self.colors['accent'],
                       foreground='#ffffff',
                       borderwidth=1,
                       focuscolor=self.colors['accent'],
                       padding=[10, 5])
        style.map('TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('pressed', self.colors['bg_dark'])])

        # Entryのスタイル
        style.configure('TEntry',
                       fieldbackground=self.colors['bg_light'],
                       foreground=self.colors['fg'],
                       insertcolor=self.colors['fg'],
                       bordercolor=self.colors['border'])

        # Comboboxのスタイル
        style.configure('TCombobox',
                       fieldbackground=self.colors['bg_light'],
                       background=self.colors['bg_light'],
                       foreground=self.colors['fg'],
                       arrowcolor=self.colors['fg'],
                       bordercolor=self.colors['border'])

        # Checkbuttonのスタイル
        style.configure('TCheckbutton',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'])

        # Radiobuttonのスタイル
        style.configure('TRadiobutton',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'])

        # Treeviewのスタイル
        style.configure('Treeview',
                       background=self.colors['bg_light'],
                       foreground=self.colors['fg'],
                       fieldbackground=self.colors['bg_light'],
                       bordercolor=self.colors['border'])
        style.configure('Treeview.Heading',
                       background=self.colors['bg_dark'],
                       foreground=self.colors['accent'],
                       borderwidth=1)
        style.map('Treeview',
                 background=[('selected', self.colors['accent'])])

        # Scrollbarのスタイル
        style.configure('Vertical.TScrollbar',
                       background=self.colors['bg_light'],
                       troughcolor=self.colors['bg_dark'],
                       bordercolor=self.colors['border'],
                       arrowcolor=self.colors['fg'])

        logger.info("ダークモードを適用しました")

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
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="打刻")

        # 現在の状態表示エリア
        status_group = ttk.LabelFrame(main_frame, text="現在の状態", padding=10)
        status_group.pack(fill=tk.X, padx=10, pady=10)

        self.status_text = scrolledtext.ScrolledText(status_group, height=8, width=70)
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

        # プロジェクト選択
        ttk.Label(start_group, text="プロジェクト:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(start_group, textvariable=self.project_var, width=30)
        self.project_combo.grid(row=1, column=1, padx=5, pady=5)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)

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

        self.report_text = scrolledtext.ScrolledText(result_group, height=15, width=70)
        self.report_text.pack(fill=tk.BOTH, expand=True)
        self.report_text.config(state=tk.DISABLED)

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
        ttk.Label(hours_frame, text="（時間外労働時間計算の基準）", font=('', 8), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))

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
        if report_type == "project":
            # プロジェクト選択を表示
            self.project_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
            self.report_project_combo.grid(row=2, column=1, padx=5, pady=5)
        else:
            # プロジェクト選択を非表示
            self.project_label.grid_forget()
            self.report_project_combo.grid_forget()

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
            session = self.tc.end_work(account)
            total_hours = session['total_minutes'] / 60
            messagebox.showinfo("作業終了",
                              f"作業を終了しました\n{session['account']} - {session['project']}\n"
                              f"作業時間: {session['total_minutes']}分 ({total_hours:.2f}時間)")
            self.update_status()
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

        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete(1.0, tk.END)

        try:
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
            elif report_type == "project":
                project = self.report_project_var.get()
                if not project:
                    messagebox.showerror("エラー", "プロジェクトを選択してください")
                    return
                summary = self.tc.get_project_summary(account, project)
                report = self.format_project_report(summary)

            self.report_text.insert(tk.END, report)
        except Exception as e:
            messagebox.showerror("エラー", str(e))

        self.report_text.config(state=tk.DISABLED)

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
        lines.append(f"\n総作業時間: {self.format_time(summary['total_minutes'])} ({summary['total_hours']:.2f}時間)")
        lines.append(f"標準労働時間: {self.format_time(summary['standard_total_minutes'])} ({summary['standard_total_hours']:.2f}時間)")

        if summary['total_overtime_minutes'] > 0:
            lines.append(f"総時間外労働時間: {self.format_time(summary['total_overtime_minutes'])} ({summary['total_overtime_hours']:.2f}時間)")
        else:
            lines.append("総時間外労働時間: なし")

        if summary['project_stats']:
            lines.append("\n【プロジェクト別内訳】")
            for project, stats in sorted(summary['project_stats'].items()):
                lines.append(f"\n■ {project}")
                lines.append(f"  稼働日数: {stats['days_worked_count']}日")
                lines.append(f"  作業時間: {self.format_time(stats['total_minutes'])} ({stats['total_hours']:.2f}時間)")
                lines.append(f"  時間外労働時間: {self.format_time(stats['overtime_minutes'])} ({stats['overtime_hours']:.2f}時間)")

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


def main():
    root = tk.Tk()
    app = TimeClockGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
