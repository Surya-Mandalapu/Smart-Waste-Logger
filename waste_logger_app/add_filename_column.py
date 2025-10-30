import sqlite3

# Path to your SQLite database file
DB_PATH = "waste_log.db"

def add_filename_column():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Add the filename column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE waste_logs ADD COLUMN filename TEXT;")
        print("Column 'filename' added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'filename' already exists.")
        else:
            print(f"Error: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_filename_column()
