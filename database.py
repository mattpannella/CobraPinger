import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_database(self) -> bool:
        """Creates the SQLite DB file if it doesn't exist."""
        if os.path.exists(self.db_path):
            print(f"Database already exists at {self.db_path}")
            return False
        else:
            with sqlite3.connect(self.db_path):
                pass
            print(f"Database created at {self.db_path}")
            return True

    def build_schema(self, schema_file_path: str) -> None:
        """Builds the DB schema from a .sql file if the tables don't already exist."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at {self.db_path}")
        
        if not os.path.exists(schema_file_path):
            raise FileNotFoundError(f"Schema file not found at {schema_file_path}")

        with sqlite3.connect(self.db_path) as conn, open(schema_file_path, 'r') as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)
            print(f"Schema applied from {schema_file_path}")

    def get_or_create_channel(self, youtube_id: str, name: str) -> int:
        """Get channel ID from database or create if it doesn't exist yet"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM channel WHERE youtube_id = ?",
                (youtube_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            cursor.execute(
                "INSERT INTO channel (youtube_id, name) VALUES (?, ?)",
                (youtube_id, name)
            )
            conn.commit()
            return cursor.lastrowid

    def store_video(self, youtube_id: str, channel_id: int, title: str) -> int:
        """Store video in database and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO video (youtube_id, channel_id, title) VALUES (?, ?, ?)",
                (youtube_id, channel_id, title)
            )
            conn.commit()
            
            cursor.execute("SELECT id FROM video WHERE youtube_id = ?", (youtube_id,))
            return cursor.fetchone()[0]

    def store_transcript(self, video_id: int, content: str) -> None:
        """Store video transcript in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transcript (video_id, content) VALUES (?, ?)",
                (video_id, content)
            )
            conn.commit()

    def store_summary(self, video_id: int, content: str) -> None:
        """Store video summary in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO summary (video_id, content) VALUES (?, ?)",
                (video_id, content)
            )
            conn.commit()

    def get_or_create_topic(self, topic_name: str) -> int:
        """Get topic ID from database or create if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM topic WHERE name = ?",
                (topic_name.lower(),)  # Store topics in lowercase for consistency
            )
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            cursor.execute(
                "INSERT INTO topic (name) VALUES (?)",
                (topic_name.lower(),)
            )
            conn.commit()
            return cursor.lastrowid

    def link_video_topics(self, video_id: int, topic_ids: list[int]) -> None:
        """Link a video to multiple topics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO video_topic (video_id, topic_id) VALUES (?, ?)",
                [(video_id, topic_id) for topic_id in topic_ids]
            )
            conn.commit()