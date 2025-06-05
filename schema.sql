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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    thumbnail_url TEXT,
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

-- Add unique index for video_topic pairs
CREATE UNIQUE INDEX IF NOT EXISTS idx_video_topic_unique 
ON video_topic(video_id, topic_id);

CREATE TABLE IF NOT EXIST quote {
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
}