# scholarship_app.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import csv
import os
from datetime import datetime

# Optional libraries
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")  # we won't block UI
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

DB_FILE = "scholarship.db"

# -----------------------------
# Database setup and functions
# -----------------------------
def db_connect():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            course TEXT,
            scholarship_type TEXT,
            amount REAL,
            status TEXT,
            application_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(username: str, password: str, role: str = "user") -> (bool, str):
    if not username or not password:
        return False, "Username and password required"
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username, password, role) VALUES(?,?,?)",
                    (username, hash_password(password), role))
        conn.commit()
        conn.close()
        return True, "Registered"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, str(e)

def validate_login(username: str, password: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE username=? AND password=?",
                (username, hash_password(password)))
    res = cur.fetchone()
    conn.close()
    return res  # (id, username, role) or None

# User management helpers
def list_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_role(user_id, new_role):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()

def delete_user_by_id(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

# Applications CRUD
def insert_application(student_name, course, scholarship_type, amount, status, application_date):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications(student_name, course, scholarship_type, amount, status, application_date)
        VALUES(?,?,?,?,?,?)
    """, (student_name, course, scholarship_type, amount, status, application_date))
    conn.commit()
    conn.close()

def fetch_applications_raw():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_application(app_id, student_name, course, scholarship_type, amount, status, application_date):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        UPDATE applications
        SET student_name=?, course=?, scholarship_type=?, amount=?, status=?, application_date=?
        WHERE id=?
    """, (student_name, course, scholarship_type, amount, status, application_date, app_id))
    conn.commit()
    conn.close()

def delete_application(app_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()

# -----------------------------
# Utilities
# -----------------------------
def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def iso_date_or_empty(s):
    # expects YYYY-MM-DD or empty
    s = (s or "").strip()
    if not s:
        return ""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        return ""

# -----------------------------
# PDF Export Helpers
# -----------------------------
def export_application_to_pdf_reportlab(app_row, path):
    # app_row: (id, student_name, course, scholarship_type, amount, status, application_date)
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    margin = 40
    x = margin
    y = h - margin

    title = "Scholarship Application"
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, title)
    y -= 30

    c.setFont("Helvetica", 12)
    labels = ["ID", "Student Name", "Course", "Scholarship Type", "Amount", "Status", "Application Date"]
    for label, value in zip(labels, app_row):
        txt = f"{label}: {value}"
        c.drawString(x, y, txt)
        y -= 20

    c.showPage()
    c.save()

def export_application_to_html(app_row, path):
    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Application {app_row[0]}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;background:#fff;color:#222;padding:24px}}
h1{{color:#111}}
.row{{margin-bottom:10px}}
.label{{font-weight:700;display:inline-block;width:160px}}
</style>
</head>
<body>
<h1>Scholarship Application</h1>
<div class="row"><span class="label">ID</span>{app_row[0]}</div>
<div class="row"><span class="label">Student Name</span>{app_row[1]}</div>
<div class="row"><span class="label">Course</span>{app_row[2]}</div>
<div class="row"><span class="label">Scholarship Type</span>{app_row[3]}</div>
<div class="row"><span class="label">Amount</span>{app_row[4]}</div>
<div class="row"><span class="label">Status</span>{app_row[5]}</div>
<div class="row"><span class="label">Application Date</span>{app_row[6]}</div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

# -----------------------------
# Main GUI App
# -----------------------------
class ScholarshipApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scholarship Application Manager")
        self.root.geometry("1200x700")
        self.root.configure(bg="#161616")
        self.center_window()

        # style
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview",
                             background="#1f1f1f",
                             foreground="white",
                             fieldbackground="#1f1f1f",
                             rowheight=24)
        self.style.configure("Treeview.Heading", background="#2b2b2b", foreground="white")
        self.style.map("Treeview", background=[("selected", "#37474f")])

        self.current_user = None  # (id, username, role)
        self.login_page()

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width() or 1200
        h = self.root.winfo_height() or 700
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # -----------------------------
    # Login / Register pages
    # -----------------------------
    def login_page(self):
        for w in self.root.winfo_children():
            w.destroy()
        frame = tk.Frame(self.root, bg="#222222")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=460, height=420)

        tk.Label(frame, text="Scholarship Manager", bg="#222222", fg="white",
                 font=("Segoe UI", 18, "bold")).pack(pady=(18,8))
        tk.Label(frame, text="Login to continue", bg="#222222", fg="#cfcfcf").pack(pady=(0,10))

        tk.Label(frame, text="Username", bg="#222222", fg="white").pack(anchor="w", padx=30)
        ent_user = tk.Entry(frame, width=36)
        ent_user.pack(padx=30, pady=(0,8))

        tk.Label(frame, text="Password", bg="#222222", fg="white").pack(anchor="w", padx=30)
        ent_pw = tk.Entry(frame, show="*", width=36)
        ent_pw.pack(padx=30, pady=(0,12))

        def do_login():
            u = ent_user.get().strip()
            p = ent_pw.get()
            if not u or not p:
                messagebox.showwarning("Login", "Please enter username and password")
                return
            res = validate_login(u, p)
            if res:
                self.current_user = res
                self.build_main_ui()
            else:
                messagebox.showerror("Login Failed", "Invalid credentials")

        tk.Button(frame, text="Login", command=do_login, width=30, bg="#2e7d32", fg="white").pack(pady=(6,6))
        tk.Button(frame, text="Register", command=self.register_page, width=30).pack()

    def register_page(self):
        for w in self.root.winfo_children():
            w.destroy()
        frame = tk.Frame(self.root, bg="#222222")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=520, height=520)

        tk.Label(frame, text="Create Account", bg="#222222", fg="white",
                 font=("Segoe UI", 18, "bold")).pack(pady=(10,8))
        tk.Label(frame, text="Choose a username and password", bg="#222222", fg="#cfcfcf").pack(pady=(0,8))

        tk.Label(frame, text="Username", bg="#222222", fg="white").pack(anchor="w", padx=30)
        ent_user = tk.Entry(frame, width=40)
        ent_user.pack(padx=30, pady=(0,8))

        tk.Label(frame, text="Password", bg="#222222", fg="white").pack(anchor="w", padx=30)
        ent_pw = tk.Entry(frame, show="*", width=40)
        ent_pw.pack(padx=30, pady=(0,8))

        tk.Label(frame, text="Confirm Password", bg="#222222", fg="white").pack(anchor="w", padx=30)
        ent_pw2 = tk.Entry(frame, show="*", width=40)
        ent_pw2.pack(padx=30, pady=(0,8))

        # Make admin checkbox: allowed if there is no admin in DB OR current_user is admin
        has_admin = any(u for u in list_users() if u[2] == "admin")
        make_admin_var = tk.BooleanVar(value=False)
        if not has_admin:
            chk = tk.Checkbutton(frame, text="Make this account ADMIN (first admin)",
                                 bg="#222222", fg="white", variable=make_admin_var, selectcolor="#333333")
            chk.pack(pady=(6,6))
        else:
            # if current logged-in user is admin allow marking
            if self.current_user and self.current_user[2] == "admin":
                chk = tk.Checkbutton(frame, text="Create as ADMIN",
                                     bg="#222222", fg="white", variable=make_admin_var, selectcolor="#333333")
                chk.pack(pady=(6,6))

        def do_register():
            u = ent_user.get().strip()
            p1 = ent_pw.get()
            p2 = ent_pw2.get()
            if not u or not p1:
                messagebox.showwarning("Register", "Complete fields")
                return
            if p1 != p2:
                messagebox.showwarning("Register", "Passwords do not match")
                return
            role = "admin" if make_admin_var.get() else "user"
            ok, msg = register_user(u, p1, role)
            if ok:
                messagebox.showinfo("Success", "Account created — please login")
                self.login_page()
            else:
                messagebox.showerror("Error", msg)

        tk.Button(frame, text="Create Account", command=do_register, width=30, bg="#1976d2", fg="white").pack(pady=(8,6))
        tk.Button(frame, text="Back to Login", command=self.login_page, width=30).pack()

    # -----------------------------
    # Main UI structure
    # -----------------------------
    def build_main_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#0f1113", width=240)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="Menu", bg="#0f1113", fg="white",
                 font=("Segoe UI", 12, "bold")).pack(pady=(12,6), anchor="w", padx=16)

        tk.Button(sidebar, text="Dashboard", anchor="w",
                  command=self.show_dashboard, width=28, bg="#0f1113", fg="white", bd=0).pack(pady=4, padx=6)
        tk.Button(sidebar, text="Manage Applications", anchor="w",
                  command=self.show_manage, width=28, bg="#0f1113", fg="white", bd=0).pack(pady=4, padx=6)
        tk.Button(sidebar, text="Export All (CSV)", anchor="w",
                  command=self.export_all_csv, width=28, bg="#0f1113", fg="white", bd=0).pack(pady=4, padx=6)
        tk.Button(sidebar, text="Export Selected to PDF", anchor="w",
                  command=self.export_selected_pdf, width=28, bg="#0f1113", fg="white", bd=0).pack(pady=4, padx=6)

        # Admin-only user management
        if self.current_user and self.current_user[2] == "admin":
            tk.Button(sidebar, text="User Management", anchor="w",
                      command=self.user_management, width=28, bg="#0f1113", fg="white", bd=0).pack(pady=4, padx=6)

        tk.Label(sidebar, text=f"User: {self.current_user[1]}", bg="#0f1113", fg="#bdbdbd",
                 font=("Segoe UI", 9)).pack(side="bottom", pady=16, padx=10, anchor="w")
        tk.Button(sidebar, text="Logout", command=self.logout, width=20, bg="#7b1fa2", fg="white").pack(side="bottom", pady=12)

        # Topbar
        topbar = tk.Frame(self.root, bg="#151515", height=80)
        topbar.pack(side="top", fill="x")

        self.title_lbl = tk.Label(topbar, text="Dashboard", bg="#151515", fg="white", font=("Segoe UI", 16, "bold"))
        self.title_lbl.pack(side="left", padx=18)

        # Content area
        self.content = tk.Frame(self.root, bg="#171717")
        self.content.pack(side="right", fill="both", expand=True)

        self.show_dashboard()

    def logout(self):
        self.current_user = None
        self.login_page()

    # -----------------------------
    # Dashboard: charts if available
    # -----------------------------
    def show_dashboard(self):
        self.title_lbl.config(text="Dashboard")
        for w in self.content.winfo_children():
            w.destroy()

        header = tk.Frame(self.content, bg="#171717")
        header.pack(fill="x", pady=(12,6), padx=12)
        tk.Label(header, text="Overview", bg="#171717", fg="white", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        rows = fetch_applications_raw()
        total = len(rows)
        approved = sum(1 for r in rows if str(r[5]).lower() == "approved")
        pending = sum(1 for r in rows if str(r[5]).lower() in ("pending","applied","in review"))
        rejected = sum(1 for r in rows if str(r[5]).lower() == "rejected")

        cards = tk.Frame(self.content, bg="#171717")
        cards.pack(fill="x", padx=12, pady=(8,12))
        self._make_card(cards, "Total Applications", total).pack(side="left", padx=8)
        self._make_card(cards, "Approved", approved).pack(side="left", padx=8)
        self._make_card(cards, "Pending", pending).pack(side="left", padx=8)
        self._make_card(cards, "Rejected", rejected).pack(side="left", padx=8)

        # Charts area or fallback
        chart_frame = tk.Frame(self.content, bg="#171717")
        chart_frame.pack(fill="both", expand=True, padx=12, pady=12)

        if MATPLOTLIB_AVAILABLE and total > 0:
            # pie chart for status
            statuses = [r[5] or "Unknown" for r in rows]
            labels = []
            counts = []
            for label in sorted(set(statuses)):
                labels.append(label)
                counts.append(sum(1 for s in statuses if s == label))

            fig1 = plt.Figure(figsize=(4,3))
            ax1 = fig1.add_subplot(111)
            ax1.pie(counts, labels=labels, autopct="%1.0f%%")
            ax1.set_title("Status Distribution")

            canvas1 = FigureCanvasTkAgg(fig1, master=chart_frame)
            canvas1.get_tk_widget().pack(side="left", padx=10, pady=10, fill="both", expand=True)

            # bar chart: top courses by count
            courses = [ (r[2] or "Unknown") for r in rows ]
            course_counts = {}
            for c in courses:
                course_counts[c] = course_counts.get(c, 0) + 1
            top_courses = sorted(course_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            if top_courses:
                fig2 = plt.Figure(figsize=(5,3))
                ax2 = fig2.add_subplot(111)
                names = [t[0] for t in top_courses]
                vals = [t[1] for t in top_courses]
                ax2.bar(range(len(names)), vals)
                ax2.set_xticks(range(len(names)))
                ax2.set_xticklabels(names, rotation=30, ha="right")
                ax2.set_title("Top Courses (by applications)")
                canvas2 = FigureCanvasTkAgg(fig2, master=chart_frame)
                canvas2.get_tk_widget().pack(side="right", padx=10, pady=10, fill="both", expand=True)
        else:
            note = "Charts require matplotlib. Install with: pip install matplotlib\n" if not MATPLOTLIB_AVAILABLE else ""
            tk.Label(chart_frame, text=note + "No chartable data." if total==0 else note,
                     bg="#171717", fg="white").pack(anchor="center", pady=40)

    def _make_card(self, parent, title, number):
        card = tk.Frame(parent, bg="#232323", width=200, height=80)
        card.pack_propagate(False)
        tk.Label(card, text=title, bg="#232323", fg="#cfcfcf", font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(8,0))
        tk.Label(card, text=str(number), bg="#232323", fg="white", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=10, pady=(6,0))
        return card

    # -----------------------------
    # Manage Applications (CRUD + search + date filters)
    # -----------------------------
    def show_manage(self):
        self.title_lbl.config(text="Manage Applications")
        for w in self.content.winfo_children():
            w.destroy()

        topbar = tk.Frame(self.content, bg="#171717")
        topbar.pack(fill="x", padx=12, pady=10)

        form = tk.Frame(topbar, bg="#171717")
        form.pack(side="left", padx=(0,12), pady=6)

        tk.Label(form, text="Student Name", bg="#171717", fg="white").grid(row=0, column=0, sticky="w")
        self.f_name = tk.Entry(form, width=28)
        self.f_name.grid(row=1, column=0, pady=(4,8))

        tk.Label(form, text="Course", bg="#171717", fg="white").grid(row=2, column=0, sticky="w")
        self.f_course = tk.Entry(form, width=28)
        self.f_course.grid(row=3, column=0, pady=(4,8))

        tk.Label(form, text="Scholarship Type", bg="#171717", fg="white").grid(row=4, column=0, sticky="w")
        self.f_type = tk.Entry(form, width=28)
        self.f_type.grid(row=5, column=0, pady=(4,8))

        tk.Label(form, text="Amount", bg="#171717", fg="white").grid(row=6, column=0, sticky="w")
        self.f_amount = tk.Entry(form, width=28)
        self.f_amount.grid(row=7, column=0, pady=(4,8))

        tk.Label(form, text="Status", bg="#171717", fg="white").grid(row=8, column=0, sticky="w")
        self.f_status = ttk.Combobox(form, values=["Pending","Approved","Rejected","In Review"], width=26)
        self.f_status.grid(row=9, column=0, pady=(4,8))
        self.f_status.set("Pending")

        tk.Label(form, text="Application Date (YYYY-MM-DD)", bg="#171717", fg="white").grid(row=10, column=0, sticky="w")
        self.f_date = tk.Entry(form, width=28)
        self.f_date.grid(row=11, column=0, pady=(4,8))
        self.f_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        btn_frame = tk.Frame(form, bg="#171717")
        btn_frame.grid(row=12, column=0, pady=(6,0))

        tk.Button(btn_frame, text="Add", width=10, command=self.add_application, bg="#2e7d32", fg="white").grid(row=0, column=0, padx=4)
        tk.Button(btn_frame, text="Update", width=10, command=self.update_application, bg="#1976d2", fg="white").grid(row=0, column=1, padx=4)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete_selected, bg="#b71c1c", fg="white").grid(row=0, column=2, padx=4)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear_form).grid(row=0, column=3, padx=4)

        # right: search & table & date filter
        right = tk.Frame(self.content, bg="#171717")
        right.pack(side="right", fill="both", expand=True, padx=12, pady=6)

        controls = tk.Frame(right, bg="#171717")
        controls.pack(fill="x", pady=(0,8))

        tk.Label(controls, text="Search:", bg="#171717", fg="white").pack(side="left")
        self.search_var = tk.Entry(controls, width=22)
        self.search_var.pack(side="left", padx=(6,8))
        tk.Button(controls, text="Search", command=self.apply_filters).pack(side="left", padx=(0,8))
        tk.Button(controls, text="Reset", command=self.reset_filters).pack(side="left")

        tk.Label(controls, text="Status:", bg="#171717", fg="white").pack(side="left", padx=(12,6))
        self.filter_status = ttk.Combobox(controls, values=["All","Pending","Approved","Rejected","In Review"], width=14)
        self.filter_status.pack(side="left")
        self.filter_status.set("All")

        tk.Label(controls, text="Course:", bg="#171717", fg="white").pack(side="left", padx=(12,6))
        self.filter_course = ttk.Combobox(controls, values=["All"], width=18)
        self.filter_course.pack(side="left")
        self.filter_course.set("All")

        # date range
        tk.Label(controls, text="From (YYYY-MM-DD):", bg="#171717", fg="white").pack(side="left", padx=(12,6))
        self.filter_from = tk.Entry(controls, width=12)
        self.filter_from.pack(side="left")
        tk.Label(controls, text="To:", bg="#171717", fg="white").pack(side="left", padx=(6,6))
        self.filter_to = tk.Entry(controls, width=12)
        self.filter_to.pack(side="left")

        cols = ("ID","Student","Course","Type","Amount","Status","Date")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=True)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == "Student":
                self.tree.column(c, width=220)
            elif c == "Amount":
                self.tree.column(c, width=90, anchor="e")
            else:
                self.tree.column(c, width=120)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        self.load_table()
        self.populate_course_filter()

    def clear_form(self):
        self.f_name.delete(0, tk.END)
        self.f_course.delete(0, tk.END)
        self.f_type.delete(0, tk.END)
        self.f_amount.delete(0, tk.END)
        self.f_status.set("Pending")
        self.f_date.delete(0, tk.END)
        self.f_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        for s in self.tree.selection():
            self.tree.selection_remove(s)

    def add_application(self):
        name = self.f_name.get().strip()
        course = self.f_course.get().strip()
        stype = self.f_type.get().strip()
        amount = safe_float(self.f_amount.get(), 0.0)
        status = self.f_status.get().strip() or "Pending"
        app_date = iso_date_or_empty(self.f_date.get().strip()) or datetime.now().strftime("%Y-%m-%d")
        if not name:
            messagebox.showwarning("Validation", "Student name is required")
            return
        insert_application(name, course, stype, amount, status, app_date)
        self.load_table()
        self.populate_course_filter()
        messagebox.showinfo("Added", "Application added")

    def update_application(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a record to update")
            return
        app_id = self.tree.item(sel)["values"][0]
        name = self.f_name.get().strip()
        course = self.f_course.get().strip()
        stype = self.f_type.get().strip()
        amount = safe_float(self.f_amount.get(), 0.0)
        status = self.f_status.get().strip() or "Pending"
        app_date = iso_date_or_empty(self.f_date.get().strip()) or datetime.now().strftime("%Y-%m-%d")
        if not name:
            messagebox.showwarning("Validation", "Student name is required")
            return
        update_application(app_id, name, course, stype, amount, status, app_date)
        self.load_table()
        self.populate_course_filter()
        messagebox.showinfo("Updated", "Record updated")

    def delete_selected(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a record to delete")
            return
        app_id = self.tree.item(sel)["values"][0]
        if messagebox.askyesno("Confirm", "Delete selected record?"):
            delete_application(app_id)
            self.load_table()
            self.populate_course_filter()
            self.clear_form()
            messagebox.showinfo("Deleted", "Record deleted")

    def on_row_select(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        vals = self.tree.item(sel)["values"]
        # (id, student, course, type, amount, status, date)
        self.f_name.delete(0, tk.END); self.f_name.insert(0, vals[1])
        self.f_course.delete(0, tk.END); self.f_course.insert(0, vals[2])
        self.f_type.delete(0, tk.END); self.f_type.insert(0, vals[3])
        self.f_amount.delete(0, tk.END); self.f_amount.insert(0, vals[4])
        self.f_status.set(vals[5])
        self.f_date.delete(0, tk.END); self.f_date.insert(0, vals[6] or "")

    def load_table(self, rows=None):
        if rows is None:
            rows = fetch_applications_raw()
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            # ensure date column present
            row_out = list(row)
            if len(row_out) < 7:
                row_out += [""]
            self.tree.insert("", tk.END, values=row_out)

    def populate_course_filter(self):
        rows = fetch_applications_raw()
        courses = sorted({(r[2] or "").strip() for r in rows if (r[2] or "").strip()})
        vals = ["All"] + [c for c in courses if c]
        self.filter_course['values'] = vals
        if self.filter_course.get() not in vals:
            self.filter_course.set("All")

    def apply_filters(self):
        q = (self.search_var.get() or "").strip().lower()
        status = (self.filter_status.get() or "All")
        course = (self.filter_course.get() or "All")
        date_from = iso_date_or_empty(self.filter_from.get().strip())
        date_to = iso_date_or_empty(self.filter_to.get().strip())
        rows = fetch_applications_raw()
        filtered = []
        for r in rows:
            sid, name, crs, stype, amount, st, app_date = (list(r) + [""])[:7]
            if q:
                if q not in str(name).lower() and q not in str(stype).lower() and q not in str(crs).lower():
                    continue
            if status and status != "All":
                if str(st).lower() != status.lower():
                    continue
            if course and course != "All":
                if str(crs).lower() != course.lower():
                    continue
            if date_from:
                try:
                    if not app_date or datetime.strptime(app_date, "%Y-%m-%d") < datetime.strptime(date_from, "%Y-%m-%d"):
                        continue
                except Exception:
                    continue
            if date_to:
                try:
                    if not app_date or datetime.strptime(app_date, "%Y-%m-%d") > datetime.strptime(date_to, "%Y-%m-%d"):
                        continue
                except Exception:
                    continue
            filtered.append(r)
        self.load_table(filtered)

    def reset_filters(self):
        self.search_var.delete(0, tk.END)
        self.filter_status.set("All")
        self.filter_course.set("All")
        self.filter_from.delete(0, tk.END)
        self.filter_to.delete(0, tk.END)
        self.load_table()

    # -----------------------------
    # Export functions
    # -----------------------------
    def export_all_csv(self):
        rows = fetch_applications_raw()
        if not rows:
            messagebox.showinfo("Export", "No data to export")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")],
                                            initialfile="scholarship_applications.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID","Student Name","Course","Scholarship Type","Amount","Status","Application Date"])
                for r in rows:
                    writer.writerow(r)
            messagebox.showinfo("Exported", f"Data exported to {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def export_selected_pdf(self):
        sel = getattr(self, "tree", None)
        if not sel:
            messagebox.showwarning("Export", "Open Manage Applications and select a record")
            return
        focused = sel.focus()
        if not focused:
            messagebox.showwarning("Export", "Select a record to export")
            return
        row = sel.item(focused)["values"]
        if not row:
            messagebox.showwarning("Export", "Select a valid record")
            return
        # ensure 7 columns
        row = list(row) + [""] * (7 - len(row))

        save_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                 filetypes=[("PDF files","*.pdf"),("HTML files","*.html")],
                                                 initialfile=f"application_{row[0]}.pdf")
        if not save_path:
            return
        try:
            if save_path.lower().endswith(".pdf"):
                if REPORTLAB_AVAILABLE:
                    export_application_to_pdf_reportlab(row, save_path)
                    messagebox.showinfo("Exported", f"PDF saved as {os.path.basename(save_path)}")
                else:
                    # fallback: create HTML and save with .pdf extension (still HTML). Notify user.
                    export_application_to_html(row, save_path + ".html")
                    messagebox.showinfo("Partial Export", "reportlab not installed. Created HTML file; open it and Print->Save as PDF.")
            else:
                # html
                export_application_to_html(row, save_path)
                messagebox.showinfo("Exported", f"HTML saved as {os.path.basename(save_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    # -----------------------------
    # Admin: User Management
    # -----------------------------
    def user_management(self):
        self.title_lbl.config(text="User Management")
        for w in self.content.winfo_children():
            w.destroy()

        frame = tk.Frame(self.content, bg="#171717")
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(frame, text="Users", bg="#171717", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        cols = ("ID","Username","Role")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        tree.pack(fill="both", expand=True, pady=(8,6))
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=200)

        def load_users():
            for r in tree.get_children():
                tree.delete(r)
            for u in list_users():
                tree.insert("", tk.END, values=u)

        load_users()

        ctrl = tk.Frame(frame, bg="#171717")
        ctrl.pack(fill="x", pady=(6,0))

        role_var = ttk.Combobox(ctrl, values=["user","reviewer","admin"], width=12)
        role_var.grid(row=0, column=0, padx=6)
        role_var.set("user")

        def promote():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Select a user")
                return
            uid = tree.item(sel)["values"][0]
            update_user_role(uid, role_var.get())
            load_users()
            messagebox.showinfo("Updated", "User role updated")

        def remove_user():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Select a user")
                return
            uid = tree.item(sel)["values"][0]
            if messagebox.askyesno("Confirm", "Delete user?"):
                delete_user_by_id(uid)
                load_users()
                messagebox.showinfo("Deleted", "User deleted")

        tk.Button(ctrl, text="Set Role", command=promote, bg="#1976d2", fg="white").grid(row=0, column=1, padx=6)
        tk.Button(ctrl, text="Delete User", command=remove_user, bg="#b71c1c", fg="white").grid(row=0, column=2, padx=6)

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    db_connect()
    root = tk.Tk()
    app = ScholarshipApp(root)
    root.mainloop()
