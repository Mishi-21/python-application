#!/usr/bin/env python3
"""
diet_manager.py
Diet Plan Manager (Tkinter + SQLite)
Single-file proof-of-concept app with Admin and User sides.

Features:
 - Register / Login (admin flag)
 - Admin: manage users, diet plans, assign plans
 - User: view assigned plan, log meals, view logs
 - Uses sqlite3 for persistence. Passwords hashed with sha256.

Run:
    python diet_manager.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
import hashlib
from datetime import datetime, date
import os

DB_FILE = "diet_manager.db"

# -------------------------
# Database helpers
# -------------------------
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            email TEXT,
            is_admin INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS diet_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            target_calories INTEGER,
            created_by INTEGER,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plan_meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            day INTEGER,
            meal_type TEXT,
            meal_desc TEXT,
            calories INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_id INTEGER,
            start_date TEXT,
            end_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            meal_type TEXT,
            description TEXT,
            calories INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    return conn

def hash_password(passw: str) -> str:
    return hashlib.sha256(passw.encode("utf-8")).hexdigest()

# initialize DB and ensure at least one admin exists
def initialize_demo_data():
    conn = connect_db()
    cur = conn.cursor()
    # create default admin if none
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT OR IGNORE INTO users (username, password_hash, full_name, email, is_admin) VALUES (?, ?, ?, ?, ?)",
                    ("admin", hash_password("admin123"), "Administrator", "admin@example.com", 1))
    conn.commit()
    conn.close()

# -------------------------
# Data access functions
# -------------------------
def create_user(username, password, full_name="", email="", is_admin=0):
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash, full_name, email, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (username, hash_password(password), full_name, email, is_admin))
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def authenticate(username, password):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, email, is_admin, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    user_id, uname, full_name, email, is_admin, p_hash = row
    if hash_password(password) == p_hash:
        return {"id": user_id, "username": uname, "full_name": full_name, "email": email, "is_admin": bool(is_admin)}
    return None

def list_users():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, email, is_admin FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_user(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# Diet plans
def create_plan(name, description, target_calories, created_by):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO diet_plans (name, description, target_calories, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, description, target_calories, created_by, datetime.now().isoformat()))
    plan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def update_plan(plan_id, name, description, target_calories):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE diet_plans SET name=?, description=?, target_calories=? WHERE id=?", (name, description, target_calories, plan_id))
    conn.commit()
    conn.close()

def delete_plan(plan_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM plan_meals WHERE plan_id=?", (plan_id,))
    cur.execute("DELETE FROM diet_plans WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()

def list_plans():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, target_calories FROM diet_plans")
    rows = cur.fetchall()
    conn.close()
    return rows

# plan meals
def add_plan_meal(plan_id, day, meal_type, meal_desc, calories):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO plan_meals (plan_id, day, meal_type, meal_desc, calories) VALUES (?, ?, ?, ?, ?)",
                (plan_id, day, meal_type, meal_desc, calories))
    conn.commit()
    conn.close()

def list_plan_meals(plan_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, day, meal_type, meal_desc, calories FROM plan_meals WHERE plan_id=? ORDER BY day, meal_type", (plan_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_plan_meal(meal_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM plan_meals WHERE id=?", (meal_id,))
    conn.commit()
    conn.close()

# assign plan
def assign_plan_to_user(user_id, plan_id, start_date_str, end_date_str):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_plans (user_id, plan_id, start_date, end_date) VALUES (?, ?, ?, ?)",
                (user_id, plan_id, start_date_str, end_date_str))
    conn.commit()
    conn.close()

def get_user_plan(user_id, on_date=None):
    conn = connect_db()
    cur = conn.cursor()
    if not on_date:
        on_date = date.today().isoformat()
    cur.execute("SELECT up.id, dp.id, dp.name, dp.description, up.start_date, up.end_date FROM user_plans up JOIN diet_plans dp ON up.plan_id = dp.id WHERE up.user_id = ? AND date(?) BETWEEN date(up.start_date) AND date(up.end_date) LIMIT 1",
                (user_id, on_date))
    row = cur.fetchone()
    conn.close()
    return row  # (user_plan_id, plan_id, name, description, start, end) or None

# meal logs
def log_meal(user_id, meal_date, meal_type, description, calories):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO meal_logs (user_id, date, meal_type, description, calories, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, meal_date, meal_type, description, calories, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def list_meal_logs(user_id, from_date=None, to_date=None):
    conn = connect_db()
    cur = conn.cursor()
    if from_date and to_date:
        cur.execute("SELECT id, date, meal_type, description, calories, created_at FROM meal_logs WHERE user_id=? AND date BETWEEN ? AND ? ORDER BY date DESC", (user_id, from_date, to_date))
    else:
        cur.execute("SELECT id, date, meal_type, description, calories, created_at FROM meal_logs WHERE user_id=? ORDER BY date DESC LIMIT 200", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# -------------------------
# Tkinter UI
# -------------------------
class DietManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diet Plan Manager")
        self.root.geometry("900x600")
        self.current_user = None
        self.build_login_ui()

    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()

    def build_login_ui(self):
        self.clear_root()
        frm = ttk.Frame(self.root, padding=20)
        frm.pack(expand=True)

        ttk.Label(frm, text="Diet Plan Manager", font=("TkDefaultFont", 18)).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frm, text="Username:").grid(row=1, column=0, sticky="e")
        self.e_username = ttk.Entry(frm, width=30)
        self.e_username.grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Password:").grid(row=2, column=0, sticky="e")
        self.e_password = ttk.Entry(frm, width=30, show="*")
        self.e_password.grid(row=2, column=1, sticky="w")

        btn_login = ttk.Button(frm, text="Login", command=self.handle_login)
        btn_login.grid(row=3, column=0, pady=10)

        btn_register = ttk.Button(frm, text="Register", command=self.handle_register)
        btn_register.grid(row=3, column=1, pady=10, sticky="w")

        info = ("Default admin: username=admin password=admin123 (created automatically on first run).")
        ttk.Label(frm, text=info, foreground="gray").grid(row=4, column=0, columnspan=2, pady=(10,0))

    def handle_register(self):
        popup = tk.Toplevel(self.root)
        popup.title("Register")
        popup.geometry("360x260")
        frm = ttk.Frame(popup, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Full name:").grid(row=0, column=0, sticky="e")
        e_full = ttk.Entry(frm, width=30); e_full.grid(row=0, column=1)

        ttk.Label(frm, text="Email:").grid(row=1, column=0, sticky="e")
        e_email = ttk.Entry(frm, width=30); e_email.grid(row=1, column=1)

        ttk.Label(frm, text="Username:").grid(row=2, column=0, sticky="e")
        e_user = ttk.Entry(frm, width=30); e_user.grid(row=2, column=1)

        ttk.Label(frm, text="Password:").grid(row=3, column=0, sticky="e")
        e_pass = ttk.Entry(frm, width=30, show="*"); e_pass.grid(row=3, column=1)

        def do_register():
            full = e_full.get().strip()
            email = e_email.get().strip()
            user = e_user.get().strip()
            pw = e_pass.get().strip()
            if not user or not pw:
                messagebox.showwarning("Validation", "Username and password are required")
                return
            ok, err = create_user(user, pw, full, email, 0)
            if ok:
                messagebox.showinfo("Success", "Registered successfully, you can login now.")
                popup.destroy()
            else:
                messagebox.showerror("Error", f"Could not register: {err}")

        ttk.Button(frm, text="Register", command=do_register).grid(row=4, column=0, columnspan=2, pady=12)

    def handle_login(self):
        username = self.e_username.get().strip()
        password = self.e_password.get().strip()
        if not username or not password:
            messagebox.showwarning("Validation", "Enter username and password")
            return
        user = authenticate(username, password)
        if not user:
            messagebox.showerror("Login failed", "Invalid credentials")
            return
        self.current_user = user
        if user['is_admin']:
            self.build_admin_dashboard()
        else:
            self.build_user_dashboard()

    # -------------------------
    # Admin UI
    # -------------------------
    def build_admin_dashboard(self):
        self.clear_root()
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=f"Admin dashboard — {self.current_user['username']}", font=("TkDefaultFont", 14)).pack(side="left")
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # Users tab
        tab_users = ttk.Frame(nb, padding=8)
        nb.add(tab_users, text="Users")

        self.users_tree = ttk.Treeview(tab_users, columns=("id", "username", "full_name", "email", "is_admin"), show="headings")
        for col, w in [("id",50), ("username",150), ("full_name",200), ("email",200), ("is_admin",80)]:
            self.users_tree.heading(col, text=col.title())
            self.users_tree.column(col, width=w)
        self.users_tree.pack(fill="both", expand=True, side="left")
        self.load_users_tree()

        users_ops = ttk.Frame(tab_users, padding=8)
        users_ops.pack(side="right", fill="y")
        ttk.Button(users_ops, text="Refresh", command=self.load_users_tree).pack(fill="x")
        ttk.Button(users_ops, text="Create User", command=self.admin_create_user).pack(fill="x", pady=4)
        ttk.Button(users_ops, text="Delete Selected", command=self.admin_delete_selected_user).pack(fill="x", pady=4)

        # Plans tab
        tab_plans = ttk.Frame(nb, padding=8)
        nb.add(tab_plans, text="Diet Plans")
        left = ttk.Frame(tab_plans)
        left.pack(side="left", fill="both", expand=True)

        self.plans_tree = ttk.Treeview(left, columns=("id","name","target_calories"), show="headings")
        self.plans_tree.heading("id", text="ID")
        self.plans_tree.heading("name", text="Plan Name")
        self.plans_tree.heading("target_calories", text="Target kcal")
        self.plans_tree.pack(fill="both", expand=True)
        self.plans_tree.bind("<Double-1>", self.admin_open_plan)

        right_ops = ttk.Frame(tab_plans, padding=8)
        right_ops.pack(side="right", fill="y")
        ttk.Button(right_ops, text="Refresh", command=self.load_plans).pack(fill="x")
        ttk.Button(right_ops, text="Create Plan", command=self.admin_create_plan).pack(fill="x", pady=4)
        ttk.Button(right_ops, text="Delete Selected", command=self.admin_delete_selected_plan).pack(fill="x", pady=4)
        ttk.Button(right_ops, text="Assign Plan to User", command=self.admin_assign_plan_popup).pack(fill="x", pady=8)

        self.load_plans()

    def logout(self):
        self.current_user = None
        self.build_login_ui()

    # Users functions
    def load_users_tree(self):
        for r in self.users_tree.get_children():
            self.users_tree.delete(r)
        rows = list_users()
        for row in rows:
            uid, uname, full, email, is_admin = row
            self.users_tree.insert("", tk.END, values=(uid, uname, full or "", email or "", "Yes" if is_admin else "No"))

    def admin_create_user(self):
        popup = tk.Toplevel(self.root)
        popup.title("Create User")
        frm = ttk.Frame(popup, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="e")
        e_user = ttk.Entry(frm); e_user.grid(row=0, column=1)
        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e")
        e_pw = ttk.Entry(frm, show="*"); e_pw.grid(row=1, column=1)
        ttk.Label(frm, text="Full name:").grid(row=2, column=0, sticky="e")
        e_full = ttk.Entry(frm); e_full.grid(row=2, column=1)
        is_admin_var = tk.IntVar()
        ttk.Checkbutton(frm, text="Is Admin", variable=is_admin_var).grid(row=3, column=1, sticky="w")

        def create():
            ok, err = create_user(e_user.get().strip(), e_pw.get().strip(), e_full.get().strip(), "", is_admin_var.get())
            if ok:
                messagebox.showinfo("OK", "User created")
                popup.destroy()
                self.load_users_tree()
            else:
                messagebox.showerror("Error", err)
        ttk.Button(frm, text="Create", command=create).grid(row=4, column=0, columnspan=2, pady=8)

    def admin_delete_selected_user(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a user row first")
            return
        item = self.users_tree.item(sel[0])['values']
        uid = item[0]
        if messagebox.askyesno("Confirm", f"Delete user {item[1]}?"):
            delete_user(uid)
            self.load_users_tree()

    # Plans functions
    def load_plans(self):
        for r in self.plans_tree.get_children():
            self.plans_tree.delete(r)
        for row in list_plans():
            pid, name, desc, kcal = row
            self.plans_tree.insert("", tk.END, values=(pid, name, kcal or ""))

    def admin_create_plan(self):
        popup = tk.Toplevel(self.root)
        popup.title("Create Diet Plan")
        frm = ttk.Frame(popup, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Plan name:").grid(row=0, column=0, sticky="e")
        e_name = ttk.Entry(frm, width=40); e_name.grid(row=0, column=1)
        ttk.Label(frm, text="Target kcal:").grid(row=1, column=0, sticky="e")
        e_kcal = ttk.Entry(frm, width=20); e_kcal.grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="Description:").grid(row=2, column=0, sticky="ne")
        e_desc = tk.Text(frm, width=50, height=6); e_desc.grid(row=2, column=1)

        def create():
            name = e_name.get().strip()
            kcal = int(e_kcal.get().strip() or 0)
            desc = e_desc.get("1.0", tk.END).strip()
            if not name:
                messagebox.showwarning("Validation", "Name required")
                return
            plan_id = create_plan(name, desc, kcal, self.current_user['id'])
            messagebox.showinfo("OK", "Plan created. Now you can add plan meals by double-clicking it.")
            popup.destroy()
            self.load_plans()
        ttk.Button(frm, text="Create", command=create).grid(row=3, column=0, columnspan=2, pady=8)

    def admin_open_plan(self, event=None):
        sel = self.plans_tree.selection()
        if not sel:
            return
        item = self.plans_tree.item(sel[0])['values']
        plan_id = item[0]
        self.open_plan_editor(plan_id)

    def admin_delete_selected_plan(self):
        sel = self.plans_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a plan first")
            return
        item = self.plans_tree.item(sel[0])['values']
        pid = item[0]
        if messagebox.askyesno("Confirm", f"Delete plan {item[1]} and its meals?"):
            delete_plan(pid)
            self.load_plans()

    def open_plan_editor(self, plan_id):
        row = None
        for p in list_plans():
            if p[0] == plan_id:
                row = p
                break
        if not row:
            messagebox.showerror("Not found", "Plan not found")
            return
        popup = tk.Toplevel(self.root)
        popup.title(f"Edit Plan: {row[1]}")
        popup.geometry("700x500")
        left = ttk.Frame(popup, padding=8); left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(popup, padding=8); right.pack(side="right", fill="y")

        # Plan header
        ttk.Label(left, text=row[1], font=("TkDefaultFont", 14)).pack(anchor="w")
        ttk.Label(left, text=row[2], foreground="gray").pack(anchor="w", pady=(0,10))

        # Plan meals tree
        meals_tree = ttk.Treeview(left, columns=("id","day","meal_type","desc","calories"), show="headings")
        for c,h,w in [("id","ID",40), ("day","Day",60), ("meal_type","Meal",120), ("desc","Description",300), ("calories","kcal",80)]:
            meals_tree.heading(c, text=h)
            meals_tree.column(c, width=w)
        meals_tree.pack(fill="both", expand=True)
        def load_meals():
            for r in meals_tree.get_children():
                meals_tree.delete(r)
            for m in list_plan_meals(plan_id):
                meals_tree.insert("", tk.END, values=m)
        load_meals()

        def add_meal():
            d = simpledialog.askinteger("Day", "Day number (e.g., 1)", parent=popup, minvalue=1)
            if d is None:
                return
            meal_type = simpledialog.askstring("Meal type", "e.g., Breakfast, Lunch", parent=popup)
            if not meal_type:
                return
            desc = simpledialog.askstring("Description", "Meal description", parent=popup)
            kcal = simpledialog.askinteger("Calories", "kcal (integer)", parent=popup, minvalue=0)
            add_plan_meal(plan_id, d, meal_type, desc or "", kcal or 0)
            load_meals()
        def delete_meal():
            sel = meals_tree.selection()
            if not sel: return
            item = meals_tree.item(sel[0])['values']
            if messagebox.askyesno("Confirm", "Delete selected plan meal?"):
                delete_plan_meal(item[0])
                load_meals()

        ttk.Button(right, text="Add Meal", command=add_meal).pack(fill="x", pady=4)
        ttk.Button(right, text="Delete Meal", command=delete_meal).pack(fill="x", pady=4)
        ttk.Button(right, text="Close", command=popup.destroy).pack(fill="x", pady=12)

    def admin_assign_plan_popup(self):
        # choose user and plan and dates
        urows = list_users()
        plans = list_plans()
        if not urows or not plans:
            messagebox.showwarning("Missing data", "Need at least one user and one plan")
            return
        popup = tk.Toplevel(self.root)
        popup.title("Assign Plan")
        frm = ttk.Frame(popup, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="User:").grid(row=0, column=0, sticky="e")
        user_cb = ttk.Combobox(frm, values=[f"{u[0]}:{u[1]}" for u in urows], width=35)
        user_cb.grid(row=0, column=1)
        ttk.Label(frm, text="Plan:").grid(row=1, column=0, sticky="e")
        plan_cb = ttk.Combobox(frm, values=[f"{p[0]}:{p[1]}" for p in plans], width=35)
        plan_cb.grid(row=1, column=1)
        ttk.Label(frm, text="Start (YYYY-MM-DD):").grid(row=2, column=0, sticky="e")
        e_start = ttk.Entry(frm); e_start.grid(row=2, column=1)
        e_start.insert(0, date.today().isoformat())
        ttk.Label(frm, text="End (YYYY-MM-DD):").grid(row=3, column=0, sticky="e")
        e_end = ttk.Entry(frm); e_end.grid(row=3, column=1)
        e_end.insert(0, (date.today()).isoformat())

        def assign():
            u = user_cb.get().split(":")[0]
            p = plan_cb.get().split(":")[0]
            if not u or not p:
                messagebox.showwarning("Select", "Choose user and plan")
                return
            assign_plan_to_user(int(u), int(p), e_start.get().strip(), e_end.get().strip())
            messagebox.showinfo("Assigned", "Plan assigned to user")
            popup.destroy()
        ttk.Button(frm, text="Assign", command=assign).grid(row=4, column=0, columnspan=2, pady=8)

    # -------------------------
    # User UI
    # -------------------------
    def build_user_dashboard(self):
        self.clear_root()
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=f"Welcome {self.current_user['full_name'] or self.current_user['username']}", font=("TkDefaultFont", 14)).pack(side="left")
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right")

        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        # Left: assigned plan
        left = ttk.Frame(main); left.pack(side="left", fill="both", expand=True, padx=(0,8))
        ttk.Label(left, text="Assigned Plan", font=("TkDefaultFont", 12)).pack(anchor="w")
        self.assigned_plan_label = ttk.Label(left, text="", foreground="gray")
        self.assigned_plan_label.pack(anchor="w")

        self.plan_meals_tree = ttk.Treeview(left, columns=("day","meal","desc","kcal"), show="headings")
        for c,h,w in [("day","Day",60), ("meal","Meal",120), ("desc","Description",360), ("kcal","kcal",70)]:
            self.plan_meals_tree.heading(c, text=h)
            self.plan_meals_tree.column(c, width=w)
        self.plan_meals_tree.pack(fill="both", expand=True)

        ttk.Button(left, text="Refresh Plan", command=self.load_my_plan).pack(pady=6)

        # Right: log meals
        right = ttk.Frame(main); right.pack(side="right", fill="y")
        ttk.Label(right, text="Log a Meal", font=("TkDefaultFont", 12)).pack()
        ttk.Label(right, text="Date (YYYY-MM-DD):").pack(anchor="w", pady=(8,0))
        self.e_log_date = ttk.Entry(right); self.e_log_date.pack(fill="x"); self.e_log_date.insert(0, date.today().isoformat())
        ttk.Label(right, text="Meal type:").pack(anchor="w", pady=(8,0))
        self.e_log_type = ttk.Combobox(right, values=["Breakfast","Lunch","Dinner","Snack"], width=25); self.e_log_type.pack()
        ttk.Label(right, text="Description:").pack(anchor="w", pady=(8,0))
        self.e_log_desc = ttk.Entry(right, width=40); self.e_log_desc.pack()
        ttk.Label(right, text="Calories:").pack(anchor="w", pady=(8,0))
        self.e_log_kcal = ttk.Entry(right, width=15); self.e_log_kcal.pack()

        ttk.Button(right, text="Add Log", command=self.user_add_log).pack(pady=12)
        ttk.Button(right, text="View Logs", command=self.user_view_logs_popup).pack(pady=4)

        self.load_my_plan()

    def load_my_plan(self):
        for r in self.plan_meals_tree.get_children():
            self.plan_meals_tree.delete(r)
        up = get_user_plan(self.current_user['id'])
        if not up:
            self.assigned_plan_label.config(text="No active plan assigned.")
            return
        user_plan_id, plan_id, name, desc, s, e = up
        self.assigned_plan_label.config(text=f"{name} — {desc} (from {s} to {e})")
        for m in list_plan_meals(plan_id):
            mid, day, meal_type, meal_desc, kcal = m
            self.plan_meals_tree.insert("", tk.END, values=(day, meal_type, meal_desc, kcal))

    def user_add_log(self):
        d = self.e_log_date.get().strip()
        t = self.e_log_type.get().strip()
        desc = self.e_log_desc.get().strip()
        try:
            kcal = int(self.e_log_kcal.get().strip() or 0)
        except:
            messagebox.showwarning("Validation", "Calories must be integer")
            return
        if not d or not t:
            messagebox.showwarning("Validation", "Date and meal type required")
            return
        log_meal(self.current_user['id'], d, t, desc, kcal)
        messagebox.showinfo("Added", "Meal logged")
        # clear fields
        self.e_log_desc.delete(0, tk.END)
        self.e_log_kcal.delete(0, tk.END)

    def user_view_logs_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("My Meal Logs")
        popup.geometry("700x450")
        frm = ttk.Frame(popup, padding=8); frm.pack(fill="both", expand=True)
        tree = ttk.Treeview(frm, columns=("id","date","meal","desc","kcal","created"), show="headings")
        for c,h,w in [("id","ID",50), ("date","Date",100), ("meal","Meal",100), ("desc","Description",300), ("kcal","kcal",70), ("created","Logged At",150)]:
            tree.heading(c, text=h)
            tree.column(c, width=w)
        tree.pack(fill="both", expand=True)
        for r in list_meal_logs(self.current_user['id']):
            tree.insert("", tk.END, values=r)
        ttk.Button(frm, text="Close", command=popup.destroy).pack(pady=6)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    initialize_demo_data()
    root = tk.Tk()
    app = DietManagerApp(root)
    root.mainloop()
