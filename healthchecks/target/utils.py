import re
import datetime
import uuid

def generate_slug(name):
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s

def iso_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")

def check_to_dict(check_row, base_url="http://localhost:8011", api_ver="v1"):
    chk_uuid = check_row["uuid"]
    b_url = f"{base_url}/b/2/{chk_uuid}.svg"

    return {
        "badge_url": b_url,
        "channels": check_row["channels"] or "",
        "desc": check_row["desc"] if check_row["desc"] is not None else "",
        "failure_kw": check_row["failure_kw"] or "",
        "filter_body": bool(check_row["filter_body"]),
        "filter_default_fail": bool(check_row["filter_default_fail"]),
        "filter_http_body": bool(check_row["filter_http_body"]),
        "filter_subject": bool(check_row["filter_subject"]),
        "grace": check_row["grace"],
        "last_ping": check_row["last_ping"],
        "manual_resume": bool(check_row["manual_resume"]),
        "methods": check_row["methods"] or "",
        "n_pings": check_row["n_pings"],
        "name": check_row["name"] or "",
        "next_ping": check_row["next_ping"],
        "pause_url": f"{base_url}/api/{api_ver}/checks/{chk_uuid}/pause",
        "ping_url": f"{base_url}/ping/{chk_uuid}",
        "resume_url": f"{base_url}/api/{api_ver}/checks/{chk_uuid}/resume",
        "slug": check_row["slug"] or generate_slug(check_row["name"]),
        "start_kw": check_row["start_kw"] or "",
        "started": False,
        "status": check_row["status"] or "new",
        "subject": check_row["subject"] or "",
        "subject_fail": check_row["subject_fail"] or "",
        "success_kw": check_row["success_kw"] or "",
        "tags": check_row["tags"] or "",
        "timeout": check_row["timeout"],
        "update_url": f"{base_url}/api/{api_ver}/checks/{chk_uuid}",
        "uuid": chk_uuid
    }
