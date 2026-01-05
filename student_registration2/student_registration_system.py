import customtkinter as ctk
import sqlite3
from datetime import datetime
import re
from tkinter import messagebox, ttk
import tkinter as tk

# Modern appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class StudentRegistrationSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Student Registration System - College Management")
        self.state('zoomed')  # This makes it FULLY MAXIMIZED on Windows (best option)
        # Alternative for cross-platform: self.attributes('-zoomed', True)

        # Database
        self.init_db()

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        
        title_label = ctk.CTkLabel(self.sidebar, text="Student Portal", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.add_btn = ctk.CTkButton(self.sidebar, text="Add Student", height=40, command=self.show_add_frame)
        self.add_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.view_btn = ctk.CTkButton(self.sidebar, text="View All Students", height=40, command=self.show_view_frame)
        self.view_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Main content
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, sticky="nswe", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.show_add_frame()

    def init_db(self):
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                age INTEGER,
                gender TEXT,
                course TEXT,
                address TEXT,
                registration_date TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_add_frame(self):
        self.clear_content()
        self.add_btn.configure(fg_color=("gray75", "gray25"))
        self.view_btn.configure(fg_color="transparent")

        # Your existing add form code (unchanged - works perfectly)
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid(row=0, column=0, sticky="nswe", padx=20, pady=20)
        frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(frame, text="Register New Student", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, columnspan=2, pady=30)

        fields = [("Full Name", "name"), ("Email", "email"), ("Phone", "phone"), ("Age", "age"),
                  ("Gender", "gender"), ("Course", "course"), ("Address", "address")]

        self.entries = {}
        row = 1
        for label_text, key in fields:
            ctk.CTkLabel(frame, text=label_text + ":", font=ctk.CTkFont(size=14), anchor="w").grid(row=row, column=0, sticky="w", padx=25, pady=8)
            if key == "gender":
                combo = ctk.CTkComboBox(frame, values=["Male", "Female", "Other"], state="readonly")
                combo.set("Select Gender")
                combo.grid(row=row, column=1, sticky="ew", padx=25, pady=8)
                self.entries[key] = combo
            elif key == "course":
                combo = ctk.CTkComboBox(frame, values=[
                    "B.Tech Computer Science", "B.Tech Mechanical", "B.Tech Civil", "BBA", "B.Com", 
                    "MBBS", "BDS", "BCA", "B.Sc Nursing", "BA Psychology", "B.Arch"
                ], state="readonly")
                combo.set("Select Course")
                combo.grid(row=row, column=1, sticky="ew", padx=25, pady=8)
                self.entries[key] = combo
            elif key == "address":
                entry = ctk.CTkTextbox(frame, height=90)
                entry.grid(row=row, column=1, sticky="ew", padx=25, pady=8)
                self.entries[key] = entry
            else:
                entry = ctk.CTkEntry(frame, height=40, font=ctk.CTkFont(size=14))
                entry.grid(row=row, column=1, sticky="ew", padx=25, pady=8)
                self.entries[key] = entry
            row += 1

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=40)

        ctk.CTkButton(btn_frame, text="Register Student", width=200, height=50,
                     fg_color="#1f6aa5", hover_color="#144870", font=ctk.CTkFont(size=16, weight="bold"),
                     command=self.register_student).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Clear Form", width=150, height=50,
                     fg_color="#555555", command=self.clear_add_form).pack(side="left", padx=20)

    def clear_add_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("0.0", "end")
            elif hasattr(widget, "delete"):
                widget.delete(0, "end")
            elif hasattr(widget, "set"):
                widget.set("Select Gender" if key == "gender" else "Select Course" if key == "course" else "")

    def validate_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email)

    def register_student(self):
        # (Your existing working code - unchanged)
        try:
            name = self.entries["name"].get().strip()
            email = self.entries["email"].get().strip().lower()
            phone = self.entries["phone"].get().strip()
            age = self.entries["age"].get().strip()
            gender = self.entries["gender"].get()
            course = self.entries["course"].get()
            address = self.entries["address"].get("0.0", "end").strip()

            if not all([name, email, gender != "Select Gender", course != "Select Course"]):
                messagebox.showerror("Error", "All fields are required!")
                return
            if not self.validate_email(email):
                messagebox.showerror("Error", "Invalid email format!")
                return
            if age and (not age.isdigit() or int(age) < 15 or int(age) > 100):
                messagebox.showerror("Error", "Age must be 15-100")
                return

            conn = sqlite3.connect("students.db")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (name, email, phone, age, gender, course, address, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, age or None, gender, course, address, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"{name} registered successfully!")
            self.clear_add_form()
            self.show_view_frame()

        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "This email is already registered!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_view_frame(self):
        self.clear_content()
        self.view_btn.configure(fg_color=("gray75", "gray25"))
        self.add_btn.configure(fg_color="transparent")

        frame = ctk.CTkFrame(self.content_frame)
        frame.grid(row=0, column=0, sticky="nswe")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Title + Search
        top_frame = ctk.CTkFrame(frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        ctk.CTkLabel(top_frame, text="All Registered Students", font=ctk.CTkFont(size=26, weight="bold")).pack(side="left", padx=10)
        
        search_frame = ctk.CTkFrame(top_frame)
        search_frame.pack(side="right")
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=300, height=40)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", self.search_students)
        ctk.CTkButton(search_frame, text="Refresh", width=100, command=self.load_students).pack(side="left", padx=5)

        # Beautiful Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#2a2d2e",
                        foreground="white",
                        rowheight=40,
                        fieldbackground="#2a2d2e",
                        font=("Segoe UI", 11))
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"), foreground="#1f6aa5")
        style.map("Treeview", background=[('selected', '#1f6aa5')])

        columns = ("ID", "Name", "Email", "Phone", "Age", "Gender", "Course", "Date")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", style="Treeview")

        # Column settings - WIDE & CLEAR
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Full Name")
        self.tree.heading("Email", text="Email Address")
        self.tree.heading("Phone", text="Phone")
        self.tree.heading("Age", text="Age")
        self.tree.heading("Gender", text="Gender")
        self.tree.heading("Course", text="Course")
        self.tree.heading("Date", text="Registered On")

        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("Name", width=200, anchor="w")
        self.tree.column("Email", width=280, anchor="w")
        self.tree.column("Phone", width=140, anchor="center")
        self.tree.column("Age", width=80, anchor="center")
        self.tree.column("Gender", width=100, anchor="center")
        self.tree.column("Course", width=300, anchor="w")
        self.tree.column("Date", width=160, anchor="center")

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=1, column=0, sticky="nswe")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=2, column=0, pady=15)
        ctk.CTkButton(btn_frame, text="Edit Selected", fg_color="#1f6aa5", width=150, height=45, command=self.edit_student).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Delete Selected", fg_color="red", hover_color="darkred", width=150, height=45, command=self.delete_student).pack(side="left", padx=10)

        # Tag for alternating row colors
        self.tree.tag_configure("oddrow", background="#2f3235")
        self.tree.tag_configure("evenrow", background="#272a2d")

        self.load_students()

    def load_students(self, search_query=""):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        query = "SELECT id, name, email, phone, age, gender, course, registration_date FROM students"
        params = []
        if search_query:
            query += " WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR course LIKE ?"
            like_query = f"%{search_query}%"
            params = [like_query] * 4

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        for i, row in enumerate(rows):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.tree.insert("", "end", values=row, tags=(tag,))

    def search_students(self, event=None):
        self.load_students(self.search_var.get())

    def edit_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Student", "Please select a student to edit")
            return
        item = self.tree.item(selected[0])
        student_id = item['values'][0]
        self.edit_window(student_id)

    def edit_window(self, student_id):
        # You can implement full edit form here later
        messagebox.showinfo("Edit", f"Edit functionality for Student ID: {student_id}\n(Will be added in next version)")

    def delete_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a student to delete")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this student?"):
            student_id = self.tree.item(selected[0])['values'][0]
            conn = sqlite3.connect("students.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
            conn.commit()
            conn.close()
            self.load_students()
            messagebox.showinfo("Deleted", "Student record deleted successfully!")

# Run the app
if __name__ == "__main__":
    app = StudentRegistrationSystem()
    app.mainloop()