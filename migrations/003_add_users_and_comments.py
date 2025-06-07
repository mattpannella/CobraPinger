import sqlite3
import os

def migrate(db_path):
    print("Running migration 003: Adding user authentication and comments...")
    
    # Read the SQL file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(current_dir, '003_add_users_and_comments.sql')
    
    with open(sql_file, 'r') as file:
        sql = file.read()
    
    # Connect and execute
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()
    
    print("Migration 003 completed successfully")

if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(current_dir), 'db.sqlite')
    migrate(db_path)