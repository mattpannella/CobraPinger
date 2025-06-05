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

    def store_video(self, youtube_id: str, channel_id: int, title: str, published_date: str, thumbnail_url: str = None) -> int:
        """Store video in database and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO video 
                (youtube_id, channel_id, title, youtube_created_at, thumbnail_url) 
                VALUES (?, ?, ?, ?, ?)
            """, (youtube_id, channel_id, title, published_date, thumbnail_url))
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

            topic_name = topic_name.lower().strip()
            
            cursor.execute("SELECT id FROM topic WHERE TRIM(name) = ?", (topic_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            cursor.execute(
                "INSERT INTO topic (name) VALUES (?)",
                (topic_name,)
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

    def get_all_videos(self, page: int = 1, per_page: int = 10, channel_ids: list[int] = None):
        """Get paginated list of videos with their channels and summaries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            count_query = """
                SELECT COUNT(*) 
                FROM video v 
                JOIN channel c ON v.channel_id = c.id
            """
            count_params = []
            if channel_ids:
                placeholders = ','.join('?' * len(channel_ids))
                count_query += f" WHERE v.channel_id IN ({placeholders})"
                count_params.extend(channel_ids)
                
            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()[0]
            
            offset = (page - 1) * per_page

            query = """
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    s.content as summary,
                    v.thumbnail_url,
                    v.youtube_created_at
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN summary s ON v.id = s.video_id
            """

            params = []
            if channel_ids:
                placeholders = ','.join('?' * len(channel_ids))
                query += f" WHERE v.channel_id IN ({placeholders})"
                params.extend(channel_ids)

            query += " ORDER BY v.youtube_created_at DESC LIMIT ? OFFSET ?"
            params.extend([per_page, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return {
                'videos': [dict(row) for row in rows],
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }

    def get_video_details(self, video_id: int):
        """Get complete details for a single video."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    t.content as transcript,
                    s.content as summary,
                    v.youtube_created_at
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN transcript t ON v.id = t.video_id
                LEFT JOIN summary s ON v.id = s.video_id
                WHERE v.id = ?
            """, (video_id,))
            video_data = cursor.fetchone()
            
            cursor.execute("""
                SELECT t.name
                FROM topic t
                JOIN video_topic vt ON t.id = vt.topic_id
                WHERE vt.video_id = ?
            """, (video_id,))
            topics = [row[0] for row in cursor.fetchall()]
            
            if video_data:
                return {
                    'id': video_data[0],
                    'youtube_id': video_data[1],
                    'title': video_data[2],
                    'channel_name': video_data[3],
                    'transcript': video_data[4],
                    'summary': video_data[5],
                    'youtube_created_at': video_data[6],
                    'topics': topics
                }
            return None

    def search_videos(self, query: str, page: int = 1, per_page: int = 10):
        """Search videos by transcript content."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    s.content as summary,
                    snippet(transcript_search, 0, '[highlight]', '[/highlight]', '...', 50) as context
                FROM transcript_search
                JOIN video v ON transcript_search.rowid = v.id
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN summary s ON v.id = s.video_id
                WHERE transcript_search MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """, (query, per_page, offset))
            return cursor.fetchall()

    def get_topic_id(self, topic_name: str) -> int:
        """Get topic ID from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            #trim whitespace and convert to lowercase for comparison
            cursor.execute("SELECT id FROM topic WHERE TRIM(name) = TRIM(?)", (topic_name.lower(),))
            result = cursor.fetchone()
                
            return result[0] if result else None

    def get_videos_by_topic(self, topic_id: int, page: int = 1, per_page: int = 10):
        """Get paginated list of videos for a specific topic."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM video v
                JOIN video_topic vt ON v.id = vt.video_id
                WHERE vt.topic_id = ?
            """, (topic_id,))
            total_count = cursor.fetchone()[0]
            
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    s.content as summary,
                    v.thumbnail_url
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                JOIN video_topic vt ON v.id = vt.video_id
                LEFT JOIN summary s ON v.id = s.video_id
                WHERE vt.topic_id = ?
                ORDER BY v.youtube_created_at DESC
                LIMIT ? OFFSET ?
            """, (topic_id, per_page, offset))
            rows = cursor.fetchall()
            return {
                'videos': [dict(row) for row in rows],
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }

    def video_exists(self, youtube_id: str) -> bool:
        """Check if a video already exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM video WHERE youtube_id = ?", (youtube_id,))
            return cursor.fetchone() is not None

    def get_all_channels(self):
        """Get list of all channels."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM channel ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_videos_by_date(self, year: int, month: int):
        """Get all videos for a specific month."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # SQLite strftime returns single digit for month, so we pad with 0
            date_pattern = f"{year}-{month:02d}-%"
            
            cursor.execute("""
                SELECT 
                    v.id,
                    v.title,
                    v.youtube_created_at,
                    c.name as channel_name
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                WHERE v.youtube_created_at LIKE ?
                ORDER BY v.youtube_created_at ASC
            """, (date_pattern,))
            
            return [dict(row) for row in cursor.fetchall()]