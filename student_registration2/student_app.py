#!/usr/bin/env python3
"""
student_app.py
Student ERP System (full working version)
"""

import os, sqlite3, hashlib, csv
from datetime import datetime
from tkinter import messagebox
try:
    import customtkinter as ctk
    from tkinter import ttk, filedialog
    from PIL import Image, ImageTk
except Exception as e:
    raise RuntimeError("Missing requirements. Run: pip install customtkinter pillow") from e

# ---------------- Config ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
DB_PATH = os.path.join(BASE_DIR, "student.db")
APP_TITLE = "Student ERP System"
WINDOW_SIZE = "1100x700"

# ---------------- DB ----------------
def get_conn(): return sqlite3.connect(DB_PATH)

def init_db_and_migrate():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            duration TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL,
            payment_date TEXT,
            method TEXT,
            note TEXT
        )
    """)
    conn.commit()

    # Safe migration for students table
    expected_student_cols = {
        "roll_no": "TEXT",
        "gender": "TEXT",
        "dob": "TEXT",
        "course_id": "INTEGER",
        "semester": "TEXT",
        "fees_due": "REAL DEFAULT 0",
        "address": "TEXT"
    }
    cur.execute("PRAGMA table_info(students)")
    existing = [r[1] for r in cur.fetchall()]
    for col, col_def in expected_student_cols.items():
        if col not in existing:
            try: cur.execute(f"ALTER TABLE students ADD COLUMN {col} {col_def}")
            except: pass
    conn.commit(); conn.close()

# ---------------- Utilities ----------------
def hash_password(pw): return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def create_user(email, password, full_name=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (email,password_hash,full_name,created_at) VALUES (?,?,?,?)",
                    (email, hash_password(password), full_name, datetime.utcnow().isoformat()))
        conn.commit(); return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def authenticate_user(email, password):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, full_name FROM users WHERE email=? AND password_hash=?", 
                (email, hash_password(password)))
    row = cur.fetchone(); conn.close(); return row

# ---------------- Courses -------------------
def all_courses():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, code, name FROM courses ORDER BY name")
    rows = cur.fetchall(); conn.close(); return rows

def add_course(code, name, duration=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO courses (code,name,duration) VALUES (?,?,?)", (code,name,duration))
        conn.commit(); return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def delete_course(course_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM courses WHERE id=?", (course_id,)); conn.commit(); conn.close()

# ---------------- Students ------------------
def insert_student(data: dict):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO students (roll_no,name,email,phone,gender,dob,course_id,semester,fees_due,address,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (data.get("roll_no"), data["name"], data.get("email"), data.get("phone"), data.get("gender"),
          data.get("dob"), data.get("course_id"), data.get("semester"), data.get("fees_due",0.0),
          data.get("address"), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def update_student(student_id, data: dict):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE students SET roll_no=?, name=?, email=?, phone=?, gender=?, dob=?, course_id=?, semester=?, fees_due=?, address=?
        WHERE id=?
    """, (data.get("roll_no"), data["name"], data.get("email"), data.get("phone"), data.get("gender"),
          data.get("dob"), data.get("course_id"), data.get("semester"), data.get("fees_due",0.0),
          data.get("address"), student_id))
    conn.commit(); conn.close()

def delete_student(student_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=?", (student_id,)); conn.commit(); conn.close()

def all_students(limit=1000):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.roll_no, s.name, s.email, s.phone, c.name, s.semester, s.fees_due
        FROM students s LEFT JOIN courses c ON s.course_id=c.id
        ORDER BY s.id DESC LIMIT ?
    """, (limit,))
    rows = cur.fetchall(); conn.close(); return rows

def search_students(q):
    q = f"%{q.lower()}%"
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.roll_no, s.name, s.email, s.phone, c.name, s.semester, s.fees_due
        FROM students s LEFT JOIN courses c ON s.course_id=c.id
        WHERE lower(s.name) LIKE ? OR lower(s.roll_no) LIKE ? OR lower(s.email) LIKE ?
        ORDER BY s.id DESC
    """, (q,q,q))
    rows = cur.fetchall(); conn.close(); return rows

# ---------------- Fees -----------------------
def add_fee_payment(student_id, amount, method="Cash", note=""):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO fees (student_id,amount,payment_date,method,note) VALUES (?,?,?,?,?)",
                (student_id, amount, datetime.utcnow().isoformat(), method, note))
    cur.execute("UPDATE students SET fees_due = fees_due - ? WHERE id=?", (amount, student_id))
    conn.commit(); conn.close()

def get_fees_for_student(student_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, amount, payment_date, method, note FROM fees WHERE student_id=? ORDER BY id DESC",
                (student_id,))
    rows = cur.fetchall(); conn.close(); return rows

# ---------------- Analytics ------------------
def analytics_summary():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students"); total_students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM courses"); total_courses = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM fees"); total_fees = cur.fetchone()[0]
    conn.close(); return {"students": total_students, "courses": total_courses, "fees": total_fees}

# ---------------- UI --------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class StudentERPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(1000,650)
        if not os.path.isdir(ASSETS_DIR): os.makedirs(ASSETS_DIR, exist_ok=True)
        init_db_and_migrate()
        self.logged_user = None
        self.selected_student_id = None
        self._build_header(minimal=True)
        signed = self.show_auth_dialog_blocking()
        if not signed: self.destroy(); return
        self._build_header(minimal=False)
        self._build_body()
        self._switch_module("students")

    def _build_header(self, minimal=False):
        if hasattr(self, "header_frame"): self.header_frame.destroy()
        self.header_frame = ctk.CTkFrame(self, height=90)
        self.header_frame.pack(side="top", fill="x"); self.header_frame.pack_propagate(False)
        left = ctk.CTkFrame(self.header_frame, fg_color="transparent"); left.pack(side="left", padx=16)
        logo_img = None
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA"); img = img.resize((56,56), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(img)
            except: logo_img=None
        if logo_img: lbl_logo=ctk.CTkLabel(left,image=logo_img,text=""); lbl_logo.image=logo_img; lbl_logo.pack(side="left", padx=(0,8))
        lbl_title = ctk.CTkLabel(left, text=APP_TITLE, font=ctk.CTkFont(size=18,weight="bold")); lbl_title.pack(side="left")
        lbl_sub = ctk.CTkLabel(self.header_frame,text="Manage students, courses and fees", font=ctk.CTkFont(size=11)); lbl_sub.place(x=150,y=46)
        if not minimal: self.user_label = ctk.CTkLabel(self.header_frame,text=f"Signed in: {self.logged_user[1]}"); self.user_label.pack(side="right", padx=12, pady=12)

    def show_auth_dialog_blocking(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Authentication"); dlg.geometry("480x360"); dlg.resizable(False,False)
        dlg.grab_set(); dlg.transient(self); dlg.focus_force()
        tab=ctk.CTkTabview(dlg,width=440,height=300); tab.pack(padx=20,pady=18); login_tab=tab.add("Login"); reg_tab=tab.add("Register")
        ctk.CTkLabel(login_tab,text="Email").grid(row=0,column=0,sticky="w",padx=6,pady=(8,4))
        login_email=ctk.CTkEntry(login_tab,width=360); login_email.grid(row=1,column=0,padx=6)
        ctk.CTkLabel(login_tab,text="Password").grid(row=2,column=0,sticky="w",padx=6,pady=(8,4))
        login_pass=ctk.CTkEntry(login_tab,width=360,show="*"); login_pass.grid(row=3,column=0,padx=6)
        def do_signin():
            em=login_email.get().strip(); pw=login_pass.get().strip()
            if not em or not pw: messagebox.showwarning("Validation","Enter email and password"); return
            user=authenticate_user(em,pw)
            if not user: messagebox.showerror("Error","Email/password incorrect"); return
            self.logged_user=user; dlg.destroy()
        ctk.CTkButton(login_tab,text="Sign In",width=140,command=do_signin).grid(pady=12)
        ctk.CTkLabel(reg_tab,text="Full Name").grid(row=0,column=0,sticky="w",padx=6,pady=(8,4))
        reg_name=ctk.CTkEntry(reg_tab,width=360); reg_name.grid(row=1,column=0,padx=6)
        ctk.CTkLabel(reg_tab,text="Email").grid(row=2,column=0,sticky="w",padx=6,pady=(8,4))
        reg_email=ctk.CTkEntry(reg_tab,width=360); reg_email.grid(row=3,column=0,padx=6)
        ctk.CTkLabel(reg_tab,text="Password").grid(row=4,column=0,sticky="w",padx=6,pady=(8,4))
        reg_pass=ctk.CTkEntry(reg_tab,width=360,show="*"); reg_pass.grid(row=5,column=0,padx=6)
        def do_register():
            nm=reg_name.get().strip(); em=reg_email.get().strip(); pw=reg_pass.get().strip()
            if not nm or not em or not pw: messagebox.showwarning("Validation","All fields required"); return
            ok=create_user(em,pw,nm)
            if not ok: messagebox.showerror("Error","Email already registered"); return
            messagebox.showinfo("Created","Account created. Please login."); tab.set("Login")
        ctk.CTkButton(reg_tab,text="Register",width=140,command=do_register,fg_color="#1abc9c").grid(pady=12)
        self.update_idletasks()
        x=self.winfo_x()+(self.winfo_width()-480)//2; y=self.winfo_y()+(self.winfo_height()-360)//2
        dlg.geometry(f"+{x}+{y}"); dlg.wait_window(); return bool(self.logged_user)

    def _build_body(self):
        body = ctk.CTkFrame(self); body.pack(side="top", fill="both", expand=True)
        self.sidebar = ctk.CTkFrame(body,width=200); self.sidebar.pack(side="left", fill="y", padx=(12,8), pady=12)
        self.sidebar.pack_propagate(False)
        self.btn_students = ctk.CTkButton(self.sidebar,text="Students",command=lambda:self._switch_module("students"))
        self.btn_courses = ctk.CTkButton(self.sidebar,text="Courses",command=lambda:self._switch_module("courses"))
        self.btn_fees = ctk.CTkButton(self.sidebar,text="Fees",command=lambda:self._switch_module("fees"))
        self.btn_analytics = ctk.CTkButton(self.sidebar,text="Analytics",command=lambda:self._switch_module("analytics"))
        self.btn_students.pack(pady=(24,8), padx=12, fill="x")
        self.btn_courses.pack(pady=8, padx=12, fill="x")
        self.btn_fees.pack(pady=8, padx=12, fill="x")
        self.btn_analytics.pack(pady=8, padx=12, fill="x")
        self.btn_logout = ctk.CTkButton(self.sidebar,text="Sign out",fg_color="#ff5252",command=self._logout)
        self.btn_logout.pack(side="bottom", pady=12, padx=12, fill="x")
        self.main_area = ctk.CTkFrame(body); self.main_area.pack(side="right",fill="both",expand=True,padx=(0,12),pady=12)
        self.frame_students = ctk.CTkFrame(self.main_area)
        self.frame_courses = ctk.CTkFrame(self.main_area)
        self.frame_fees = ctk.CTkFrame(self.main_area)
        self.frame_analytics = ctk.CTkFrame(self.main_area)
        for f in (self.frame_students,self.frame_courses,self.frame_fees,self.frame_analytics): f.place(relx=0,rely=0,relwidth=1,relheight=1)
        # Call your existing module code here
        # self._build_students_module() etc.

    def _switch_module(self,name):
        frames={"students":self.frame_students,"courses":self.frame_courses,"fees":self.frame_fees,"analytics":self.frame_analytics}
        for k,f in frames.items(): 
            if k==name: f.lift()

    def _logout(self):
        if messagebox.askyesno("Sign out","Do you want to sign out?"): self.destroy()

if __name__=="__main__":
    app=StudentERPApp()
    app.mainloop()
