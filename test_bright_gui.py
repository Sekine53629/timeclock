#!/usr/bin/env python3
"""
明るい色で強制的に表示するテスト
"""
import tkinter as tk
import os

os.environ['TK_SILENCE_DEPRECATION'] = '1'

print("[TEST] 明るい色テスト開始")

root = tk.Tk()
root.title("明るい色テスト")
root.geometry("600x500")

# 強制的に明るい背景色
root.configure(bg='white')

# 大きな赤いラベル
label1 = tk.Label(root, text="赤いテキスト - 見えますか？",
                 font=('Arial', 24, 'bold'),
                 bg='white', fg='red')
label1.pack(pady=20)

# 大きな青いラベル
label2 = tk.Label(root, text="青いテキスト - 見えますか？",
                 font=('Arial', 24, 'bold'),
                 bg='white', fg='blue')
label2.pack(pady=20)

# 黄色い背景に黒文字
label3 = tk.Label(root, text="黒字に黄色背景 - 見えますか？",
                 font=('Arial', 24, 'bold'),
                 bg='yellow', fg='black')
label3.pack(pady=20)

# 大きなボタン
button = tk.Button(root, text="見えたらこのボタンをクリック",
                   font=('Arial', 18, 'bold'),
                   bg='green', fg='white',
                   command=lambda: print("[TEST] ボタンがクリックされました！"))
button.pack(pady=30)

# テキストエリア（明るい色）
text_frame = tk.Frame(root, bg='white')
text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

scrollbar = tk.Scrollbar(text_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

text_widget = tk.Text(text_frame,
                     font=('Arial', 14),
                     bg='lightyellow',
                     fg='black',
                     yscrollcommand=scrollbar.set)
text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=text_widget.yview)

# テキスト挿入
for i in range(20):
    text_widget.insert(tk.END, f"行 {i+1}: このテキストが見えますか？黒字に明るい黄色背景です。\n")

print("[TEST] ウィジェット作成完了")
root.update_idletasks()
root.update()
print("[TEST] mainloop 開始")

root.mainloop()
print("[TEST] 終了")
