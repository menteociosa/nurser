import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_TS_DEFAULT = "to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS')"


def _connect():
    return psycopg2.connect(
        host=os.getenv("postgress_host"),
        port=int(os.getenv("postgress_port", 5432)),
        user=os.getenv("postgress_user"),
        password=os.getenv("postgress_password"),
        dbname=os.getenv("postgress_db"),
    )


class _Db:
    """Wraps a psycopg2 connection with a SQLite-compatible execute() interface.

    Automatically converts SQLite-style ``?`` placeholders to psycopg2 ``%s``
    so all existing route code works without modification.
    """

    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql, params=None):
        self._cur.execute(sql.replace("?", "%s"), params)
        return self._cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._cur.close()
        self._conn.close()


def get_db() -> _Db:
    """Return a database wrapper connected to PostgreSQL."""
    return _Db(_connect())


def init_db():
    """Create all tables if they don't exist."""
    conn = _connect()
    cur = conn.cursor()

    statements = [
        f"""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            phone_verified INTEGER NOT NULL DEFAULT 0,
            otp_code TEXT,
            otp_expires_at TEXT,
            created_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT})
        )""",
        f"""CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            team_notices TEXT,
            created_by TEXT NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT})
        )""",
        f"""CREATE TABLE IF NOT EXISTS team_memberships (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'contributor' CHECK(role IN ('admin','contributor','viewer')),
            joined_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT}),
            UNIQUE(team_id, user_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS event_types (
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
            created_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT})
        )""",
        f"""CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            caregiver_id TEXT NOT NULL REFERENCES users(id),
            event_type_id TEXT NOT NULL REFERENCES event_types(id),
            event_value TEXT,
            timestamp TEXT NOT NULL,
            note TEXT,
            recorded_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT})
        )""",
        f"""CREATE TABLE IF NOT EXISTS invite_codes (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            code TEXT UNIQUE NOT NULL,
            created_by TEXT NOT NULL REFERENCES users(id),
            invited_phone TEXT,
            role TEXT NOT NULL DEFAULT 'contributor' CHECK(role IN ('admin','contributor','viewer')),
            max_uses INTEGER DEFAULT 1,
            use_count INTEGER NOT NULL DEFAULT 0,
            expires_at TEXT,
            created_at TEXT NOT NULL DEFAULT ({_TS_DEFAULT})
        )""",
        "CREATE INDEX IF NOT EXISTS idx_events_team ON events(team_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(team_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_team_memberships_user ON team_memberships(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_team_memberships_team ON team_memberships(team_id)",
        "CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code)",
        # Migration: add invited_phone if missing (safe to re-run)
        """DO $$ BEGIN
            ALTER TABLE invite_codes ADD COLUMN invited_phone TEXT;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$""",
    ]

    for stmt in statements:
        cur.execute(stmt)

    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully.")
