CREATE TABLE IF NOT EXISTS video_embedding (
    video_id INTEGER PRIMARY KEY,
    embedding TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES video(id)
);
