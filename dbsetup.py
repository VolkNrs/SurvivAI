import sqlite3
import csv
import os

def build_database_from_csv():
    conn = sqlite3.connect("survival_data.db")
    cursor = conn.cursor()

    # main
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT
        )
    ''')

   
    cursor.execute('DELETE FROM guides')

    
    csv_filename = "aigen_large_data.csv"
    
    if not os.path.exists(csv_filename):
        print(f"Error: Could not find {csv_filename}. Make sure it is in the same folder!")
        return

    with open(csv_filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file) 
        
        for row in reader:
            cursor.execute('''
                INSERT INTO guides (category, title, content, tags)VALUES (?, ?, ?, ?)''', (row['category'], row['title'], row['content'], row['tags']))

    
    conn.commit()
    conn.close()
    print(f"Success: Pipeline complete! 'survival_data.db' was built using {csv_filename}.")

if __name__ == "__main__":
    build_database_from_csv()