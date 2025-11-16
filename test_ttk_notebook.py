#!/usr/bin/env python3
"""
ttk.Notebookが表示されるかテスト
"""
import tkinter as tk
from tkinter import ttk
import os

os.environ['TK_SILENCE_DEPRECATION'] = '1'

print("[TEST] ttk.Notebook テスト開始")

root = tk.Tk()
root.title("ttk.Notebook Test")
root.geometry("600x400")
root.configure(bg='white')

# ttk.Notebookを作成
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# タブ1: 通常のtkウィジェット
tab1 = tk.Frame(notebook, bg='lightyellow')
notebook.add(tab1, text="Tab 1 (tk)")

label1 = tk.Label(tab1, text="これはTab 1です（通常のtkウィジェット）",
                  font=('Arial', 16), bg='lightyellow', fg='black')
label1.pack(pady=50)

button1 = tk.Button(tab1, text="ボタン1", font=('Arial', 14),
                    command=lambda: print("[TEST] ボタン1がクリックされました"))
button1.pack(pady=20)

# タブ2: 別のtkウィジェット
tab2 = tk.Frame(notebook, bg='lightblue')
notebook.add(tab2, text="Tab 2 (tk)")

label2 = tk.Label(tab2, text="これはTab 2です",
                  font=('Arial', 16), bg='lightblue', fg='black')
label2.pack(pady=50)

print("[TEST] ウィジェット作成完了")
print("[TEST] タブが見えますか？クリックできますか？")

root.mainloop()
print("[TEST] 終了")
