"""
Git インポートダイアログ
GUIからGitコミット履歴をインポートするためのダイアログ
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
from git_import import GitCommitImporter
from storage import Storage


class GitImportDialog:
    """Gitコミット履歴インポートダイアログ"""

    def __init__(self, parent, account: str, storage: Storage):
        """
        Args:
            parent: 親ウィンドウ
            account: 社員番号
            storage: Storageインスタンス
        """
        self.parent = parent
        self.account = account
        self.storage = storage
        self.importer = GitCommitImporter(storage)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gitコミット履歴インポート")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.csv_file = None
        self.preview_sessions = []

        self.setup_ui()

    def setup_ui(self):
        """UIを構築"""
        # ダークモード対応（親ウィンドウの色を継承）
        if hasattr(self.parent, 'colors'):
            colors = self.parent.colors
            self.dialog.configure(bg=colors['bg'])
        else:
            colors = {
                'bg': '#1e1e1e',
                'fg': '#e0e0e0',
                'bg_light': '#2d2d2d',
                'accent': '#007acc'
            }
            self.dialog.configure(bg=colors['bg'])

        # メインフレーム
        main_frame = tk.Frame(self.dialog, bg=colors['bg'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        title_label = tk.Label(
            main_frame,
            text="Gitコミット履歴インポート",
            font=('Arial', 16, 'bold'),
            bg=colors['bg'],
            fg=colors['fg']
        )
        title_label.pack(pady=(0, 20))

        # 説明
        desc_text = (
            "git_work_time_estimator.py で生成したCSVファイルを選択してください。\n"
            "コミット履歴が作業セッションとしてインポートされます。"
        )
        desc_label = tk.Label(
            main_frame,
            text=desc_text,
            bg=colors['bg'],
            fg=colors['fg'],
            justify=tk.LEFT,
            wraplength=600
        )
        desc_label.pack(pady=(0, 20))

        # ファイル選択エリア
        file_frame = tk.Frame(main_frame, bg=colors['bg'])
        file_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            file_frame,
            text="CSVファイル:",
            bg=colors['bg'],
            fg=colors['fg'],
            width=15,
            anchor='w'
        ).pack(side=tk.LEFT)

        self.file_entry = tk.Entry(
            file_frame,
            bg=colors['bg_light'],
            fg=colors['fg'],
            insertbackground=colors['fg']
        )
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            file_frame,
            text="参照...",
            command=self.browse_file,
            bg=colors['accent'],
            fg='white',
            relief=tk.FLAT,
            padx=15
        )
        browse_btn.pack(side=tk.LEFT)

        # オプション設定エリア
        options_frame = tk.LabelFrame(
            main_frame,
            text="インポート設定",
            bg=colors['bg'],
            fg=colors['fg'],
            padx=10,
            pady=10
        )
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # セッション分割間隔
        gap_frame = tk.Frame(options_frame, bg=colors['bg'])
        gap_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            gap_frame,
            text="セッション分割間隔:",
            bg=colors['bg'],
            fg=colors['fg'],
            width=20,
            anchor='w'
        ).pack(side=tk.LEFT)

        self.gap_spinbox = tk.Spinbox(
            gap_frame,
            from_=30,
            to=480,
            increment=30,
            width=10,
            bg=colors['bg_light'],
            fg=colors['fg']
        )
        self.gap_spinbox.delete(0, tk.END)
        self.gap_spinbox.insert(0, "120")
        self.gap_spinbox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(
            gap_frame,
            text="分",
            bg=colors['bg'],
            fg=colors['fg']
        ).pack(side=tk.LEFT)

        tk.Label(
            gap_frame,
            text="（この時間以上空いたら別セッション）",
            bg=colors['bg'],
            fg=colors['fg'],
            font=('Arial', 8)
        ).pack(side=tk.LEFT, padx=(10, 0))

        # 既存データの扱い
        self.skip_existing_var = tk.BooleanVar(value=True)
        skip_check = tk.Checkbutton(
            options_frame,
            text="既存の手動入力データがある日はスキップする",
            variable=self.skip_existing_var,
            bg=colors['bg'],
            fg=colors['fg'],
            selectcolor=colors['bg_light'],
            activebackground=colors['bg'],
            activeforeground=colors['fg']
        )
        skip_check.pack(anchor='w', pady=5)

        # プレビューボタン
        preview_btn = tk.Button(
            main_frame,
            text="プレビュー",
            command=self.preview_import,
            bg=colors['accent'],
            fg='white',
            relief=tk.FLAT,
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=5
        )
        preview_btn.pack(pady=(0, 10))

        # プレビュー表示エリア
        preview_frame = tk.LabelFrame(
            main_frame,
            text="プレビュー",
            bg=colors['bg'],
            fg=colors['fg']
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # スクロール可能なテキストエリア
        preview_scroll = tk.Scrollbar(preview_frame)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.preview_text = tk.Text(
            preview_frame,
            bg=colors['bg_light'],
            fg=colors['fg'],
            insertbackground=colors['fg'],
            yscrollcommand=preview_scroll.set,
            wrap=tk.WORD,
            height=15
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        preview_scroll.config(command=self.preview_text.yview)

        # ボタンエリア
        button_frame = tk.Frame(main_frame, bg=colors['bg'])
        button_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            button_frame,
            text="キャンセル",
            command=self.dialog.destroy,
            bg=colors['bg_light'],
            fg=colors['fg'],
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.import_btn = tk.Button(
            button_frame,
            text="インポート実行",
            command=self.execute_import,
            bg='#4ec9b0',
            fg='white',
            relief=tk.FLAT,
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=5,
            state=tk.DISABLED
        )
        self.import_btn.pack(side=tk.RIGHT)

    def browse_file(self):
        """ファイル選択ダイアログを開く"""
        filename = filedialog.askopenfilename(
            parent=self.dialog,
            title="CSVファイルを選択",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir=str(Path.cwd())
        )

        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.csv_file = filename

    def preview_import(self):
        """インポート内容をプレビュー"""
        csv_file = self.file_entry.get().strip()

        if not csv_file:
            messagebox.showwarning(
                "ファイル未選択",
                "CSVファイルを選択してください",
                parent=self.dialog
            )
            return

        if not Path(csv_file).exists():
            messagebox.showerror(
                "ファイルエラー",
                "指定されたファイルが見つかりません",
                parent=self.dialog
            )
            return

        try:
            max_gap = int(self.gap_spinbox.get())

            # プレビュー実行
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', "読み込み中...\n")
            self.dialog.update()

            commits = self.importer.load_git_commits_csv(csv_file)
            commits = sorted(commits, key=lambda x: x['datetime'])
            self.preview_sessions = self.importer.group_commits_by_session(commits, max_gap)

            # プレビューテキスト生成
            preview_text = []
            preview_text.append(f"【インポート対象: {len(self.preview_sessions)} セッション】\n")
            preview_text.append(f"社員番号: {self.account}\n")
            preview_text.append(f"セッション分割間隔: {max_gap} 分\n")
            preview_text.append("=" * 60 + "\n\n")

            total_minutes = 0

            for i, session in enumerate(self.preview_sessions, 1):
                date_str = session['date'].strftime('%Y-%m-%d (%a)')
                start_str = session['start_time'].strftime('%H:%M')
                end_str = session['last_commit_time'].strftime('%H:%M')

                preview_text.append(f"{i}. {date_str}  {start_str} - {end_str}\n")
                preview_text.append(f"   プロジェクト: {session['project']}\n")
                preview_text.append(f"   作業時間: {session['total_minutes']:.0f} 分\n")
                preview_text.append(f"   コミット数: {len(session['commits'])}\n")

                # フラグ表示
                flags = []
                if session['is_overtime']:
                    flags.append('🕐時間外')
                if session['is_weekend']:
                    flags.append('📅休日')
                if session['is_late_night']:
                    flags.append('🌙深夜')
                if flags:
                    preview_text.append(f"   フラグ: {' '.join(flags)}\n")

                # コミット詳細（最初の3つ）
                preview_text.append("   コミット:\n")
                for commit in session['commits'][:3]:
                    msg = commit['message'][:60]
                    preview_text.append(f"     [{commit['commit_id']}] {msg}\n")

                if len(session['commits']) > 3:
                    preview_text.append(f"     ... 他 {len(session['commits']) - 3} 件\n")

                preview_text.append("\n")
                total_minutes += session['total_minutes']

            preview_text.append("=" * 60 + "\n")
            preview_text.append(f"合計作業時間: {total_minutes:.0f} 分 ({total_minutes/60:.1f} 時間)\n")

            # テキストエリアに表示
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', ''.join(preview_text))

            # インポートボタンを有効化
            self.import_btn.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror(
                "プレビューエラー",
                f"プレビューの生成に失敗しました:\n{str(e)}",
                parent=self.dialog
            )
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', f"エラー: {str(e)}")

    def execute_import(self):
        """インポートを実行"""
        if not self.preview_sessions:
            messagebox.showwarning(
                "プレビュー未実行",
                "先にプレビューボタンを押してください",
                parent=self.dialog
            )
            return

        # 確認ダイアログ
        result = messagebox.askyesno(
            "インポート確認",
            f"{len(self.preview_sessions)} セッションをインポートします。\n"
            f"よろしいですか？",
            parent=self.dialog
        )

        if not result:
            return

        try:
            csv_file = self.file_entry.get().strip()
            max_gap = int(self.gap_spinbox.get())
            skip_existing = self.skip_existing_var.get()

            # インポート実行
            stats = self.importer.import_commits_to_account(
                csv_file,
                self.account,
                max_gap_minutes=max_gap,
                skip_existing=skip_existing
            )

            # 統計を保存
            self.importer.export_statistics()

            # 成功メッセージ
            messagebox.showinfo(
                "インポート完了",
                f"インポートが完了しました。\n\n"
                f"インポート件数: {stats['total_imported']}\n"
                f"スキップ件数: {stats['skipped_duplicates']}\n"
                f"総作業時間: {stats['total_work_minutes']} 分 "
                f"({stats['total_work_minutes']/60:.1f} 時間)",
                parent=self.dialog
            )

            # ダイアログを閉じる
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror(
                "インポートエラー",
                f"インポートに失敗しました:\n{str(e)}",
                parent=self.dialog
            )


def show_git_import_dialog(parent, account: str, storage: Storage):
    """Gitインポートダイアログを表示（外部から呼び出し用）"""
    GitImportDialog(parent, account, storage)
