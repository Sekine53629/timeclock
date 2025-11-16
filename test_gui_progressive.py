#!/usr/bin/env python3
"""
段階的なGUIテスト - どこまで表示されるか確認
"""
import tkinter as tk
from tkinter import ttk
import os

os.environ['TK_SILENCE_DEPRECATION'] = '1'

print("[TEST] スクリプト開始")

def test_stage_1():
    """ステージ1: 最小限のウィンドウとラベル"""
    print("\n=== ステージ1: 基本ウィンドウ + ラベル ===")
    root = tk.Tk()
    root.title("Stage 1: Basic Window")
    root.geometry("500x400")

    # 背景色を設定して表示確認
    root.configure(bg='lightblue')

    label = tk.Label(root, text="ステージ1: このテキストが見えますか？",
                     font=('Arial', 20), bg='yellow', fg='black')
    label.pack(pady=50)

    button = tk.Button(root, text="見えたらクリック → ステージ2へ",
                       command=lambda: [root.destroy(), test_stage_2()],
                       font=('Arial', 14))
    button.pack(pady=20)

    print("[TEST] ステージ1 mainloop 開始")
    root.mainloop()

def test_stage_2():
    """ステージ2: フレームとスクロールバー"""
    print("\n=== ステージ2: フレーム + スクロールバー ===")
    root = tk.Tk()
    root.title("Stage 2: Frame + Scrollbar")
    root.geometry("500x400")
    root.configure(bg='lightgreen')

    label = tk.Label(root, text="ステージ2: フレームとスクロールバー",
                     font=('Arial', 16), bg='white')
    label.pack(pady=10)

    # フレーム作成
    frame = tk.Frame(root, bg='white', relief=tk.SUNKEN, borderwidth=2)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # スクロールバー付きテキスト
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget = tk.Text(frame, yscrollcommand=scrollbar.set,
                          font=('Arial', 12), bg='lightyellow')
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    # テキスト追加
    for i in range(20):
        text_widget.insert(tk.END, f"行 {i+1}: このテキストが見えますか？スクロールできますか？\n")

    button = tk.Button(root, text="見えたらクリック → ステージ3へ",
                       command=lambda: [root.destroy(), test_stage_3()],
                       font=('Arial', 14))
    button.pack(pady=10)

    print("[TEST] ステージ2 mainloop 開始")
    root.mainloop()

def test_stage_3():
    """ステージ3: ダークモード風スタイル"""
    print("\n=== ステージ3: ダークモードスタイル ===")
    root = tk.Tk()
    root.title("Stage 3: Dark Style")
    root.geometry("500x400")

    # ダークモード色設定
    bg_color = '#2b2b2b'
    fg_color = '#ffffff'

    root.configure(bg=bg_color)

    label = tk.Label(root, text="ステージ3: ダークモードスタイル",
                     font=('Arial', 16), bg=bg_color, fg=fg_color)
    label.pack(pady=10)

    frame = tk.Frame(root, bg=bg_color)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget = tk.Text(frame, yscrollcommand=scrollbar.set,
                          font=('Arial', 12), bg='#1e1e1e', fg='#d4d4d4',
                          insertbackground='white')
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    for i in range(20):
        text_widget.insert(tk.END, f"行 {i+1}: ダークモードでテキストが見えますか？\n")

    button = tk.Button(root, text="完了",
                       command=root.destroy,
                       font=('Arial', 14), bg='#4a4a4a', fg='white')
    button.pack(pady=10)

    print("[TEST] ステージ3 mainloop 開始")
    root.mainloop()
    print("[TEST] テスト完了")

if __name__ == '__main__':
    print("[TEST] プログレッシブテスト開始")
    print("各ステージでウィジェットが見えるか確認してください")
    test_stage_1()
