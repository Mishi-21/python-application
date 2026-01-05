"""
Student Projects Submission Tracker
with Email Notifications (Gmail SMTP default)

Features:
- Login / Register (collects email)
- Admin / Student roles and role-based access control
- Project CRUD + attachments
- CSV / PDF export (PDF uses reportlab if installed)
- Email notifications:
    - Student submits new project -> email to admin(s)
    - Admin approves/rejects -> email to student (with optional PDF)
    - Any status change -> email to student and admins (configurable)
- DB migration adds 'attachment' in projects and 'email' in users

SETUP:
- Fill SMTP settings below (Gmail example).
- For Gmail: create an App Password (if using 2FA) and use that as EMAIL_PASSWORD.
- If not using email, leave EMAIL_USERNAME blank and emails will be skipped.

Optional:
pip install reportlab
"""

import os
import shutil
import platform
import sqlite3
import csv
import smtplib
import ssl
import mimetypes
from email.message import EmailMessage
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Optional PDF library
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# ---------------------------
# SMTP / Email configuration
# ---------------------------
# Default: Gmail SMTP. Replace these with your settings.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USERNAME = ""   # e.g. "youremail@gmail.com"
EMAIL_PASSWORD = ""   # app password or account password (preferred: app password)

DEFAULT_ADMIN_EMAIL = "admin@example.com"  # used if no admin email found

DB_FILE = "project_tracker.db"
UPLOAD_DIR = "uploads"

# ---------------------------
# Helper: Email sending
# ---------------------------
def send_email(to_addrs, subject, html_body, attachment_path=None):
    """
    Send HTML email to a single email or list.
    to_addrs: string email or list of emails.
    attachment_path: optional file to attach
    """
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        # Email not configured
        print("Email not sent: SMTP credentials not configured.")
        return False, "SMTP not configured"

    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]

    # filter empty emails
    to_addrs = [e for e in to_addrs if e and "@" in e]
    if not to_addrs:
        print("No valid recipient emails found.")
        return False, "No recipients"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_USERNAME
    msg["To"] = ", ".join(to_addrs)
    msg.set_content("This email requires an HTML-capable client.")
    msg.add_alternative(html_body, subtype='html')

    # attach file if provided and exists
    if attachment_path and os.path.exists(attachment_path):
        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(attachment_path, "rb") as f:
            data = f.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {to_addrs}")
        return True, None
    except Exception as e:
        print("Email send failed:", e)
        return False, str(e)

# ---------------------------
# DB setup and migration
# ---------------------------
def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def ensure_db_and_migrate():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # users table (add email column via migration if missing)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    conn.commit()

    # projects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            username TEXT,
            enrollment TEXT,
            project_title TEXT,
            guide_name TEXT,
            submission_date TEXT,
            status TEXT
        )
    """)
    conn.commit()

    # Ensure 'attachment' column exists in projects
    cur.execute("PRAGMA table_info(projects)")
    cols = [r[1] for r in cur.fetchall()]
    if 'attachment' not in cols:
        try:
            cur.execute("ALTER TABLE projects ADD COLUMN attachment TEXT")
            conn.commit()
        except Exception:
            pass

    # Ensure 'email' column exists in users
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    if 'email' not in cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
            conn.commit()
        except Exception:
            pass

    # default admin
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users(username, password, role, email) VALUES(?,?,?,?)",
                    ('admin', 'admin', 'admin', DEFAULT_ADMIN_EMAIL))
        conn.commit()

    conn.close()
    ensure_upload_dir()

# ---------------------------
# Auth + Users
# ---------------------------
CURRENT_USER = None  # {'username', 'role', 'email'}

def register_user_in_db(username, password, role, email):
    if not username or not password:
        messagebox.showwarning("Validation", "Username and password required.")
        return False
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username, password, role, email) VALUES(?,?,?,?)",
                    (username, password, role, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists.")
        return False

def login_user_db(username, password):
    global CURRENT_USER
    if not username or not password:
        messagebox.showwarning("Validation", "Username and password required.")
        return False
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT username, role, email FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        CURRENT_USER = {'username': row[0], 'role': row[1], 'email': row[2]}
        return True
    else:
        messagebox.showerror("Login failed", "Invalid username or password.")
        return False

def get_admin_emails():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE role='admin'")
    rows = cur.fetchall()
    conn.close()
    emails = [r[0] for r in rows if r and r[0] and "@" in r[0]]
    if not emails:
        # fallback
        emails = [DEFAULT_ADMIN_EMAIL]
    return emails

def get_user_email(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and row[0] and "@" in row[0]:
        return row[0]
    return None

# ---------------------------
# Projects CRUD + attachments
# ---------------------------
def save_attachment_file(src_path):
    if not src_path:
        return None
    try:
        ensure_upload_dir()
        base = os.path.basename(src_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        dest_name = f"{timestamp}_{base}"
        dest_path = os.path.join(UPLOAD_DIR, dest_name)
        shutil.copy2(src_path, dest_path)
        return dest_path
    except Exception as e:
        messagebox.showerror("Attachment Error", f"Failed to save attachment: {e}")
        return None

def add_project_db(student_name, enrollment, title, guide, date_str, status, attachment_path):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects(student_name, username, enrollment, project_title, guide_name, submission_date, status, attachment)
        VALUES(?,?,?,?,?,?,?,?)
    """, (student_name, CURRENT_USER['username'], enrollment, title, guide, date_str, status, attachment_path))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def update_project_db(proj_id, student_name, enrollment, title, guide, date_str, status, attachment_path):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        UPDATE projects SET student_name=?, enrollment=?, project_title=?, guide_name=?, submission_date=?, status=?, attachment=?
        WHERE id=?
    """, (student_name, enrollment, title, guide, date_str, status, attachment_path, proj_id))
    conn.commit()
    conn.close()

def delete_project_db(proj_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT attachment FROM projects WHERE id=?", (proj_id,))
    r = cur.fetchone()
    if r and r[0] and os.path.exists(r[0]):
        try:
            os.remove(r[0])
        except Exception:
            pass
    cur.execute("DELETE FROM projects WHERE id=?", (proj_id,))
    conn.commit()
    conn.close()

def fetch_projects(filters=None):
    q = filters.get('q') if filters else None
    status = filters.get('status') if filters else None
    date_from = filters.get('date_from') if filters else None
    date_to = filters.get('date_to') if filters else None
    username_only = filters.get('username_only') if filters else False

    sql = "SELECT id, student_name, username, enrollment, project_title, guide_name, submission_date, status, attachment FROM projects WHERE 1=1"
    params = []
    if username_only:
        sql += " AND username=?"
        params.append(CURRENT_USER['username'])
    if q:
        sql += " AND (student_name LIKE ? OR project_title LIKE ? OR enrollment LIKE ?)"
        likeq = f"%{q}%"
        params.extend([likeq, likeq, likeq])
    if status and status != "All":
        sql += " AND status=?"
        params.append(status)
    if date_from:
        sql += " AND submission_date>=?"
        params.append(date_from)
    if date_to:
        sql += " AND submission_date<=?"
        params.append(date_to)
    sql += " ORDER BY submission_date DESC"
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_project_by_id(proj_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, student_name, username, enrollment, project_title, guide_name, submission_date, status, attachment FROM projects WHERE id=?", (proj_id,))
    r = cur.fetchone()
    conn.close()
    return r

# ---------------------------
# Export (CSV / PDF)
# ---------------------------
def export_csv(rows, filename):
    header = ["ID", "Student Name", "Username", "Enrollment", "Project Title", "Guide", "Submission Date", "Status", "Attachment"]
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for r in rows:
                writer.writerow(r)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"CSV export failed: {e}")
        return False

def export_pdf(rows, filename):
    if not REPORTLAB_AVAILABLE:
        messagebox.showwarning("PDF Export", "ReportLab not installed. Install with: pip install reportlab")
        return False
    try:
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)
        margin = 30
        y = height - margin
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, "Student Projects Submission Report")
        c.setFont("Helvetica", 10)
        y -= 25
        cols = ["ID", "Student", "User", "Enroll", "Title", "Guide", "Date", "Status"]
        col_w = (width - 2 * margin) / len(cols)
        for i, col in enumerate(cols):
            c.drawString(margin + i * col_w + 2, y, col)
        y -= 12
        c.line(margin, y, width - margin, y)
        y -= 12
        for r in rows:
            if y < margin + 40:
                c.showPage()
                y = height - margin
            for i, cell in enumerate(r[:8]):
                text = str(cell) if cell is not None else ""
                if i == 4 and len(text) > 30:
                    text = text[:27] + "..."
                c.drawString(margin + i * col_w + 2, y, text)
            y -= 14
        c.save()
        return True
    except Exception as e:
        messagebox.showerror("Error", f"PDF export failed: {e}")
        return False

# ---------------------------
# Notifications: HTML templates
# ---------------------------
def html_new_submission(project):
    # project is a row tuple
    return f"""
    <html>
      <body>
        <p>Hi Admin,</p>
        <p>A new project has been submitted:</p>
        <ul>
          <li><strong>Student:</strong> {project[1]}</li>
          <li><strong>Enrollment:</strong> {project[3]}</li>
          <li><strong>Title:</strong> {project[4]}</li>
          <li><strong>Guide:</strong> {project[5]}</li>
          <li><strong>Date:</strong> {project[6]}</li>
          <li><strong>Status:</strong> {project[7]}</li>
        </ul>
        <p>Open the app to review and take action.</p>
      </body>
    </html>
    """

def html_status_change(project, old_status, new_status):
    student_email = get_user_email(project[2]) or project[2]
    return f"""
    <html>
      <body>
        <p>Hi {project[1]},</p>
        <p>Your project "<strong>{project[4]}</strong>" status has changed.</p>
        <p><strong>From:</strong> {old_status} &nbsp;&nbsp; <strong>To:</strong> {new_status}</p>
        <p>Submission date: {project[6]}</p>
        <p>If you have questions, contact your guide: {project[5]}</p>
      </body>
    </html>
    """

# ---------------------------
# Notification wrappers
# ---------------------------
def notify_admins_of_submission(project_id):
    project = get_project_by_id(project_id)
    if not project:
        return
    subject = f"New Project Submitted: {project[4]}"
    body = html_new_submission(project)
    admin_emails = get_admin_emails()
    send_email(admin_emails, subject, body, attachment_path=project[8] if project[8] else None)

def notify_student_of_status_change(project_id, old_status, new_status):
    project = get_project_by_id(project_id)
    if not project:
        return
    student_email = get_user_email(project[2])
    subject = f"Project Status Updated: {project[4]}"
    body = html_status_change(project, old_status, new_status)
    # attach PDF report optionally if reportlab available
    attachment = None
    if REPORTLAB_AVAILABLE:
        # generate small pdf report in temp location
        tmp_pdf = f"report_project_{project_id}.pdf"
        ok = export_pdf([project], tmp_pdf)
        if ok and os.path.exists(tmp_pdf):
            attachment = tmp_pdf
    if student_email:
        send_email(student_email, subject, body, attachment_path=attachment)
    # cleanup temp pdf
    if attachment and os.path.exists(attachment):
        try:
            os.remove(attachment)
        except Exception:
            pass

# ---------------------------
# GUI: Login/Register
# ---------------------------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Login - Project Tracker")
        self.geometry("460x400")
        self.configure(bg="#121212")
        self.resizable(False, False)
        self.build_ui()

    def build_ui(self):
        frm = tk.Frame(self, bg="#121212")
        frm.pack(expand=True, pady=18)

        title = tk.Label(frm, text="🔐 Login", bg="#121212", fg="white", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=6)

        tk.Label(frm, text="Username", bg="#121212", fg="white").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.ent_user = tk.Entry(frm, width=30)
        self.ent_user.grid(row=1, column=1, padx=8, pady=6)

        tk.Label(frm, text="Password", bg="#121212", fg="white").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.ent_pass = tk.Entry(frm, width=30, show="*")
        self.ent_pass.grid(row=2, column=1, padx=8, pady=6)

        btn_login = tk.Button(frm, text="Login 🔑", command=self.do_login, width=26)
        btn_login.grid(row=3, column=0, columnspan=2, pady=12)

        tk.Label(frm, text="Don't have an account?", bg="#121212", fg="white").grid(row=4, column=0, columnspan=2)
        btn_register = tk.Button(frm, text="Register ✍️", command=self.open_register, width=26)
        btn_register.grid(row=5, column=0, columnspan=2, pady=6)

        tk.Label(frm, text="Default admin: username=admin password=admin", bg="#121212", fg="#cccccc",
                 font=("Segoe UI", 8)).grid(row=6, column=0, columnspan=2, pady=10)

    def do_login(self):
        user = self.ent_user.get().strip()
        pw = self.ent_pass.get().strip()
        ok = login_user_db(user, pw)
        if ok:
            self.destroy()
            MainApp()

    def open_register(self):
        RegisterWindow(self)

class RegisterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Register - Project Tracker")
        self.geometry("460x440")
        self.configure(bg="#121212")
        self.resizable(False, False)
        self.build_ui()

    def build_ui(self):
        frm = tk.Frame(self, bg="#121212")
        frm.pack(expand=True, pady=10)

        tk.Label(frm, text="Create Account ✨", bg="#121212", fg="white", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=8)
        tk.Label(frm, text="Username", bg="#121212", fg="white").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.ent_user = tk.Entry(frm, width=32)
        self.ent_user.grid(row=1, column=1, padx=8, pady=6)

        tk.Label(frm, text="Password", bg="#121212", fg="white").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.ent_pass = tk.Entry(frm, width=32, show="*")
        self.ent_pass.grid(row=2, column=1, padx=8, pady=6)

        tk.Label(frm, text="Email (for notifications)", bg="#121212", fg="white").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.ent_email = tk.Entry(frm, width=32)
        self.ent_email.grid(row=3, column=1, padx=8, pady=6)

        tk.Label(frm, text="Role", bg="#121212", fg="white").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        self.role_var = tk.StringVar(value="student")
        ttk.Combobox(frm, textvariable=self.role_var, values=["student", "admin"], state="readonly", width=29).grid(row=4, column=1, padx=8, pady=6)

        btn_create = tk.Button(frm, text="Create Account ✅", command=self.create_account, width=26)
        btn_create.grid(row=5, column=0, columnspan=2, pady=14)

    def create_account(self):
        u = self.ent_user.get().strip()
        p = self.ent_pass.get().strip()
        e = self.ent_email.get().strip()
        r = self.role_var.get()
        if register_user_in_db(u, p, r, e):
            messagebox.showinfo("Success", "Account created. You may login now.")
            self.destroy()

# ---------------------------
# Main GUI with notifications
# ---------------------------
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Submission Tracker - Dashboard")
        self.geometry("1180x700")
        self.configure(bg="#121212")
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e")
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        self.resizable(True, True)
        self.current_attachment_src = None
        self.selected_project_row = None  # before update for status comparison
        self.build_ui()
        self.refresh_table()
        self.mainloop()

    def build_ui(self):
        top_frame = tk.Frame(self, bg="#121212")
        top_frame.pack(fill="x", padx=12, pady=8)
        lbl = tk.Label(top_frame, text=f"📚 Project Tracker - Logged in as: {CURRENT_USER['username']} ({CURRENT_USER['role']})",
                       bg="#121212", fg="white", font=("Segoe UI", 12, "bold"))
        lbl.pack(side="left")
        btn_logout = tk.Button(top_frame, text="Logout 🚪", command=self.do_logout, width=12)
        btn_logout.pack(side="right", padx=6)

        middle = tk.Frame(self, bg="#121212")
        middle.pack(fill="both", expand=True, padx=12, pady=6)

        left = tk.Frame(middle, bg="#121212", width=420)
        left.pack(side="left", fill="y", padx=(0,10), pady=6)

        tk.Label(left, text="Project Form", bg="#121212", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=6)
        form = tk.Frame(left, bg="#121212"); form.pack(anchor="nw")

        tk.Label(form, text="Student Name", bg="#121212", fg="white").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.entry_student = tk.Entry(form, width=36); self.entry_student.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(form, text="Enrollment No.", bg="#121212", fg="white").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.entry_enroll = tk.Entry(form, width=36); self.entry_enroll.grid(row=1, column=1, padx=6, pady=6)

        tk.Label(form, text="Project Title", bg="#121212", fg="white").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.entry_title = tk.Entry(form, width=36); self.entry_title.grid(row=2, column=1, padx=6, pady=6)

        tk.Label(form, text="Guide Name", bg="#121212", fg="white").grid(row=3, column=0, sticky="w", padx=6, pady=6)
        self.entry_guide = tk.Entry(form, width=36); self.entry_guide.grid(row=3, column=1, padx=6, pady=6)

        tk.Label(form, text="Submission Date (YYYY-MM-DD)", bg="#121212", fg="white").grid(row=4, column=0, sticky="w", padx=6, pady=6)
        self.entry_date = tk.Entry(form, width=36); self.entry_date.grid(row=4, column=1, padx=6, pady=6)
        self.entry_date.insert(0, datetime.today().strftime("%Y-%m-%d"))

        tk.Label(form, text="Status", bg="#121212", fg="white").grid(row=5, column=0, sticky="w", padx=6, pady=6)
        self.status_var = tk.StringVar(value="Pending")
        ttk.Combobox(form, textvariable=self.status_var, values=["Pending", "Submitted", "Resubmitted", "Approved", "Rejected"], state="readonly", width=34).grid(row=5, column=1, padx=6, pady=6)

        tk.Label(form, text="Attachment (optional)", bg="#121212", fg="white").grid(row=6, column=0, sticky="w", padx=6, pady=6)
        attach_frame = tk.Frame(form, bg="#121212"); attach_frame.grid(row=6, column=1, padx=6, pady=6, sticky="w")
        self.lbl_attachment = tk.Label(attach_frame, text="No file selected", bg="#121212", fg="#cccccc", anchor="w"); self.lbl_attachment.pack(side="left", padx=(0,6))
        tk.Button(attach_frame, text="📎 Attach File", command=self.pick_attachment).pack(side="left", padx=4)
        tk.Button(attach_frame, text="📂 Open Attachment", command=self.open_selected_attachment).pack(side="left", padx=4)

        btn_frame = tk.Frame(left, bg="#121212"); btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="➕ Add Project", width=14, command=self.handle_add).grid(row=0, column=0, padx=6)
        tk.Button(btn_frame, text="✏️ Update", width=12, command=self.handle_update).grid(row=0, column=1, padx=6)
        tk.Button(btn_frame, text="🗑️ Delete", width=12, command=self.handle_delete).grid(row=0, column=2, padx=6)
        tk.Button(btn_frame, text="🧹 Clear", width=12, command=self.clear_form).grid(row=0, column=3, padx=6)

        stats = tk.Frame(left, bg="#121212"); stats.pack(fill="x", pady=12)
        self.stat_label = tk.Label(stats, text="", bg="#121212", fg="#cccccc", font=("Segoe UI", 9)); self.stat_label.pack(anchor="w")

        right = tk.Frame(middle, bg="#121212"); right.pack(side="left", fill="both", expand=True)
        filter_frame = tk.Frame(right, bg="#121212"); filter_frame.pack(fill="x", pady=6)
        tk.Label(filter_frame, text="Search", bg="#121212", fg="white").grid(row=0, column=0, padx=6)
        self.search_q = tk.Entry(filter_frame, width=28); self.search_q.grid(row=0, column=1, padx=6)
        tk.Label(filter_frame, text="Status", bg="#121212", fg="white").grid(row=0, column=2, padx=6)
        self.filter_status = tk.StringVar(value="All")
        ttk.Combobox(filter_frame, textvariable=self.filter_status, values=["All", "Pending", "Submitted", "Resubmitted", "Approved", "Rejected"], state="readonly", width=18).grid(row=0, column=3, padx=6)
        tk.Label(filter_frame, text="From (YYYY-MM-DD)", bg="#121212", fg="white").grid(row=1, column=0, padx=6, pady=6)
        self.filter_from = tk.Entry(filter_frame, width=18); self.filter_from.grid(row=1, column=1, padx=6, pady=6)
        tk.Label(filter_frame, text="To (YYYY-MM-DD)", bg="#121212", fg="white").grid(row=1, column=2, padx=6)
        self.filter_to = tk.Entry(filter_frame, width=18); self.filter_to.grid(row=1, column=3, padx=6)
        tk.Button(filter_frame, text="🔎 Search / Filter", command=self.refresh_table, width=18).grid(row=0, column=4, padx=8)
        tk.Button(filter_frame, text="🔄 Reset Filters", command=self.reset_filters, width=14).grid(row=1, column=4, padx=8)

        export_frame = tk.Frame(right, bg="#121212"); export_frame.pack(fill="x", pady=6)
        tk.Button(export_frame, text="Export CSV", command=self.export_current_csv, width=12).pack(side="left", padx=6)
        tk.Button(export_frame, text="Export PDF", command=self.export_current_pdf, width=12).pack(side="left", padx=6)

        cols = ("ID", "Student", "User", "Enrollment", "Title", "Guide", "Date", "Status", "Attachment")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            w = 110
            if c == "Title": w = 220
            if c == "Attachment": w = 90
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

    def pick_attachment(self):
        path = filedialog.askopenfilename(title="Select attachment file")
        if not path:
            return
        self.current_attachment_src = path
        self.lbl_attachment.config(text=os.path.basename(path))

    def open_selected_attachment(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0])['values']
            attach_indicator = vals[8]
            # we store actual path in DB; fetch exact row to get path
            proj = get_project_by_id(vals[0])
            if proj and proj[8]:
                attach_path = proj[8]
                if os.path.exists(attach_path):
                    try:
                        if platform.system() == "Windows":
                            os.startfile(attach_path)
                        elif platform.system() == "Darwin":
                            os.system(f"open '{attach_path}'")
                        else:
                            os.system(f"xdg-open '{attach_path}'")
                    except Exception as e:
                        messagebox.showerror("Open Error", f"Failed to open attachment: {e}")
                else:
                    messagebox.showwarning("Missing", "Attachment file not found.")
            else:
                messagebox.showinfo("No Attachment", "Selected record has no attachment.")
            return
        # else open the unsaved selected file
        if getattr(self, "current_attachment_src", None):
            try:
                src = self.current_attachment_src
                if platform.system() == "Windows":
                    os.startfile(src)
                elif platform.system() == "Darwin":
                    os.system(f"open '{src}'")
                else:
                    os.system(f"xdg-open '{src}'")
            except Exception as e:
                messagebox.showerror("Open Error", f"Failed to open file: {e}")
        else:
            messagebox.showinfo("No file", "No attachment selected or available to open.")

    def do_logout(self):
        global CURRENT_USER
        CURRENT_USER = None
        self.destroy()
        LoginWindow().mainloop()

    def clear_form(self):
        self.entry_student.delete(0, tk.END)
        self.entry_enroll.delete(0, tk.END)
        self.entry_title.delete(0, tk.END)
        self.entry_guide.delete(0, tk.END)
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, datetime.today().strftime("%Y-%m-%d"))
        self.status_var.set("Pending")
        self.current_attachment_src = None
        self.lbl_attachment.config(text="No file selected")
        self.selected_project_row = None
        for i in self.tree.selection():
            self.tree.selection_remove(i)

    def handle_add(self):
        student = self.entry_student.get().strip()
        if CURRENT_USER['role'] == 'student' and not student:
            student = CURRENT_USER['username']
            self.entry_student.delete(0, tk.END)
            self.entry_student.insert(0, student)
        enroll = self.entry_enroll.get().strip()
        title = self.entry_title.get().strip()
        guide = self.entry_guide.get().strip()
        date_str = self.entry_date.get().strip()
        status = self.status_var.get()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Validation", "Date must be in YYYY-MM-DD format.")
            return
        attachment_db_path = None
        if getattr(self, "current_attachment_src", None):
            attachment_db_path = save_attachment_file(self.current_attachment_src)
        proj_id = add_project_db(student, enroll, title, guide, date_str, status, attachment_db_path)
        if proj_id:
            messagebox.showinfo("Success", "Project added.")
            self.refresh_table()
            self.clear_form()
            # notify admins
            notify_admins_of_submission(proj_id)

    def handle_update(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a project to update.")
            return
        item = self.tree.item(sel[0])['values']
        proj_id = item[0]
        # load original row for comparison
        orig = get_project_by_id(proj_id)
        if CURRENT_USER['role'] == 'student' and orig[2] != CURRENT_USER['username']:
            messagebox.showerror("Permission", "Students can only update their own submissions.")
            return
        student = self.entry_student.get().strip()
        if CURRENT_USER['role'] == 'student' and not student:
            student = CURRENT_USER['username']
        enroll = self.entry_enroll.get().strip()
        title = self.entry_title.get().strip()
        guide = self.entry_guide.get().strip()
        date_str = self.entry_date.get().strip()
        status = self.status_var.get()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Validation", "Date must be in YYYY-MM-DD format.")
            return
        # handle attachment update
        attachment_db_path = orig[8]
        if getattr(self, "current_attachment_src", None):
            # remove old file if exists
            if attachment_db_path and os.path.exists(attachment_db_path):
                try:
                    os.remove(attachment_db_path)
                except Exception:
                    pass
            attachment_db_path = save_attachment_file(self.current_attachment_src)
        update_project_db(proj_id, student, enroll, title, guide, date_str, status, attachment_db_path)
        messagebox.showinfo("Updated", "Project updated.")
        self.refresh_table()
        # If status changed -> notify student (and admins)
        old_status = orig[7]
        new_status = status
        if old_status != new_status:
            # notify student
            notify_student_of_status_change(proj_id, old_status, new_status)
            # notify admins as well about status change
            admins = get_admin_emails()
            send_email(admins, f"Status changed: {title}", f"<p>Status changed for project <b>{title}</b> from {old_status} to {new_status}.</p>")

    def handle_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a project to delete.")
            return
        item = self.tree.item(sel[0])['values']
        proj_id = item[0]
        orig = get_project_by_id(proj_id)
        if CURRENT_USER['role'] == 'student' and orig[2] != CURRENT_USER['username']:
            messagebox.showerror("Permission", "Students can only delete their own submissions.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected project?"):
            return
        delete_project_db(proj_id)
        messagebox.showinfo("Deleted", "Project deleted.")
        self.refresh_table()
        self.clear_form()

    def on_row_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])['values']
        proj = get_project_by_id(vals[0])
        if not proj:
            return
        self.selected_project_row = proj  # store full row for comparison
        self.entry_student.delete(0, tk.END); self.entry_student.insert(0, proj[1])
        self.entry_enroll.delete(0, tk.END); self.entry_enroll.insert(0, proj[3])
        self.entry_title.delete(0, tk.END); self.entry_title.insert(0, proj[4])
        self.entry_guide.delete(0, tk.END); self.entry_guide.insert(0, proj[5])
        self.entry_date.delete(0, tk.END); self.entry_date.insert(0, proj[6])
        self.status_var.set(proj[7])
        self.current_attachment_src = None
        self.lbl_attachment.config(text=os.path.basename(proj[8]) if proj[8] else "No file selected")

    def reset_filters(self):
        self.search_q.delete(0, tk.END)
        self.filter_status.set("All")
        self.filter_from.delete(0, tk.END)
        self.filter_to.delete(0, tk.END)
        self.refresh_table()

    def refresh_table(self):
        filters = {}
        q = self.search_q.get().strip()
        if q: filters['q'] = q
        status = self.filter_status.get()
        if status: filters['status'] = status
        date_from = self.filter_from.get().strip()
        date_to = self.filter_to.get().strip()
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if CURRENT_USER['role'] == 'student': filters['username_only'] = True
        rows = fetch_projects(filters)
        self.stat_label.config(text=f"Showing {len(rows)} records. Role: {CURRENT_USER['role']}.")
        for r in self.tree.get_children(): self.tree.delete(r)
        for r in rows:
            display_attach = "🔗" if (r[8] and os.path.exists(r[8])) else ""
            ins = list(r)
            ins[8] = display_attach
            self.tree.insert("", tk.END, values=ins)

    def export_current_csv(self):
        filters = {}
        q = self.search_q.get().strip()
        if q: filters['q'] = q
        status = self.filter_status.get()
        if status: filters['status'] = status
        date_from = self.filter_from.get().strip()
        date_to = self.filter_to.get().strip()
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if CURRENT_USER['role'] == 'student': filters['username_only'] = True
        rows = fetch_projects(filters)
        if not rows:
            messagebox.showinfo("No data", "No records to export.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], title="Save CSV")
        if not fpath: return
        ok = export_csv(rows, fpath)
        if ok: messagebox.showinfo("Exported", f"CSV exported to {fpath}")

    def export_current_pdf(self):
        if not REPORTLAB_AVAILABLE:
            messagebox.showwarning("ReportLab missing", "ReportLab not installed. Install with: pip install reportlab\nExporting CSV instead.")
            self.export_current_csv()
            return
        filters = {}
        q = self.search_q.get().strip()
        if q: filters['q'] = q
        status = self.filter_status.get()
        if status: filters['status'] = status
        date_from = self.filter_from.get().strip()
        date_to = self.filter_to.get().strip()
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if CURRENT_USER['role'] == 'student': filters['username_only'] = True
        rows = fetch_projects(filters)
        if not rows:
            messagebox.showinfo("No data", "No records to export.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files","*.pdf")], title="Save PDF")
        if not fpath: return
        ok = export_pdf(rows, fpath)
        if ok: messagebox.showinfo("Exported", f"PDF exported to {fpath}")

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    ensure_db_and_migrate()
    LoginWindow().mainloop()
