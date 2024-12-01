import sqlite3

# Connect to SQLite database (creates a file named 'organ_donation.db')
connection = sqlite3.connect('organ_donation.db')
cursor = connection.cursor()

# Create donors table with age column
cursor.execute('''
    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT,
        password TEXT,
        blood_type TEXT,
        organ TEXT,
        longitude REAL,
        latitude REAL,
        age INTEGER,  -- New age column added
        hla_type TEXT  -- New HLA type column added
    )
''')

# Create recipients table with age column
cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT,
        password TEXT,
        blood_type TEXT,
        needed_organ TEXT,
        urgency_level INTEGER,
        longitude REAL,
        latitude REAL,
        age INTEGER,  -- New age column added
        hla_type TEXT  -- New HLA type column added
    )
''')

connection.commit()
connection.close()