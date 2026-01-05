#!/usr/bin/env python3
"""
Professional Daily Journal / Diary App
Author: ChatGPT
Dark Theme UI • Login/Register • SQLite • Export CSV • Search • Edit Entries
"""

import sqlite3
import hashlib
import csv
from datetime import datetime
from tkinter import messagebox, filedialog

import customtkinter as ctk

DB_NAME = "journal.db"

# ===== DATABASE SETUP =====
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ===== MAIN APP =====
class DiaryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Professional Diary App")
        self.geometry("1100x650")

        init_db()
        self.user_id = None

        self.show_login_page()

    # ---------------- LOGIN PAGE ----------------
    def show_login_page(self):
        self.clear_frame()
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(pady=80)

        ctk.CTkLabel(self.login_frame, text="Login", font=("Arial", 24)).pack(pady=10)

        self.username_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Username")
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Password", show="•")
        self.password_entry.pack(pady=10)

        ctk.CTkButton(self.login_frame, text="Login", command=self.login).pack(pady=5)
        ctk.CTkButton(self.login_frame, text="Register", fg_color="gray", command=self.show_register_page).pack()

    def login(self):
        username = self.username_entry.get()
        password = hash_password(self.password_entry.get())

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        data = cur.fetchone()
        conn.close()

        if data:
            self.user_id = data[0]
            self.show_dashboard()
        else:
            messagebox.showerror("Error", "Invalid credentials!")

    # ---------------- REGISTER PAGE ----------------
    def show_register_page(self):
        self.clear_frame()
        self.register_frame = ctk.CTkFrame(self)
        self.register_frame.pack(pady=80)

        ctk.CTkLabel(self.register_frame, text="Register", font=("Arial", 24)).pack(pady=10)

        self.reg_user = ctk.CTkEntry(self.register_frame, placeholder_text="New Username")
        self.reg_user.pack(pady=10)

        self.reg_pass = ctk.CTkEntry(self.register_frame, placeholder_text="New Password", show="•")
        self.reg_pass.pack(pady=10)

        ctk.CTkButton(self.register_frame, text="Create Account", command=self.register_user).pack(pady=5)
        ctk.CTkButton(self.register_frame, text="Back to Login", fg_color="gray",
                      command=self.show_login_page).pack()

    def register_user(self):
        username = self.reg_user.get()
        password = hash_password(self.reg_pass.get())

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            messagebox.showinfo("Success", "Account created! Please login.")
            self.show_login_page()
        except:
            messagebox.showerror("Error", "Username already exists!")
        conn.close()

    # ---------------- DASHBOARD ----------------
    def show_dashboard(self):
        self.clear_frame()

        # Sidebar
        sidebar = ctk.CTkFrame(self, width=200)
        sidebar.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkButton(sidebar, text="Add Entry", command=self.add_entry).pack(pady=10)
        ctk.CTkButton(sidebar, text="Update Entry", command=self.update_entry).pack(pady=10)
        ctk.CTkButton(sidebar, text="Delete Entry", command=self.delete_entry).pack(pady=10)
        ctk.CTkButton(sidebar, text="Export CSV", fg_color="purple", command=self.export_csv).pack(pady=10)
        ctk.CTkButton(sidebar, text="Logout", fg_color="red", command=self.show_login_page).pack(side="bottom", pady=20)

        # Right panel with Search + List + Editor
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, pady=5)

        self.search_entry = ctk.CTkEntry(right_frame, placeholder_text="Search entries...")
        self.search_entry.pack(fill="x", padx=10, pady=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_entries())

        display_frame = ctk.CTkFrame(right_frame)
        display_frame.pack(fill="both", expand=True)

        self.entries_list = ctk.CTkTextbox(display_frame, width=350)
        self.entries_list.pack(side="right", fill="y")

        self.entries_list.bind("<ButtonRelease-1>", self.load_selected_text)

        self.editor = ctk.CTkTextbox(display_frame)
        self.editor.pack(side="left", fill="both", expand=True)

        self.load_entries()

    def load_entries(self):
        search = self.search_entry.get().lower()
        self.entries_list.delete("0.0", "end")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id, date, content FROM entries WHERE user_id=? ORDER BY id DESC", (self.user_id,))
        rows = cur.fetchall()
        conn.close()

        self.entries = [r for r in rows if search in r[2].lower() or search in r[1].lower()]

        for entry in self.entries:
            self.entries_list.insert("end", f"{entry[0]} • {entry[1]}\n{entry[2][:60]}...\n\n")

    def load_selected_text(self, event):
        try:
            selected = self.entries_list.get("insert linestart", "insert lineend")
            entry_id = selected.split("•")[0].strip()
            if not entry_id.isdigit():
                return

            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT content FROM entries WHERE id=?", (entry_id,))
            data = cur.fetchone()
            conn.close()

            if data:
                self.editor.delete("0.0", "end")
                self.editor.insert("0.0", data[0])
                self.current_edit_id = entry_id
        except:
            pass

    def add_entry(self):
        content = self.editor.get("0.0", "end").strip()
        if not content:
            return

        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO entries (user_id, date, content) VALUES (?,?,?)",
                    (self.user_id, date, content))
        conn.commit()
        conn.close()

        self.editor.delete("0.0", "end")
        self.load_entries()

    def update_entry(self):
        if not hasattr(self, "current_edit_id"):
            messagebox.showwarning("Warning", "Select an entry first!")
            return

        content = self.editor.get("0.0", "end").strip()
        if not content:
            messagebox.showerror("Error", "Content cannot be empty")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE entries SET content=? WHERE id=? AND user_id=?",
                    (content, self.current_edit_id, self.user_id))
        conn.commit()
        conn.close()

        messagebox.showinfo("Updated", "Entry updated successfully!")
        self.load_entries()

    def delete_entry(self):
        selected = self.entries_list.get("insert linestart", "insert lineend")
        if not selected.strip():
            messagebox.showerror("Error", "Select a line where an entry is shown")
            return

        entry_id = selected.split("•")[0].strip()

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, self.user_id))
        conn.commit()
        conn.close()

        self.editor.delete("0.0", "end")
        self.load_entries()

    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV Files", "*.csv")])
        if not file:
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT date, content FROM entries WHERE user_id=?", (self.user_id,))
        rows = cur.fetchall()
        conn.close()

        with open(file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Content"])
            writer.writerows(rows)

        messagebox.showinfo("Exported", "Entries successfully exported!")

    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()


# ===== RUN APP =====
if __name__ == "__main__":
    app = DiaryApp()
    app.mainloop()
