#!/usr/bin/env python3
"""
最小限のGUIテスト
"""
import tkinter as tk

print("[DEBUG] Script started")

def main():
    print("[DEBUG] main() called")
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("400x300")

    label = tk.Label(root, text="Test Label", font=('Arial', 24))
    label.pack(pady=100)

    print("[DEBUG] Starting mainloop")
    root.mainloop()

if __name__ == '__main__':
    print("[DEBUG] __name__ ==", __name__)
    main()
