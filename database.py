import sqlite3
import os
import re
import secrets
import json
from markupsafe import escape

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
        """Store video summary in database and extract quote if present."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            #store summary
            cursor.execute(
                "INSERT INTO summary (video_id, content) VALUES (?, ?)",
                (video_id, content)
            )
            
            #extract and store quote if present
            pattern = r'\*\*"([^"]+)"\*\*'
            matches = re.finditer(pattern, content)
            for match in matches:
                quote = match.group(1)
                cursor.execute(
                    "INSERT INTO quote (video_id, content) VALUES (?, ?)",
                    (video_id, quote)
                )
            
            conn.commit()

    def store_embedding(self, video_id: int, embedding: list[float]) -> None:
        """Store embedding vector for a video."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO video_embedding (video_id, embedding) VALUES (?, ?)",
                (video_id, json.dumps(embedding))
            )
            conn.commit()

    def get_embedding(self, video_id: int) -> list[float] | None:
        """Retrieve embedding vector for a video."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT embedding FROM video_embedding WHERE video_id = ?",
                (video_id,)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

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
        """Search videos by transcript content with pagination."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            #sanitize the search query
            safe_query = self._sanitize_fts_query(query)
            
            if not safe_query:
                return {
                    'results': [],
                    'total': 0,
                    'pages': 0
                }
            
            cursor.execute("""
                SELECT COUNT(*)
                FROM transcript_search
                WHERE transcript_search MATCH ?
            """, (safe_query,))
            total_count = cursor.fetchone()[0]
            
            offset = (page - 1) * per_page
            
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    s.content as summary,
                    snippet(transcript_search, 0, '<mark class="bg-warning">', '</mark>', '...', 50) as context
                FROM transcript_search
                JOIN video v ON transcript_search.rowid = v.id
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN summary s ON v.id = s.video_id
                WHERE transcript_search MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """, (safe_query, per_page, offset))
            
            return {
                'results': [dict(row) for row in cursor.fetchall()],
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }

    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitize FTS query to prevent injection and handle special characters."""
        if not query:
            return ""
            
        #remove special characters
        special_chars = ['"', "'", '-', '+', '*', '(', ')', '~', '^', ':', '\\', ';']
        for char in special_chars:
            query = query.replace(char, ' ')
        
        query = ' '.join(query.split())
        
        #escape any remaining special characters
        query = query.replace('"', '""')
        
        #wrap in quotes to treat as phrase
        return f'"{query}"' if query else ""

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

    def get_videos_without_transcript(self) -> list:
        """Get all videos that don't have transcripts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    c.id as channel_id,
                    v.youtube_created_at
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN transcript t ON v.id = t.video_id
                WHERE t.content IS NULL
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_videos_without_summary(self) -> list:
        """Get all videos that have transcripts but no summaries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.id,
                    v.youtube_id,
                    v.title,
                    c.name as channel_name,
                    c.id as channel_id,
                    c.youtube_id as youtube_channel_id,
                    v.youtube_created_at,
                    t.content as transcript
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                JOIN transcript t ON v.id = t.video_id
                LEFT JOIN summary s ON v.id = s.video_id
                WHERE s.content IS NULL OR s.video_id IS NULL
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_topic_counts(self):
        """Get all topics and their video counts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name, COUNT(vt.video_id) as count
                FROM topic t
                LEFT JOIN video_topic vt on t.id = vt.topic_id
                GROUP BY t.id, t.name
                ORDER BY count DESC
            """)
            return cursor.fetchall()

    def get_video_quote(self, video_id):
        """Get quote for a specific video."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content 
                FROM quote 
                WHERE video_id = ?
            ''', (video_id,))
            result = cursor.fetchone()
            return result['content'] if result else None

    def get_random_quote(self):
        """Get a random quote with its video details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    q.content as quote,
                    v.id as video_id,
                    v.title,
                    c.name as channel_name
                FROM quote q
                JOIN video v ON q.video_id = v.id
                JOIN channel c ON v.channel_id = c.id
                ORDER BY RANDOM()
                LIMIT 1
            """)
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_latest_video(self):
        """Get the most recently published video with all its details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.id,
                    v.title,
                    v.youtube_id,
                    v.youtube_created_at,
                    v.thumbnail_url,
                    c.name as channel_name,
                    c.id as channel_id,
                    s.content as summary
                FROM video v
                JOIN channel c ON v.channel_id = c.id
                LEFT JOIN summary s ON v.id = s.video_id
                ORDER BY v.youtube_created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_all_videos_with_transcripts(self):
        """Get all videos that have transcripts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.id,
                    v.title,
                    v.youtube_id,
                    t.content as transcript
                FROM video v
                JOIN transcript t ON v.id = t.video_id
                ORDER BY v.youtube_created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def clear_all_topics(self):
        """Remove all topic links and topics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clear the mapping table first (due to foreign key constraints)
            cursor.execute("DELETE FROM video_topic")
            # Then clear the topics table
            cursor.execute("DELETE FROM topic")
            conn.commit()

    def get_all_topics(self):
        """Get all existing topics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM topic ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def clear_topic_links(self):
        """Clear only the video-topic mappings, keeping the topics themselves."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_topic")
            conn.commit()

    def seed_topics(self):
        """Seed the topic table with predefined topics."""
        seed_topics = [
            "food hacks", "beer", "alcohol", "mead", "trolls", 
            "jessica boyle", "guitar", "ozzy osbourne", "magic", 
            "gender relations", "politics", "puff", "warlord", 
            "drink combos", "bacon", "youtube", "food review", 
            "drink review", "wand making", "jokes", "farting", 
            "video response", "music"
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # First clear existing topics
            cursor.execute("DELETE FROM video_topic")
            cursor.execute("DELETE FROM topic")
            
            # Insert seed topics
            cursor.executemany(
                "INSERT INTO topic (name) VALUES (?)",
                [(topic.lower(),) for topic in seed_topics]
            )
            conn.commit()
            
            # Verify count
            cursor.execute("SELECT COUNT(*) FROM topic")
            count = cursor.fetchone()[0]
            return count

    def validate_invite_code(self, code: str) -> bool:
        """Check if invite code is valid and unused."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM invite_code WHERE code = ? AND used = 0",
                (code,)
            )
            return cursor.fetchone() is not None

    def mark_invite_code_used(self, code: str) -> None:
        """Mark an invite code as used."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE invite_code SET used = 1 WHERE code = ?",
                (code,)
            )
            conn.commit()

    def create_user(self, username: str, email: str, password_hash: str) -> int:
        """Create a new user and return their ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            return cursor.lastrowid
        
    def can_generate_invite_code(self, daily_limit: int = 30) -> bool:
        """Check if we can generate more invite codes today."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM invite_code 
                WHERE date(created_at) = date('now')
            """)
            count = cursor.fetchone()[0]
            return count < daily_limit

    def generate_invite_code(self, daily_limit: int = 30) -> tuple[bool, str]:
        """Generate a new invite code if within daily limit."""
        if not self.can_generate_invite_code(daily_limit):
            return False, "Daily invite code limit reached"
        
        code = secrets.token_urlsafe(16)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO invite_code (code) VALUES (?)",
                (code,)
            )
            conn.commit()
        
        return True, code
    
    def get_user_by_username(self, username: str):
        """Get user by username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, password_hash FROM user WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_user_by_id(self, user_id: int):
        """Get user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email FROM user WHERE id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def can_user_comment(self, user_id: int) -> bool:
        """Check if user can comment (5 minute rate limit)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM video_comment 
                WHERE user_id = ? 
                AND datetime(created_at) > datetime('now', '-5 minutes')
            """, (user_id,))
            count = cursor.fetchone()[0]
            return count == 0

    def add_comment(self, user_id: int, video_id: int, content: str) -> bool:
        """Add a comment if user is within rate limit."""
        if not self.can_user_comment(user_id):
            return False
            
        # Escape HTML in comments
        safe_content = escape(content)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO video_comment (user_id, video_id, content) VALUES (?, ?, ?)",
                (user_id, video_id, safe_content)
            )
            conn.commit()
            return True

    def get_video_comments(self, video_id: int):
        """Get all comments for a video with user info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.*,
                    u.username
                FROM video_comment c
                JOIN user u ON c.user_id = u.id
                WHERE c.video_id = ?
                ORDER BY c.created_at DESC
            """, (video_id,))
            return [dict(row) for row in cursor.fetchall()]

    def check_login_attempts(self, username: str) -> bool:
        """Check if user has too many failed login attempts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM login_attempt 
                WHERE username = ? 
                AND datetime(created_at) > datetime('now', '-15 minutes')
                AND success = 0
            """, (username,))
            count = cursor.fetchone()[0]
            return count < 5  # Allow 5 attempts per 15 minutes

    def record_login_attempt(self, username: str, success: bool) -> None:
        """Record a login attempt."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO login_attempt (username, success) VALUES (?, ?)",
                (username, success)
            )
            conn.commit()