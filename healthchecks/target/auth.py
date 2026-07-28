import uuid
from db import get_db

def validate_api_key(headers):
    api_key = None
    for k, v in headers.items():
        if k.lower() == 'x-api-key':
            api_key = v
            break

    if not api_key:
        return None, (401, {"error": "missing api key"})

    if len(api_key) != 32 or not api_key.isalnum():
        return None, (401, {"error": "missing api key"})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE api_key = ?", (api_key,))
    project = cursor.fetchone()
    conn.close()

    if not project:
        return None, (401, {"error": "wrong api key"})

    return project, None

def get_session_user(cookies):
    session_id = cookies.get("sessionid")
    if not session_id:
        return None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.* FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.session_id = ?
    """, (session_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_session(user_id):
    session_id = str(uuid.uuid4()).replace("-", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (session_id, user_id, created_at) VALUES (?, ?, datetime('now'))",
        (session_id, user_id)
    )
    conn.commit()
    conn.close()
    return session_id

def create_csrf_token():
    token = str(uuid.uuid4()).replace("-", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO csrf_tokens (token, created_at) VALUES (?, datetime('now'))",
        (token,)
    )
    conn.commit()
    conn.close()
    return token

def validate_csrf(cookies, form_data):
    cookie_token = cookies.get("csrftoken")
    form_token = form_data.get("csrfmiddlewaretoken") if isinstance(form_data, dict) else None

    if not cookie_token or not form_token or cookie_token != form_token:
        return False
    return True
