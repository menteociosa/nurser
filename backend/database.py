import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "nurser.db")


def get_db():
    """Return a sqlite3 connection with row_factory set to Row."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL,
        phone_verified INTEGER NOT NULL DEFAULT 0,
        otp_code TEXT,
        otp_expires_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        team_notices TEXT,
        created_by TEXT NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS team_memberships (
        id TEXT PRIMARY KEY,
        team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'contributor' CHECK(role IN ('admin','contributor','viewer')),
        joined_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(team_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS event_types (
        id TEXT PRIMARY KEY,
        team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        field_type TEXT NOT NULL CHECK(field_type IN ('boolean','dropdown','numeric','multi_select','text','timestamp_event')),
        options TEXT,
        icon TEXT,
        color TEXT,
        is_header INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        caregiver_id TEXT NOT NULL REFERENCES users(id),
        event_type_id TEXT NOT NULL REFERENCES event_types(id),
        event_value TEXT,
        timestamp TEXT NOT NULL,
        note TEXT,
        recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS invite_codes (
        id TEXT PRIMARY KEY,
        team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        code TEXT UNIQUE NOT NULL,
        created_by TEXT NOT NULL REFERENCES users(id),
        role TEXT NOT NULL DEFAULT 'contributor' CHECK(role IN ('admin','contributor','viewer')),
        max_uses INTEGER DEFAULT 1,
        use_count INTEGER NOT NULL DEFAULT 0,
        expires_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_events_team ON events(team_id);
    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(team_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_team_memberships_user ON team_memberships(user_id);
    CREATE INDEX IF NOT EXISTS idx_team_memberships_team ON team_memberships(team_id);
    CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code);
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")
