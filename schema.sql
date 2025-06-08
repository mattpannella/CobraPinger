CREATE TABLE IF NOT EXISTS channel (
    id INTEGER PRIMARY KEY,
    youtube_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video (
    id INTEGER PRIMARY KEY,
    youtube_id TEXT UNIQUE NOT NULL,
    channel_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    youtube_created_at TEXT NOT NULL,
    thumbnail_url TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channel(id)
);

CREATE TABLE IF NOT EXISTS transcript (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS transcript_search USING fts5(
    content,
    content='transcript',
    content_rowid='id'
);

CREATE TRIGGER transcript_ai AFTER INSERT ON transcript BEGIN
  INSERT INTO transcript_search(rowid, content)
  VALUES (new.id, new.content);
END;

CREATE TABLE IF NOT EXISTS summary (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
);

CREATE TABLE IF NOT EXISTS topic (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS video_topic (
    video_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    PRIMARY KEY (video_id, topic_id),
    FOREIGN KEY (video_id) REFERENCES video(id),
    FOREIGN KEY (topic_id) REFERENCES topic(id)
);

CREATE TABLE IF NOT EXISTS quote (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
);

CREATE TABLE IF NOT EXISTS invite_code (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    used BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS video_comment (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (video_id) REFERENCES video(id)
);

CREATE TABLE IF NOT EXISTS login_attempt (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS video_embedding (
    video_id INTEGER PRIMARY KEY,
    embedding TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
);

CREATE INDEX IF NOT EXISTS idx_login_attempt_username_time
ON login_attempt(username, created_at);

CREATE TABLE IF NOT EXISTS advisor (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS advisor_video_note (
    advisor_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (advisor_id, video_id),
    FOREIGN KEY (advisor_id) REFERENCES advisor(id),
    FOREIGN KEY (video_id) REFERENCES video(id)
);

INSERT INTO advisor (key, name) VALUES ('clint', 'Clint');
INSERT INTO advisor (key, name) VALUES ('financial', 'Financial Advisor');
INSERT INTO advisor (key, name) VALUES ('police', 'Police Advisor');
INSERT INTO advisor (key, name) VALUES ('health', 'Health Advisor');
INSERT INTO advisor (key, name) VALUES ('fire', 'Fire Marshall');
INSERT INTO advisor (key, name) VALUES ('education', 'Education Advisor');
INSERT INTO advisor (key, name) VALUES ('transit', 'Transit Advisor');