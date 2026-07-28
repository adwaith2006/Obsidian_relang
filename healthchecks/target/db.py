import sqlite3
import uuid
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "healthchecks.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        theme TEXT DEFAULT 'dark',
        reports TEXT DEFAULT 'daily',
        api_key TEXT
    );

    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        api_key TEXT NOT NULL,
        ping_key TEXT NOT NULL,
        badge_key TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE NOT NULL,
        project_id TEXT NOT NULL,
        name TEXT DEFAULT '',
        slug TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        desc TEXT,
        timeout INTEGER DEFAULT 86400,
        grace INTEGER DEFAULT 3600,
        schedule TEXT,
        tz TEXT DEFAULT 'UTC',
        status TEXT DEFAULT 'new',
        n_pings INTEGER DEFAULT 0,
        last_ping TEXT,
        next_ping TEXT,
        manual_resume INTEGER DEFAULT 0,
        methods TEXT DEFAULT '',
        subject TEXT DEFAULT '',
        subject_fail TEXT DEFAULT '',
        start_kw TEXT DEFAULT '',
        success_kw TEXT DEFAULT '',
        failure_kw TEXT DEFAULT '',
        filter_body INTEGER DEFAULT 0,
        filter_subject INTEGER DEFAULT 0,
        filter_http_body INTEGER DEFAULT 0,
        filter_default_fail INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        channels TEXT DEFAULT '',
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS pings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_uuid TEXT NOT NULL,
        n INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        scheme TEXT DEFAULT 'http',
        remote_addr TEXT DEFAULT '127.0.0.1',
        method TEXT DEFAULT 'GET',
        ua TEXT DEFAULT 'curl/7.68.0',
        body TEXT DEFAULT '',
        kind TEXT DEFAULT 'success',
        exit_status INTEGER,
        FOREIGN KEY(check_uuid) REFERENCES checks(uuid)
    );

    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE NOT NULL,
        project_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        value TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS csrf_tokens (
        token TEXT PRIMARY KEY,
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def reset_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
    DROP TABLE IF EXISTS pings;
    DROP TABLE IF EXISTS checks;
    DROP TABLE IF EXISTS channels;
    DROP TABLE IF EXISTS sessions;
    DROP TABLE IF EXISTS csrf_tokens;
    DROP TABLE IF EXISTS projects;
    DROP TABLE IF EXISTS users;
    """)
    conn.commit()
    conn.close()

    init_db()

    conn = get_db()
    cursor = conn.cursor()
    # Seed Alice
    cursor.execute(
        "INSERT INTO users (id, email, password, theme, reports, api_key) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "alice@example.org", "password", "dark", "daily", "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    )
    # Seed Bob
    cursor.execute(
        "INSERT INTO users (id, email, password, theme, reports, api_key) VALUES (?, ?, ?, ?, ?, ?)",
        (2, "bob@example.org", "password", "dark", "daily", "BOBXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    )

    # Seed Alice's Project
    alice_project_id = "00000000-0000-0000-0000-000000000001"
    cursor.execute(
        "INSERT INTO projects (id, user_id, api_key, ping_key, badge_key) VALUES (?, ?, ?, ?, ?)",
        (
            alice_project_id,
            1,
            "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "pppppppppppppppppppppp",
            "bbbbbbbbbbbbbbbbbbbbbb"
        )
    )

    conn.commit()
    conn.close()
