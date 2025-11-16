#!/usr/bin/env python3
"""
ttkウィジェットを通常のtkウィジェットに変換するスクリプト
macOS互換性のため
"""
import re

def convert_gui_file():
    with open('gui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # backup
    with open('gui.py.backup', 'w', encoding='utf-8') as f:
        f.write(content)

    print("バックアップ作成: gui.py.backup")

    # ttk.LabelFrame を tk.LabelFrame に変換（色設定付き）
    # padding=N を padx=N, pady=N に変換
    pattern = r'ttk\.LabelFrame\(([^,]+),\s*text="([^"]+)"(?:,\s*padding=(\d+))?\)'
    def replace_labelframe(match):
        parent = match.group(1)
        text = match.group(2)
        return f'tk.LabelFrame({parent}, text="{text}", bg=self.colors[\'bg\'], fg=self.colors[\'fg\'], padx=10, pady=10)'

    content = re.sub(pattern, replace_labelframe, content)

    # ttk.Frame を tk.Frame に変換
    pattern = r'ttk\.Frame\(([^,\)]+)(?:,\s*padding=\d+)?\)'
    def replace_frame(match):
        parent = match.group(1)
        return f'tk.Frame({parent}, bg=self.colors[\'bg\'])'

    content = re.sub(pattern, replace_frame, content)

    # ttk.Label を tk.Label に変換（色設定付き）
    pattern = r'ttk\.Label\(([^,]+),\s*text="([^"]+)"\)'
    def replace_label(match):
        parent = match.group(1)
        text = match.group(2)
        return f'tk.Label({parent}, text="{text}", bg=self.colors[\'bg\'], fg=self.colors[\'fg\'])'

    content = re.sub(pattern, replace_label, content)

    # ttk.Button を tk.Button に変換（色設定付き）
    pattern = r'ttk\.Button\('
    content = content.replace('ttk.Button(', 'tk.Button(')

    # ttk.Checkbutton を tk.Checkbutton に変換
    content = content.replace('ttk.Checkbutton(', 'tk.Checkbutton(')

    # ttk.Radiobutton を tk.Radiobutton に変換
    content = content.replace('ttk.Radiobutton(', 'tk.Radiobutton(')

    # ttk.Entry を tk.Entry に変換
    content = content.replace('ttk.Entry(', 'tk.Entry(')

    # ttk.Combobox はそのまま（tkにComboboxはない）

    # 結果を保存
    with open('gui.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("変換完了！")
    print("元のファイルは gui.py.backup に保存されています")

    # 変更内容を確認
    changes = sum(1 for a, b in zip(original_content.split('\n'), content.split('\n')) if a != b)
    print(f"変更された行数: {changes}")

if __name__ == '__main__':
    convert_gui_file()
