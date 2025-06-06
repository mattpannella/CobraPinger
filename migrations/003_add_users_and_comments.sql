-- Add invite code table
CREATE TABLE IF NOT EXISTS invite_code (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    used BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add user table
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add comments table
CREATE TABLE IF NOT EXISTS video_comment (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (video_id) REFERENCES video(id)
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_video_comment_user 
ON video_comment(user_id);

CREATE INDEX IF NOT EXISTS idx_video_comment_video 
ON video_comment(video_id);

CREATE INDEX IF NOT EXISTS idx_invite_code_used 
ON invite_code(used);