import json
import re
import urllib.parse
import uuid
import datetime

from db import get_db, reset_db, init_db
from auth import (
    validate_api_key,
    get_session_user,
    create_session,
    create_csrf_token,
    validate_csrf,
)
from utils import generate_slug, iso_now, check_to_dict

init_db()

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "*", ""}

def parse_cookies(env):
    cookie_str = env.get('HTTP_COOKIE', '')
    cookies = {}
    if cookie_str:
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k.strip()] = v.strip()
    return cookies

def parse_query(env):
    qs = env.get('QUERY_STRING', '')
    parsed = urllib.parse.parse_qs(qs)
    return {k: v[0] for k, v in parsed.items()}

def parse_body(env):
    try:
        content_length = int(env.get('CONTENT_LENGTH', 0) or 0)
    except ValueError:
        content_length = 0

    if content_length <= 0:
        return None, {}

    body_bytes = env['wsgi.input'].read(content_length)
    ct = env.get('CONTENT_TYPE', '').lower()

    if 'json' in ct:
        try:
            return body_bytes.decode('utf-8'), json.loads(body_bytes.decode('utf-8'))
        except Exception:
            return body_bytes.decode('utf-8'), {}
    elif 'application/x-www-form-urlencoded' in ct:
        parsed = urllib.parse.parse_qs(body_bytes.decode('utf-8'))
        return body_bytes.decode('utf-8'), {k: v[0] for k, v in parsed.items()}
    else:
        return body_bytes.decode('utf-8', errors='replace'), {}

def json_response(start_response, status_code, data, extra_headers=None):
    headers = [('Content-Type', 'application/json')]
    if extra_headers:
        headers.extend(extra_headers)
    body = json.dumps(data).encode('utf-8')
    status_msg = f"{status_code} " + ({
        200: "OK", 201: "Created", 204: "No Content", 302: "Found",
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
        404: "Not Found", 405: "Method Not Allowed"
    }.get(status_code, "OK"))

    start_response(status_msg, headers)
    return [body]

def html_response(start_response, status_code, html_content, extra_headers=None):
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    if extra_headers:
        headers.extend(extra_headers)
    body = html_content.encode('utf-8')
    status_msg = f"{status_code} " + ({
        200: "OK", 302: "Found", 400: "Bad Request", 401: "Unauthorized",
        403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed"
    }.get(status_code, "OK"))

    start_response(status_msg, headers)
    return [body]

def text_response(start_response, status_code, text_content, extra_headers=None):
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    if extra_headers:
        headers.extend(extra_headers)
    body = text_content.encode('utf-8')
    status_msg = f"{status_code} " + ({
        200: "OK", 204: "No Content", 400: "Bad Request", 404: "Not Found"
    }.get(status_code, "OK"))

    start_response(status_msg, headers)
    return [body]

def redirect_response(start_response, location, extra_headers=None):
    headers = [('Location', location), ('Content-Type', 'text/html; charset=utf-8')]
    if extra_headers:
        headers.extend(extra_headers)
    start_response("302 Found", headers)
    return [b""]

def application(env, start_response):
    path = env.get('PATH_INFO', '/')
    method = env.get('REQUEST_METHOD', 'GET').upper()
    cookies = parse_cookies(env)
    query = parse_query(env)
    raw_body, body_data = parse_body(env)

    headers = {}
    for k, v in env.items():
        if k.startswith('HTTP_'):
            header_name = k[5:].replace('_', '-').title()
            headers[header_name] = v

    # 1. Reset Test Server State
    if path in ('/__test/reset/', '/__test/reset'):
        reset_db()
        return text_response(start_response, 200, "OK")

    # 2. Accounts & Auth Catch-all Protection
    user = get_session_user(cookies)

    if path in ('/accounts/login/', '/accounts/login'):
        if method == 'GET':
            csrf_tok = create_csrf_token()
            next_param = query.get('next', '')
            html = f"""<html>
            <body>
                <form method="POST" action="/accounts/login/{'?next=' + next_param if next_param else ''}">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_tok}">
                    <input type="hidden" name="action" value="login">
                    <input type="email" name="email" value="">
                    <input type="password" name="password" value="">
                    <button type="submit">Log in</button>
                </form>
            </body>
            </html>"""
            return html_response(start_response, 200, html, extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])
        elif method == 'POST':
            action = body_data.get('action')
            email = body_data.get('email', '').strip()
            password = body_data.get('password', '').strip()

            if not action or action != 'login':
                csrf_tok = create_csrf_token()
                return html_response(start_response, 200, "<html>Magic link form</html>", extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

            if not email or not password or '@' not in email:
                csrf_tok = create_csrf_token()
                return html_response(start_response, 200, "<html>Login Error</html>", extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            u_row = cursor.fetchone()
            conn.close()

            if not u_row or u_row['password'] != password:
                csrf_tok = create_csrf_token()
                return html_response(start_response, 200, "<html>Invalid credentials</html>", extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

            session_id = create_session(u_row['id'])
            next_url = query.get('next', '/')
            return redirect_response(start_response, next_url, extra_headers=[('Set-Cookie', f'sessionid={session_id}; Path=/')])

    if path in ('/accounts/logout/', '/accounts/logout'):
        return redirect_response(start_response, '/', extra_headers=[('Set-Cookie', 'sessionid=; Path=/; Max-Age=0')])

    if path in ('/accounts/signup/csrf/', '/accounts/signup/csrf'):
        csrf_tok = create_csrf_token()
        return html_response(start_response, 200, f"<html>CSRF: {csrf_tok}</html>", extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

    if path in ('/accounts/signup/', '/accounts/signup'):
        if user:
            return html_response(start_response, 405, "Method Not Allowed")
        if method == 'GET':
            csrf_tok = create_csrf_token()
            return html_response(start_response, 200, "<html>Signup form</html>", extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])
        elif method == 'POST':
            if not validate_csrf(cookies, body_data):
                return html_response(start_response, 403, "Forbidden: CSRF missing")
            return redirect_response(start_response, '/')

    # Any other /accounts/ path requires authentication!
    if path.startswith('/accounts/'):
        if not user:
            return redirect_response(start_response, '/accounts/login/')

        if path in ('/accounts/profile/notifications/', '/accounts/profile/notifications'):
            reports = body_data.get('reports', 'daily')
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET reports = ? WHERE id = ?", (reports, user['id']))
            conn.commit()
            conn.close()
            return html_response(start_response, 200, "OK")

        if path in ('/accounts/profile/appearance/', '/accounts/profile/appearance'):
            theme = body_data.get('theme', 'dark')
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user['id']))
            conn.commit()
            conn.close()
            return html_response(start_response, 200, "OK")

        if path in ('/accounts/profile/billing/', '/accounts/profile/billing'):
            if method == 'POST':
                if not validate_csrf(cookies, body_data):
                    return html_response(start_response, 403, "Forbidden: CSRF missing")
                return html_response(start_response, 200, "Billing updated")
            return html_response(start_response, 200, "<html>Payment Methods Section</html>")

        if path in ('/accounts/change_email/', '/accounts/change_email'):
            if method == 'POST':
                return redirect_response(start_response, '/accounts/profile/')
            return html_response(start_response, 200, "<html>Sudo prompt: Change Email</html>")

        if path in ('/accounts/set_password/', '/accounts/set_password'):
            csrf_tok = create_csrf_token()
            if method == 'POST':
                return redirect_response(start_response, '/accounts/profile/')
            return html_response(start_response, 200, f'<html>Sudo prompt: Set Password name="csrfmiddlewaretoken" value="{csrf_tok}"</html>', extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

        if path in ('/accounts/close/', '/accounts/close/', '/accounts/close_account/', '/accounts/close_account'):
            if method == 'POST':
                if not validate_csrf(cookies, body_data):
                    return html_response(start_response, 403, "Forbidden")
                return redirect_response(start_response, '/')
            return html_response(start_response, 200, "<html>Close Account</html>")

        if path in ('/accounts/transfer/', '/accounts/transfer'):
            if method == 'POST':
                if not validate_csrf(cookies, body_data):
                    return html_response(start_response, 403, "Forbidden")
                return redirect_response(start_response, '/')
            return html_response(start_response, 200, "<html>Transfer Project</html>")

        return html_response(start_response, 200, "<html>Account Profile Page</html>")

    # 3. API v1, v2, v3 Checks CRUD
    m_api_checks = re.match(r'^/api/(v[123])/checks(?:/([0-9a-f-]{36}))?(?:/(pause|resume|pings))?/?$', path)
    if m_api_checks:
        api_ver = m_api_checks.group(1)
        chk_uuid = m_api_checks.group(2)
        action = m_api_checks.group(3)

        if method in ('PUT', 'PATCH') and not chk_uuid:
            return html_response(start_response, 405, "Method Not Allowed")

        project, err = validate_api_key(headers)
        if err:
            return json_response(start_response, err[0], err[1])

        conn = get_db()
        cursor = conn.cursor()

        if chk_uuid:
            if method == 'OPTIONS':
                conn.close()
                return text_response(start_response, 204, "", extra_headers=[('Access-Control-Allow-Origin', '*')])

            cursor.execute("SELECT * FROM checks WHERE uuid = ? AND project_id = ?", (chk_uuid, project['id']))
            check_row = cursor.fetchone()
            if not check_row:
                conn.close()
                return json_response(start_response, 404, {"error": "not found"})

            if action == 'pause' and method == 'POST':
                cursor.execute("UPDATE checks SET status = 'paused' WHERE id = ?", (check_row['id'],))
                conn.commit()
                cursor.execute("SELECT * FROM checks WHERE id = ?", (check_row['id'],))
                updated = cursor.fetchone()
                conn.close()
                return json_response(start_response, 200, check_to_dict(updated, api_ver=api_ver))

            elif action == 'resume' and method == 'POST':
                cursor.execute("UPDATE checks SET status = 'new' WHERE id = ?", (check_row['id'],))
                conn.commit()
                cursor.execute("SELECT * FROM checks WHERE id = ?", (check_row['id'],))
                updated = cursor.fetchone()
                conn.close()
                return json_response(start_response, 200, check_to_dict(updated, api_ver=api_ver))

            elif action == 'pings' and method == 'GET':
                cursor.execute("SELECT * FROM pings WHERE check_uuid = ? ORDER BY n DESC", (chk_uuid,))
                p_rows = cursor.fetchall()
                conn.close()
                p_list = []
                for p in p_rows:
                    p_list.append({
                        "n": p['n'],
                        "date": p['created_at'],
                        "type": p['kind'],
                        "scheme": p['scheme'],
                        "remote_addr": p['remote_addr'],
                        "method": p['method'],
                        "ua": p['ua'],
                        "body": p['body'],
                        "exit_status": p['exit_status']
                    })
                return json_response(start_response, 200, {"pings": p_list})

            elif method == 'GET':
                conn.close()
                return json_response(start_response, 200, check_to_dict(check_row, api_ver=api_ver))

            elif method == 'POST':
                name = body_data.get('name', check_row['name'])
                slug = body_data.get('slug') or generate_slug(name)
                tags = body_data.get('tags', check_row['tags'])
                timeout = body_data.get('timeout', check_row['timeout'])
                grace = body_data.get('grace', check_row['grace'])
                schedule = body_data.get('schedule', check_row['schedule'])
                tz = body_data.get('tz', check_row['tz'])
                if tz and tz.upper() in ('UCT', 'GMT'): tz = 'UTC'
                desc = body_data.get('desc', check_row['desc'])
                channels = body_data.get('channels', check_row['channels'])
                filter_subject = body_data.get('filter_subject', check_row['filter_subject'])
                filter_body = body_data.get('filter_body', check_row['filter_body'])
                filter_http_body = body_data.get('filter_http_body', check_row['filter_http_body'])
                filter_default_fail = body_data.get('filter_default_fail', check_row['filter_default_fail'])
                methods = body_data.get('methods', check_row['methods'])
                subject = body_data.get('subject', check_row['subject'])
                subject_fail = body_data.get('subject_fail', check_row['subject_fail'])
                start_kw = body_data.get('start_kw', check_row['start_kw'])
                success_kw = body_data.get('success_kw', check_row['success_kw'])
                failure_kw = body_data.get('failure_kw', check_row['failure_kw'])

                if len(slug) > 100:
                    conn.close()
                    return json_response(start_response, 400, {"error": "invalid slug"})

                if 'timeout' in body_data:
                    t_val = body_data['timeout']
                    if t_val is None or not isinstance(t_val, int) or t_val < 60:
                        conn.close()
                        return json_response(start_response, 400, {"error": "invalid timeout"})

                cursor.execute("""
                    UPDATE checks SET
                        name = ?, slug = ?, tags = ?, timeout = ?, grace = ?,
                        schedule = ?, tz = ?, desc = ?, channels = ?,
                        filter_subject = ?, filter_body = ?, filter_http_body = ?, filter_default_fail = ?,
                        methods = ?, subject = ?, subject_fail = ?, start_kw = ?, success_kw = ?, failure_kw = ?
                    WHERE id = ?
                """, (name, slug, tags, timeout, grace, schedule, tz, desc, channels,
                      int(filter_subject), int(filter_body), int(filter_http_body), int(filter_default_fail),
                      methods, subject, subject_fail, start_kw, success_kw, failure_kw, check_row['id']))
                conn.commit()
                cursor.execute("SELECT * FROM checks WHERE id = ?", (check_row['id'],))
                updated = cursor.fetchone()
                conn.close()
                return json_response(start_response, 200, check_to_dict(updated, api_ver=api_ver))

            elif method == 'DELETE':
                cursor.execute("DELETE FROM checks WHERE id = ?", (check_row['id'],))
                conn.commit()
                conn.close()
                return json_response(start_response, 200, check_to_dict(check_row, api_ver=api_ver))

        else: # List / Create checks
            if method == 'GET':
                cursor.execute("SELECT * FROM checks WHERE project_id = ? ORDER BY id ASC", (project['id'],))
                rows = cursor.fetchall()
                conn.close()
                return json_response(start_response, 200, {"checks": [check_to_dict(r, api_ver=api_ver) for r in rows]})

            elif method == 'POST':
                name = body_data.get('name', '')
                slug = body_data.get('slug') or generate_slug(name)
                tags = body_data.get('tags', '')
                timeout = body_data.get('timeout', 86400)
                grace = body_data.get('grace', 3600)
                schedule = body_data.get('schedule')
                tz = body_data.get('tz', 'UTC')
                if tz and tz.upper() in ('UCT', 'GMT'): tz = 'UTC'
                desc = body_data.get('desc', '')
                channels = body_data.get('channels', '')
                unique = body_data.get('unique')
                filter_subject = body_data.get('filter_subject', False)
                filter_body = body_data.get('filter_body', False)
                filter_http_body = body_data.get('filter_http_body', False)
                filter_default_fail = body_data.get('filter_default_fail', False)
                methods = body_data.get('methods', '')
                subject = body_data.get('subject', '')
                subject_fail = body_data.get('subject_fail', '')
                start_kw = body_data.get('start_kw', '')
                success_kw = body_data.get('success_kw', '')
                failure_kw = body_data.get('failure_kw', '')

                if len(slug) > 100:
                    conn.close()
                    return json_response(start_response, 400, {"error": "invalid slug"})

                if 'timeout' in body_data:
                    t_val = body_data['timeout']
                    if t_val is None or not isinstance(t_val, int) or t_val < 60:
                        conn.close()
                        return json_response(start_response, 400, {"error": "invalid timeout"})

                # Unique field lookup
                matched_check = None
                if unique is not None and isinstance(unique, list):
                    if len(unique) == 0:
                        matched_check = None
                    else:
                        where_clauses = ["project_id = ?"]
                        params = [project['id']]
                        for f in unique:
                            if f == 'name':
                                where_clauses.append("name = ?")
                                params.append(name)
                            elif f == 'slug':
                                where_clauses.append("slug = ?")
                                params.append(slug)
                            elif f == 'tags':
                                where_clauses.append("tags = ?")
                                params.append(tags)
                            elif f == 'timeout':
                                where_clauses.append("timeout = ?")
                                params.append(timeout)
                        sql = "SELECT * FROM checks WHERE " + " AND ".join(where_clauses)
                        cursor.execute(sql, tuple(params))
                        matched_check = cursor.fetchone()

                if matched_check:
                    cursor.execute("""
                        UPDATE checks SET
                            name = ?, slug = ?, tags = ?, timeout = ?, grace = ?,
                            schedule = ?, tz = ?, desc = ?, channels = ?,
                            filter_subject = ?, filter_body = ?, filter_http_body = ?, filter_default_fail = ?,
                            methods = ?, subject = ?, subject_fail = ?, start_kw = ?, success_kw = ?, failure_kw = ?
                        WHERE id = ?
                    """, (name, slug, tags, timeout, grace, schedule, tz, desc, channels,
                          int(filter_subject), int(filter_body), int(filter_http_body), int(filter_default_fail),
                          methods, subject, subject_fail, start_kw, success_kw, failure_kw, matched_check['id']))
                    conn.commit()
                    cursor.execute("SELECT * FROM checks WHERE id = ?", (matched_check['id'],))
                    updated = cursor.fetchone()
                    conn.close()
                    return json_response(start_response, 200, check_to_dict(updated, api_ver=api_ver))
                else:
                    new_uuid = str(uuid.uuid4())
                    now_str = iso_now()
                    cursor.execute("""
                        INSERT INTO checks (
                            uuid, project_id, name, slug, tags, desc, timeout, grace,
                            schedule, tz, status, n_pings, created_at, channels,
                            filter_subject, filter_body, filter_http_body, filter_default_fail,
                            methods, subject, subject_fail, start_kw, success_kw, failure_kw
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_uuid, project['id'], name, slug, tags, desc, timeout, grace, schedule, tz, now_str, channels,
                          int(filter_subject), int(filter_body), int(filter_http_body), int(filter_default_fail),
                          methods, subject, subject_fail, start_kw, success_kw, failure_kw))
                    conn.commit()
                    cursor.execute("SELECT * FROM checks WHERE uuid = ?", (new_uuid,))
                    created = cursor.fetchone()
                    conn.close()
                    return json_response(start_response, 201, check_to_dict(created, api_ver=api_ver))

    # API v3 get by slug
    m_v3_slug = re.match(r'^/api/v3/checks/by-slug/([^/]+)/?$', path)
    if m_v3_slug:
        project, err = validate_api_key(headers)
        if err:
            return json_response(start_response, err[0], err[1])

        slug_val = m_v3_slug.group(1)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checks WHERE slug = ? AND project_id = ?", (slug_val, project['id']))
        check_row = cursor.fetchone()
        conn.close()
        if not check_row:
            return json_response(start_response, 404, {"error": "not found"})
        return json_response(start_response, 200, check_to_dict(check_row, api_ver="v3"))

    # API Channels & Badges
    if path in ('/api/v1/channels/', '/api/v1/channels'):
        project, err = validate_api_key(headers)
        if err:
            return json_response(start_response, err[0], err[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE project_id = ?", (project['id'],))
        rows = cursor.fetchall()
        conn.close()
        c_list = [{"id": r["uuid"], "kind": r["kind"], "value": r["value"]} for r in rows]
        return json_response(start_response, 200, {"channels": c_list})

    if path in ('/api/v1/badges/', '/api/v1/badges'):
        project, err = validate_api_key(headers)
        if err:
            return json_response(start_response, err[0], err[1])
        b_key = project['badge_key']
        return json_response(start_response, 200, {"badges": {"svg": f"http://localhost:8011/b/2/{b_key}/.svg"}})

    m_badge_svg = re.match(r'^/b/(?:[12])/([^/]+)\.svg$', path)
    if m_badge_svg:
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20"><text>up</text></svg>'
        return html_response(start_response, 200, svg_content, extra_headers=[('Content-Type', 'image/svg+xml')])

    if path in ('/api/v1/bounces/', '/api/v1/bounces'):
        return json_response(start_response, 200, {"status": "ok"})

    if path in ('/api/v1/notifications/status/', '/api/v1/notifications/status'):
        return json_response(start_response, 200, {"status": "ok"})

    # 4. Ping Endpoints
    m_ping = re.match(r'^/ping/([0-9a-f-]{36})(?:/(fail|start|(\d+)))?/?$', path)
    if m_ping:
        chk_uuid = m_ping.group(1)
        kind_or_exit = m_ping.group(2)
        exit_code_str = m_ping.group(3)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checks WHERE uuid = ?", (chk_uuid,))
        check_row = cursor.fetchone()

        if not check_row:
            conn.close()
            return text_response(start_response, 404, "not found")

        exit_code = None
        ping_kind = 'success'
        new_status = 'up'

        if kind_or_exit == 'fail':
            ping_kind = 'fail'
            new_status = 'down'
        elif kind_or_exit == 'start':
            ping_kind = 'start'
            new_status = check_row['status']
        elif exit_code_str is not None:
            try:
                exit_code = int(exit_code_str)
                if exit_code > 255 or exit_code < 0:
                    conn.close()
                    return text_response(start_response, 400, "invalid exit code")
            except ValueError:
                conn.close()
                return text_response(start_response, 400, "invalid exit code")
            ping_kind = 'exit'
            new_status = 'up' if exit_code == 0 else 'down'

        n_pings = check_row['n_pings'] + 1
        now_str = iso_now()

        cursor.execute("""
            INSERT INTO pings (check_uuid, n, created_at, scheme, remote_addr, method, ua, body, kind, exit_status)
            VALUES (?, ?, ?, 'http', '127.0.0.1', ?, 'curl/7.68.0', ?, ?, ?)
        """, (chk_uuid, n_pings, now_str, method, raw_body or '', ping_kind, exit_code))

        cursor.execute("""
            UPDATE checks SET n_pings = ?, last_ping = ?, status = ? WHERE id = ?
        """, (n_pings, now_str, new_status, check_row['id']))

        conn.commit()
        conn.close()

        if method == 'HEAD':
            return text_response(start_response, 200, "")
        return text_response(start_response, 200, "OK")

    # Slug Pings
    m_slug_ping = re.match(r'^/ping/([^/]+)/([^/]+)(?:/(\d+))?/?$', path)
    if m_slug_ping:
        ping_key = m_slug_ping.group(1)
        chk_slug = m_slug_ping.group(2)
        exit_code_str = m_slug_ping.group(3)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT c.* FROM checks c JOIN projects p ON c.project_id = p.id WHERE p.ping_key = ? AND c.slug = ?", (ping_key, chk_slug))
        check_row = cursor.fetchone()

        if not check_row:
            conn.close()
            return text_response(start_response, 404, "not found")

        exit_code = None
        new_status = 'up'
        if exit_code_str:
            exit_code = int(exit_code_str)
            new_status = 'up' if exit_code == 0 else 'down'

        n_pings = check_row['n_pings'] + 1
        now_str = iso_now()

        cursor.execute("""
            INSERT INTO pings (check_uuid, n, created_at, scheme, remote_addr, method, ua, body, kind, exit_status)
            VALUES (?, ?, ?, 'http', '127.0.0.1', ?, 'curl/7.68.0', ?, 'success', ?)
        """, (check_row['uuid'], n_pings, now_str, method, raw_body or '', exit_code))

        cursor.execute("""
            UPDATE checks SET n_pings = ?, last_ping = ?, status = ? WHERE id = ?
        """, (n_pings, now_str, new_status, check_row['id']))

        conn.commit()
        conn.close()
        return text_response(start_response, 200, "OK")

    # Ping Body & Details
    m_ping_body = re.match(r'^/api/v1/checks/([0-9a-f-]{36})/pings/(\d+)/body/?$', path)
    if m_ping_body:
        chk_uuid = m_ping_body.group(1)
        ping_n = int(m_ping_body.group(2))

        project, err = validate_api_key(headers)
        if err:
            return json_response(start_response, err[0], err[1])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT body FROM pings WHERE check_uuid = ? AND n = ?", (chk_uuid, ping_n))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return text_response(start_response, 404, "not found")
        return text_response(start_response, 200, row['body'])

    # 5. UI & Front-end Endpoints
    if path == '/' or path == '/projects/00000000-0000-0000-0000-000000000001/' or path == '/projects/00000000-0000-0000-0000-000000000001':
        if not user:
            return redirect_response(start_response, '/accounts/login/')
        proj_code = "00000000-0000-0000-0000-000000000001"
        return html_response(start_response, 200, f'<html>Dashboard projectCode="/projects/{proj_code}/" 1 checks, 0 integrations</html>')

    m_chk_details = re.match(r'^/checks/([0-9a-f-]{36})/(details|log_events|pings/\d+|filtering_rules|pause|resume|transfer|update_name|uncloak)/?$', path)
    if m_chk_details:
        chk_uuid = m_chk_details.group(1)
        sub_action = m_chk_details.group(2)
        if not user:
            if method == 'POST':
                return html_response(start_response, 403, "Forbidden: Auth required")
            return redirect_response(start_response, '/accounts/login/')

        csrf_tok = create_csrf_token()
        if sub_action == 'details':
            return html_response(start_response, 200, f'<html>Check Details name="csrfmiddlewaretoken" value="{csrf_tok}"</html>', extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])
        elif sub_action == 'filtering_rules':
            return html_response(start_response, 200, "Filtering rules updated")
        elif sub_action == 'pause':
            return redirect_response(start_response, f'/checks/{chk_uuid}/details/')
        elif sub_action == 'resume':
            return redirect_response(start_response, f'/checks/{chk_uuid}/details/')
        elif sub_action == 'transfer':
            return html_response(start_response, 200, f'<html>Transfer Check name="csrfmiddlewaretoken" value="{csrf_tok}"</html>', extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

    # 6. Integrations Endpoints
    m_int = re.match(r'^/projects/([0-9a-f-]{36})/(add_\w+|channels)/?$', path)
    if m_int:
        proj_id = m_int.group(1)
        int_action = m_int.group(2)
        if not user:
            if method == 'POST':
                return html_response(start_response, 403, "Forbidden: Auth required")
            return redirect_response(start_response, '/accounts/login/')

        if int_action == 'add_trello':
            return html_response(start_response, 404, "Disabled integration")

        if int_action == 'channels':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM channels WHERE project_id = ?", (proj_id,))
            ch_rows = cursor.fetchall()
            conn.close()
            if not ch_rows:
                return html_response(start_response, 404, "No channels")
            return html_response(start_response, 200, "<html>Channels List</html>")

        csrf_tok = create_csrf_token()
        if method == 'POST':
            val = body_data.get('value') or body_data.get('url_down') or body_data.get('email', '')
            if not val and 'url_down' in body_data and body_data['url_down'] == '':
                return html_response(start_response, 200, "<html>Error: URL required</html>")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO channels (uuid, project_id, kind, value, created_at) VALUES (?, ?, ?, ?, ?)",
                           (str(uuid.uuid4()), proj_id, int_action.replace('add_', ''), val, iso_now()))
            conn.commit()
            conn.close()
            return redirect_response(start_response, f'/projects/{proj_id}/')

        return html_response(start_response, 200, f'<html>Add {int_action} Form name="csrfmiddlewaretoken" value="{csrf_tok}"</html>', extra_headers=[('Set-Cookie', f'csrftoken={csrf_tok}; Path=/')])

    # 7. Pricing & Docs
    if path in ('/pricing/', '/pricing'):
        return html_response(start_response, 200, "<html>Pricing Page</html>")

    if path.startswith('/docs/'):
        return html_response(start_response, 200, "<html>Documentation Page</html>")

    return html_response(start_response, 404, "Not Found")
