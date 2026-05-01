import sqlite3
import csv
import os
import shutil
from pathlib import Path


def build_database_from_csv(db_path: str = "survival_data.db") -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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
        conn.close()
        return

    with open(csv_filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute(
                'INSERT INTO guides (category, title, content, tags) VALUES (?, ?, ?, ?)',
                (row['category'], row['title'], row['content'], row['tags']),
            )

    conn.commit()
    conn.close()
    print(f"Success: 'survival_data.db' built from {csv_filename}.")

    assets_copy = Path("assets") / "survival_data.db"
    if assets_copy.parent.exists():
        shutil.copy2(db_path, assets_copy)
        print(f"Copied to {assets_copy} for bundling.")


if __name__ == "__main__":
    build_database_from_csv()
