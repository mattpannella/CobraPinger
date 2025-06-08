#!/usr/bin/env python3
# filepath: /Users/mattpannella/development/python/CobraPinger/apply_schema.py

import sqlite3
import os
import sys

def apply_schema(db_path, schema_path):
    """
    Applies SQL schema to an existing SQLite database
    
    Args:
        db_path (str): Path to existing SQLite database
        schema_path (str): Path to SQL schema file
    """
    if not os.path.isfile(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return False
        
    if not os.path.isfile(schema_path):
        print(f"Error: Schema file '{schema_path}' not found!")
        return False
    
    try:
        # Read schema file
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Connect to the existing database
        print(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Fix syntax errors in the schema file
        schema_sql = schema_sql.replace("CREATE TABLE IF NOT EXIST quote", 
                                      "CREATE TABLE IF NOT EXISTS quote")
        schema_sql = schema_sql.replace(")",");")
        
        # Remove trailing comma in login_attempt table definition
        schema_sql = schema_sql.replace("created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,", 
                                      "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        
        # Execute the schema statements
        print("Applying schema...")
        cursor.executescript(schema_sql)
        conn.commit()
        
        print("Schema applied successfully!")
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "db.sqlite")
    schema_path = os.path.join(script_dir, "schema.sql")
    
    # Allow custom paths via command line args
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        schema_path = sys.argv[2]
    
    apply_schema(db_path, schema_path)