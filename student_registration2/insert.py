# insert_50_indian_students.py
# 100% Indian names, realistic courses, cities, phones – feels completely human-written
import sqlite3
import random

# Real Indian names – very common in colleges across India
indian_names = [
    "Aarav Sharma", "Vihaan Patel", "Arjun Singh", "Reyansh Gupta", "Sai Reddy", "Krishna Kumar", "Aditya Verma", 
    "Ayaan Joshi", "Ishaan Mehta", "Dhruv Nair", "Aryan Desai", "Kabir Malhotra", "Rudra Iyer", "Shaurya Rao",
    "Saanvi Sharma", "Aadhya Patel", "Diya Singh", "Ananya Gupta", "Pari Reddy", "Avni Kumar", "Myra Verma",
    "Sia Joshi", "Kiara Mehta", "Aarohi Nair", "Zara Khan", "Isha Desai", "Riya Malhotra", "Navya Rao", "Sara Ahmed",
    "Priyanka Yadav", "Sneha Choudhary", "Tanvi Singh", "Rohan Kapoor", "Neha Dubey", "Rahul Tiwari", "Pooja Mishra",
    "Vikram Pratap Singh", "Anjali Pandey", "Siddharth Trivedi", "Meera Agarwal", "Karan Thakur", "Shreya Saxena",
    "Yash Rajput", "Aditi Chauhan", "Nikhil Bharadwaj", "Simran Kaur", "Atharva More", "Jhanvi Shetty", "Omkar Jadhav"
]

courses = [
    "B.Tech Computer Science", "B.Tech Electronics & Communication", "B.Tech Mechanical Engineering",
    "B.Tech Civil Engineering", "B.Sc Biotechnology", "BBA", "B.Com (Hons)", "MBBS", "BDS", "B.Pharm",
    "BCA", "B.Sc Data Science", "BA Psychology", "B.Tech Information Technology", "B.Arch", "B.Sc Nursing"
]

cities = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", 
    "Lucknow", "Indore", "Bhopal", "Patna", "Coimbatore", "Nagpur", "Visakhapatnam", "Kanpur", "Surat"
]

print("Inserting 50 authentic Indian student records...\n")

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

# Create table if not exists
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

used_emails = set()
inserted = 0

while inserted < 50:
    name = random.choice(indian_names)
    
    # Very Indian-style email patterns
    patterns = [
        name.lower().replace(" ", "."),
        name.lower().replace(" ", "") + str(random.randint(10,999)),
        name.split()[0].lower() + "." + name.split()[1].lower() + str(random.randint(0,99)),
        name.lower().replace(" ", "_") + str(random.randint(100,9999))
    ]
    email = random.choice(patterns) + random.choice(["@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com"])
    
    if email in used_emails:
        continue
    used_emails.add(email)
    
    phone = random.choice(["98", "99", "97", "96", "88", "79", "90", "85"]) + "".join([str(random.randint(0,9)) for _ in range(8)])
    age = random.randint(17, 25)
    gender = "Male" if any(x in name for x in ["Aarav","Vihaan","Arjun","Reyansh","Sai","Aditya","Ayaan","Ishaan","Dhruv","Aryan","Kabir","Rudra","Shaurya","Rohan","Rahul","Vikram","Siddharth","Karan","Yash","Atharva","Omkar","Nikhil"]) else "Female"
    course = random.choice(courses)
    address = f"Flat No. {random.randint(101,999)}, {random.choice(['Sai', 'Shree', 'Om', 'Ganesh', 'Laxmi', 'Surya', 'Anand'])} Residency, {random.choice(cities)}, Maharashtra {random.randint(400001,422999)}"
    reg_date = f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d} 1{random.randint(0,9)}:{random.randint(10,59):02d}"

    try:
        cursor.execute('''
            INSERT INTO students (name, email, phone, age, gender, course, address, registration_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, age, gender, course, address, reg_date))
        
        inserted += 1
        print(f"{inserted:2d}. {name:<25} → {course:<40} → {email}")
        
    except sqlite3.IntegrityError:
        continue  # rare duplicate email

conn.commit()
conn.close()

print("\n50 genuine Indian student records inserted successfully!")
print("Your app now looks like a real Indian college database!")