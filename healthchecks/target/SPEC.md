# Healthchecks — Complete Reverse-Engineered Specification

> Derived exclusively from the 134 HTTP replay test cases in `relang/input/` and `relang/output/`.
> Every claim is traceable to at least one test file.

---

## Table of Contents

1. [Authentication & Session Model](#1-authentication--session-model)
2. [CSRF Protection Rules](#2-csrf-protection-rules)
3. [Cookie Specification](#3-cookie-specification)
4. [API Authentication](#4-api-authentication)
5. [Endpoint Catalogue](#5-endpoint-catalogue)
   - 5.1 Accounts / Auth Endpoints
   - 5.2 API v1 Endpoints
   - 5.3 API v2 Endpoints
   - 5.4 API v3 Endpoints
   - 5.5 Ping Endpoints
   - 5.6 Front-End / UI Endpoints
   - 5.7 Integration Endpoints
   - 5.8 Payment Endpoints
6. [Check JSON Schema](#6-check-json-schema)
7. [Validation Rules](#7-validation-rules)
8. [Entity Model](#8-entity-model)
9. [Workflow Diagrams](#9-workflow-diagrams)
10. [Error Response Formats](#10-error-response-formats)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Authentication & Session Model

### Session Cookie

| Property | Value |
|---|---|
| Cookie name | `sessionid` |
| Set by | `POST /accounts/login/` on success (HTTP 302) |
| Required by | All `/checks/`, `/accounts/profile/`, `/projects/`, `/accounts/change_email/`, `/accounts/set_password/`, `/accounts/close_account/` endpoints |
| Missing behaviour | 302 redirect to `/accounts/login/` (or 403 for some POST endpoints) |

### Login Flow (mandatory sequence)

```
1. GET  /accounts/login/          -> 200, sets csrftoken cookie
2. POST /accounts/login/          -> 302, sets sessionid cookie
           body: action=login&email=<email>&password=<password>&csrfmiddlewaretoken=<csrf>
3. <protected page>               -> 200
```

### Test Users (fixture data)

| Email | Password | Role |
|---|---|---|
| `alice@example.org` | `password` | Primary test user / project owner |
| bob (fixture) | — | Member of Alice's project (used in transfer tests) |

### Sudo Mode (sensitive pages)

Some pages require re-authentication even when already logged in:

| Endpoint | Behaviour |
|---|---|
| `GET /accounts/change_email/` | Shows sudo prompt (200) when logged in |
| `GET /accounts/set_password/` | Shows sudo prompt (200) when logged in |

### Login `action` Parameter

| `action` value | Behaviour |
|---|---|
| `login` | Standard email+password login |
| (absent) | Uses magic-link / passwordless form |

### Remember-me

`POST /accounts/login/` with a `remember` field makes the session persistent.

### Redirect after login

`GET/POST /accounts/login/?next=<path>` honours the `next` parameter:
- `GET /accounts/login/?next=/projects/` -> 200
- `POST /accounts/login/?next=/projects/` -> 302 to `/projects/`

---

## 2. CSRF Protection Rules

Django's standard double-submit CSRF pattern.

### Endpoints that REQUIRE CSRF

| Endpoint | How CSRF is supplied |
|---|---|
| `POST /accounts/login/` | Cookie -> form body `csrfmiddlewaretoken` |
| `POST /accounts/logout/` | Form body |
| `POST /accounts/signup/` | Form body; missing -> 403 |
| `POST /accounts/profile/notifications/` | Form body |
| `POST /accounts/profile/billing/` | Form body; missing -> 403 |
| `POST /accounts/profile/appearance/` | Form body |
| `POST /accounts/change_email/` | Form body |
| `POST /accounts/set_password/` | Extracted from page HTML |
| `POST /accounts/close_account/` | Form body; missing -> 403 |
| `POST /accounts/transfer/` | Form body; missing -> 403 |
| `POST /projects/<uuid>/add_email/` | Form body |
| `POST /projects/<uuid>/add_slack/` | Form body |
| `POST /projects/<uuid>/add_webhook/` | Form body |
| `POST /checks/<uuid>/filtering_rules/` | Extracted from details page HTML |
| `POST /checks/<uuid>/transfer/` | Extracted from transfer page HTML |
| `POST /checks/<uuid>/pause/` | Form body |
| `POST /checks/<uuid>/resume/` | Form body |

### Endpoints that do NOT use CSRF

| Endpoint | Reason |
|---|---|
| All `POST /api/v1/*`, `/api/v2/*`, `/api/v3/*` | Use `X-Api-Key` header |
| `POST /ping/<uuid>` | Public ping, no auth |
| `POST /api/v1/bounces/` | Uses request signing |
| `POST /api/v1/notifications/status/` | Uses API key |
| `GET /accounts/signup/csrf/` | Returns a fresh CSRF token |

### How CSRF Token is Obtained

1. **Via cookie**: `GET /accounts/login/` sets `csrftoken` cookie -> sent as `csrfmiddlewaretoken` in body.
2. **Via HTML**: some pages embed the token as `csrfmiddlewaretoken" value="<token>"`. Extraction regex: `csrfmiddlewaretoken" value="([^"]+)"`.

### Signup CSRF Endpoint

```
GET /accounts/signup/csrf/  -> 200  (returns CSRF token, no auth required)
```

---

## 3. Cookie Specification

| Cookie Name | Set By | Purpose |
|---|---|---|
| `csrftoken` | Any form page (e.g. `GET /accounts/login/`) | Django CSRF protection |
| `sessionid` | `POST /accounts/login/` success | Authenticated session |

---

## 4. API Authentication

### Header

```
X-Api-Key: <32-character-alphanumeric-key>
```

### Validation Rules

| Rule | Status | Evidence |
|---|---|---|
| Header must be exactly `X-Api-Key` | 401 if wrong name | `x-apikey` -> 401 `{"error": "missing api key"}` |
| Key must be exactly 32 characters | 401 | 33-char key -> 401 |
| Key must be alphanumeric (no special chars) | 401 | `ABC!@#$%^&*()_+=-01` -> 401 |
| Missing header | 401 `{"error": "missing api key"}` | `api_get_checks_without_auth_header_returns_401` |
| Wrong key | 401 `{"error": "wrong api key"}` | `api_create_with_wrong_api_key_returns_401` |
| Read-only key on write endpoint | 401 | `api_list_pings_with_readonly_key_returns_401` |

### Fixture Keys

| Key | Purpose |
|---|---|
| `XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` (32 X's) | Full-access API key for alice's project |
| `pppppppppppppppppppppp` (22 p's) | Ping key for slug-based pings |

---

## 5. Endpoint Catalogue

### 5.1 Accounts / Auth Endpoints

#### `GET /accounts/login/`
- Auth: None
- Sets cookie: `csrftoken`
- Response: 200 HTML
- Query: `next=<path>` (optional)

#### `POST /accounts/login/`
- Auth: None; CSRF: Yes
- Content-Type: `application/x-www-form-urlencoded`
- Body: `action=login&email=<email>&password=<password>&csrfmiddlewaretoken=<csrf>`
- Optional: `remember=<value>` for persistent session
- Success: 302 + sets `sessionid`
- Empty email: 200 (form error)
- Empty password: 200 (form error)
- Invalid email format: 200 (form error)
- Username instead of email: 200 (form error)
- No `action` field: 200 (magic-link form shown)
- Query: `next=<path>` for post-login redirect

#### `POST /accounts/logout/`
- Auth: Yes; CSRF: Yes
- Success: 302 to `/`

#### `GET /accounts/signup/`
- Auth: None
- When already logged in: 200 or redirect

#### `POST /accounts/signup/`
- Auth: None; CSRF: Yes (missing -> 403)
- Body: `email=<email>&csrfmiddlewaretoken=<csrf>`
- Duplicate email: 200 (form error)

#### `GET /accounts/signup/csrf/`
- Auth: None
- Response: 200 (returns CSRF token)

#### `GET /accounts/profile/`
- Auth: Yes (session)
- Response: 200 HTML (includes password section)

#### `POST /accounts/profile/notifications/`
- Auth: Yes; CSRF: Yes
- Body: `reports=<value>&csrfmiddlewaretoken=<csrf>`
- `reports` values: `daily` (confirmed); also `weekly`, `monthly`, `off`
- Response: 200

#### `POST /accounts/profile/appearance/`
- Auth: Yes; CSRF: Yes
- Body: `theme=<value>&csrfmiddlewaretoken=<csrf>`
- `theme` values: `dark` (confirmed)
- Response: 200

#### `GET /accounts/profile/billing/`
- Auth: Yes
- Response: 200 HTML (payment methods section)

#### `POST /accounts/profile/billing/`
- Auth: Yes; CSRF: Yes (missing -> 403)

#### `GET /accounts/change_email/`
- No auth: 302 redirect
- Logged in: 200 (sudo prompt)

#### `POST /accounts/change_email/`
- Auth: Yes; CSRF: Yes
- Body: `email=<new-email>&csrfmiddlewaretoken=<csrf>`
- Invalid email: 200 (form error)

#### `GET /accounts/set_password/`
- No auth: 302 redirect
- Logged in: 200 (sudo prompt, embeds CSRF in HTML)

#### `POST /accounts/set_password/`
- Auth: Yes; CSRF: Yes (from HTML)
- Body: `current_password=<cur>&password=<new>&password2=<new>&csrfmiddlewaretoken=<csrf>`
- Short password: 200 (form error)

#### `GET /accounts/close_account/`
- No auth: 302 redirect
- Logged in: 200 HTML

#### `POST /accounts/close_account/`
- CSRF: Yes (missing -> 403)

#### `GET /accounts/transfer/`
- No auth: 403

#### `POST /accounts/transfer/`
- CSRF: Yes (missing -> 403)

#### `GET /accounts/verify_email/<token>/`
- Auth: None
- Invalid token: 200 (error page)
- Malformed token: 200 (error page)

#### `GET /accounts/unsubscribe/alerts/<token>/`
- Auth: None; Invalid token: 200

#### `GET /accounts/unsubscribe/reports/<token>/`
- Auth: None; Invalid token: 200

#### `GET /accounts/add_webauthn/`
- No auth: 302 redirect

---

### 5.2 API v1 Endpoints

All require `X-Api-Key: <32-char key>` unless noted.

#### `GET /api/v1/checks/`
- Response: 200 `{"checks": [...]}`
- Query: `tag=<tag>` (empty string returns all checks)
- No auth: 401 `{"error": "missing api key"}`

#### `POST /api/v1/checks/`
- Content-Type: `application/json`
- New check: 201 `<check-object>`
- Existing check (unique match): 200 `<check-object>`
- PATCH on list: 405
- PUT on list: 405

**Request body fields:**

| Field | Type | Notes |
|---|---|---|
| `name` | string | Auto-generates slug |
| `slug` | string | Max 100 chars |
| `tags` | string | Space/comma-separated |
| `desc` | string | `null` accepted |
| `timeout` | integer | Min 60, default 3600 |
| `grace` | integer | Default 60 |
| `schedule` | string | Cron expression |
| `tz` | string | IANA timezone; legacy names converted |
| `methods` | string | HTTP method filter |
| `unique` | array | Dedup fields: `["name"]`, `["name","timeout"]`, etc. |
| `filter_subject` | bool | |
| `filter_body` | bool | |
| `channels` | string | Channel IDs |

#### `GET /api/v1/checks/<uuid>`
- Found: 200 `<check-object>`
- Not found: 404
- After delete: 404

#### `POST /api/v1/checks/<uuid>` (update)
- Content-Type: `application/json`
- Response: 200 `<check-object>`
- Partial update: only specified fields change
- Name change: regenerates slug automatically
- Non-numeric timeout: 400
- `null` timeout: 400

#### `DELETE /api/v1/checks/<uuid>`
- Response: 200 `<check-object>` (returns the deleted check)
- Already deleted: 404

#### `OPTIONS /api/v1/checks/<uuid>`
- Response: 204 No Content

#### `GET /api/v1/checks/<uuid>/pings/`
- Read-only key: 401
- No pings yet: 200 `{"pings": []}`
- Non-existent uuid: 404

#### `GET /api/v1/checks/<uuid>/pings/<n>/body`
- Response: 200 `text/plain` containing ping body
- No auth: 401 `{"error": "missing api key"}`

#### `POST /api/v1/checks/<uuid>/pause`
- Response: 200 `<check-object>` with `"status": "paused"`

#### `POST /api/v1/checks/<uuid>/resume`
- Resumes a paused check

#### `GET /api/v1/channels/`
- Response: 200 `{"channels": []}` (empty if none exist)

#### `GET /api/v1/badges/`
- No auth: 401

#### `GET /badge/<badge-key>/<40-hex>/<tag>.svg`
- Public (no auth)
- Invalid badge key: 404

#### `POST /api/v1/bounces/`
- Auth: Request signing (no X-Api-Key)
- Content-Type: `application/json`
- Body: `{"signed": true, "type": "Bounce"}`
- Response: 200

#### `POST /api/v1/notifications/status/`
- Auth: X-Api-Key
- Content-Type: `application/json`
- Body: `{"status": "delivered"}`
- No matching notification: 404

---

### 5.3 API v2 Endpoints

#### `POST /api/v2/checks/`
- Auth: X-Api-Key; Content-Type: `application/json`
- Response: 201 `<check-object>`

---

### 5.4 API v3 Endpoints

#### `POST /api/v3/checks/`
- Auth: X-Api-Key; Content-Type: `application/json`
- `slug` is a first-class field in v3
- Response (new): 201 `<check-object-with-slug>`

#### `GET /api/v3/checks/`
- Auth: X-Api-Key
- Response: 200 `{"checks": [<check-with-slug>, ...]}`
- `slug` field present in every check object

#### `GET /api/v3/checks/<slug>`
- Auth: X-Api-Key
- Lookup by slug string (not UUID)

---

### 5.5 Ping Endpoints

All ping endpoints are **public** (no auth, no CSRF).

#### `GET /ping/<uuid>` -> 200
#### `HEAD /ping/<uuid>` -> 200
#### `POST /ping/<uuid>` -> 200 (`OK`)
- Optional body stored as ping body
- Malformed UUID: 400

#### `POST /ping/<uuid>/fail`
- Sets check status to `"down"`

#### `POST /ping/<uuid>/start`
- Non-existent check: 404

#### `POST /ping/<uuid>/<exit-status>`
- `exit_status` range: 0-255
- 0 = success; non-zero = failure
- > 255: 400 error

#### `POST /ping/<ping-key>/<slug>`
- Slug-based ping using ping key

#### `POST /ping/<ping-key>/<slug>/<exit-status>`
- Exit status 0-255

---

### 5.6 Front-End / UI Endpoints

All require session authentication unless noted.

#### `GET /`
- Auth: Yes
- Response: 200 HTML containing `/projects/<uuid>/` links
- Project UUID extraction: regex `/projects/([0-9a-f-]{36})/`

#### `GET /projects/<uuid>/`
- Auth: Yes (no auth -> 302 redirect)

#### `GET /checks/<uuid>/details/`
- Auth: Yes
- Response: 200 HTML; embeds CSRF token as `csrfmiddlewaretoken" value="..."`
- Contains: tags, timeout, grace period values

#### `GET /checks/<uuid>/log_events/`
- Auth: Yes; Response: 200

#### `GET /checks/<uuid>/pings/<n>/`
- Auth: Yes; Response: 200 (after at least one ping)

#### `POST /checks/<uuid>/filtering_rules/`
- Auth: Yes; CSRF: Yes (from details page HTML)
- Body: `csrfmiddlewaretoken=<csrf>&filter_subject=on&filter_body=on&keywords=<words>`
- Response: 302

#### `POST /checks/<uuid>/pause/`
- Auth: Yes; CSRF: Yes; Response: 302

#### `POST /checks/<uuid>/resume/`
- Auth: Yes; CSRF: Yes; Response: 302

#### `GET /checks/<uuid>/transfer/`
- Auth: Yes; Response: 200 HTML (embeds CSRF)

#### `POST /checks/<uuid>/transfer/`
- Auth: Yes; CSRF: Yes (from GET page)
- Body: `csrfmiddlewaretoken=<csrf>&action=transfer`
- Missing target: 400
- Success: 302

#### `POST /checks/<uuid>/update_name/`
- No auth: 403

#### `GET /checks/<uuid>/uncloak/`
- Auth: Yes; Bad key: 404

#### `GET /channels/<uuid>/edit/`
- Auth: Yes; Non-existent: 404

#### `GET /docs/` -> 200 (public)
#### `GET /docs/api/` -> 200 (public)
#### `GET /docs/cron/` -> 200 (public)
#### `GET /docs/signals/` -> 200 (public)

#### `POST /docs/search/`
- XSS attempts in query are sanitized in output

#### `GET /pricing/` -> 200 (public)

---

### 5.7 Integration Endpoints

All require session authentication.

#### `GET /projects/<uuid>/add_<integration>/`
- Returns 200 HTML form
- Returns 404 if integration is disabled

**Confirmed integrations (200):**

| Slug | Test |
|---|---|
| `email` | `integrations_add_channel_page_for_email_renders_with_correct_form` |
| `webhook` | `integrations_get_add_webhook_form_returns_200_2` |
| `slack` | `integrations_post_with_valid_data_creates_channel_and_redirects_2` |
| `googlechat` | `integrations_add_page_renders_after_login_2` |
| `mattermost` | `integrations_add_page_renders_after_login_5` |
| `msteams` | `integrations_add_page_renders_after_login_6` |
| `prometheus` | `integrations_add_page_renders_after_login_10` |
| `zulip` | `integrations_add_page_renders_after_login_17` |
| `signal` | `integrations_add_channel_for_signal_with_down_only_notifications` |
| `group` | `integrations_add_channel_for_group_after_creating_other_channels` |

**Disabled integration (404):**
- `trello`

#### `POST /projects/<uuid>/add_webhook/`
- Body: `url_down=<url>&method_down=GET&url_up=<url>&method_up=GET&csrfmiddlewaretoken=<csrf>`
- Both URLs empty: 200 (validation error)
- `url_down` only provided: 200 (partial — no channel created)
- Both valid: 302 (channel created)

#### `POST /projects/<uuid>/add_slack/`
- Body: `value=<webhook-url>&csrfmiddlewaretoken=<csrf>`
- Valid webhook URL: 302

#### `POST /projects/<uuid>/add_email/`
- Body: `value=<email>&up=true&down=true&csrfmiddlewaretoken=<csrf>`
- Success: 302

#### `GET /projects/<uuid>/channels/`
- Auth: Yes; Returns 404 when no channels exist (path confirmed valid)

---

### 5.8 Payment Endpoints

#### `GET /pricing/` -> 200 (public)
#### `GET /accounts/profile/billing/` -> 200 (auth required)
#### `POST /accounts/profile/billing/` -> 403 if no CSRF

---

## 6. Check JSON Schema

The canonical check object returned by all check API endpoints:

```json
{
  "badge_url":            "http://<host>/b/2/<UUID>.svg",
  "channels":             "",
  "desc":                 "",
  "failure_kw":           "",
  "filter_body":          false,
  "filter_default_fail":  false,
  "filter_http_body":     false,
  "filter_subject":       false,
  "grace":                60,
  "last_ping":            null,
  "manual_resume":        false,
  "methods":              "",
  "n_pings":              0,
  "name":                 "<string>",
  "next_ping":            null,
  "pause_url":            "http://<host>/api/v1/checks/<UUID>/pause",
  "ping_url":             "http://<host>/ping/<UUID>",
  "resume_url":           "http://<host>/api/v1/checks/<UUID>/resume",
  "slug":                 "<slugified-name>",
  "start_kw":             "",
  "started":              false,
  "status":               "new",
  "subject":              "",
  "subject_fail":         "",
  "success_kw":           "",
  "tags":                 "",
  "timeout":              3600,
  "update_url":           "http://<host>/api/v1/checks/<UUID>",
  "uuid":                 "<UUID>"
}
```

**Status values observed:**
- `"new"` — never pinged
- `"paused"` — after `/pause` call
- `"down"` — after `/fail` ping
- `"up"` — after successful ping (inferred)

**Checks list response:**
```json
{"checks": [<check-object>, ...]}
```

**Pings list response:**
```json
{"pings": []}
```

**Channels list response:**
```json
{"channels": []}
```

**Slug generation:**
- Auto-generated from `name` by slugifying (lowercase, hyphens)
- `"Slug Update"` -> `"slug-update"`
- `"Renamed Again"` -> `"renamed-again"`
- `"API Pause"` -> `"api-pause"`
- Name change via update regenerates slug automatically

**Content-Type for API responses:** `application/json`

**Ping body response Content-Type:** `text/plain`

---

## 7. Validation Rules

### API Key Validation

| Rule | Status | Response |
|---|---|---|
| Missing `X-Api-Key` header | 401 | `{"error": "missing api key"}` |
| Wrong header name (e.g. `X-Apikey`) | 401 | `{"error": "missing api key"}` |
| Key length != 32 | 401 | — |
| Special characters in key | 401 | `{"error": "missing api key"}` |
| Valid format but wrong key | 401 | `{"error": "wrong api key"}` |
| Read-only key on write endpoint | 401 | — |

### Check Field Validation

| Field | Rule | Status |
|---|---|---|
| `timeout` | Must be integer >= 60 | 400 |
| `timeout` | Non-numeric string rejected | 400 |
| `timeout` | `null` rejected on update | 400 |
| `timeout` = 60 | Accepted (boundary) | 201 |
| `slug` | Max 100 characters | 400 if > 100 |
| `schedule` | Must be valid cron / OnCalendar | 400 |
| `methods` | Must be valid HTTP method names | 400 |
| `exit_status` in URL | Must be 0-255 | 400 if > 255 |
| `unique=[]` (empty array) | Creates new check | 201 |
| Extra / unknown fields | Silently ignored | 201 |
| `desc=null` | Accepted | 201 |

### Timezone Conversion

| Input | Stored As |
|---|---|
| `UCT` | `UTC` |
| Legacy names | Canonical IANA form |

### Account Form Validation

| Field | Rule | Status |
|---|---|---|
| Login `email` | Must not be empty | 200 (form error) |
| Login `password` | Must not be empty | 200 (form error) |
| Login `email` | Must be valid email format | 200 (form error) |
| Login with username (no @) | Rejected | 200 (form error) |
| Signup `email` | Must not already exist | 200 (form error) |
| Change email `email` | Must be valid email | 200 (form error) |
| Set password `password` | Minimum length enforced | 200 (form error if short) |
| Set password | `password` must match `password2` | (inferred) |

---

## 8. Entity Model

### Project

| Field | Type | Notes |
|---|---|---|
| `code` | UUID | URL key `/projects/<uuid>/` |

- UUID format: 36-char with hyphens, regex `[0-9a-f-]{36}`

### Check

| Field | Type | Notes |
|---|---|---|
| `uuid` | UUID | Primary key |
| `name` | string | Display name |
| `slug` | string | URL-safe name, max 100 chars, auto-generated |
| `tags` | string | Space/comma-separated tag list |
| `desc` | string | Nullable description |
| `timeout` | integer | Seconds, min 60 |
| `grace` | integer | Seconds, default 60 |
| `status` | enum | `new`, `up`, `down`, `paused` |
| `n_pings` | integer | Total ping count |
| `last_ping` | datetime\|null | |
| `next_ping` | datetime\|null | |
| `started` | boolean | |
| `manual_resume` | boolean | |
| `methods` | string | HTTP method filter |
| `filter_subject` | boolean | Email subject filtering |
| `filter_body` | boolean | Email/HTTP body filtering |
| `filter_http_body` | boolean | HTTP body filtering |
| `filter_default_fail` | boolean | |
| `failure_kw` | string | |
| `success_kw` | string | |
| `start_kw` | string | |
| `subject` | string | |
| `subject_fail` | string | |
| `channels` | string | Associated channel IDs |
| `ping_url` | URL | `http://<host>/ping/<uuid>` |
| `pause_url` | URL | `http://<host>/api/v1/checks/<uuid>/pause` |
| `resume_url` | URL | `http://<host>/api/v1/checks/<uuid>/resume` |
| `update_url` | URL | `http://<host>/api/v1/checks/<uuid>` |
| `badge_url` | URL | `http://<host>/b/2/<uuid>.svg` |

### Ping

| Field | Type | Notes |
|---|---|---|
| `n` | integer | Sequence number (1-indexed) |
| `body` | text | Content from request body |

### Channel (Integration)

| Field | Type | Notes |
|---|---|---|
| `kind` | string | `email`, `webhook`, `slack`, `googlechat`, `mattermost`, `msteams`, `prometheus`, `zulip`, `signal`, `group` |
| Project | FK | Belongs to a project |

### User / Profile

| Field | Notes |
|---|---|
| `email` | Login identifier (unique) |
| `password` | Hashed; minimum length enforced |
| `reports` | `daily`, `weekly`, `monthly`, `off` |
| `theme` | `dark`, `light` |

---

## 9. Workflow Diagrams

### 9.1 Standard Login Flow

```
Client                              Server
  |                                    |
  |--GET /accounts/login/ ------------>|
  |<--200 + Set-Cookie: csrftoken------|
  |                                    |
  |--POST /accounts/login/ ----------->|
  |   body: action=login               |
  |         email=alice@example.org    |
  |         password=password          |
  |         csrfmiddlewaretoken=<tok>  |
  |<--302 + Set-Cookie: sessionid------|
  |                                    |
  |--GET /<protected-page>/ ---------->|
  |   Cookie: sessionid=<id>           |
  |<--200 HTML-------------------------|
```

### 9.2 Create and Ping a Check (API)

```
Client                              Server
  |                                    |
  |--POST /api/v1/checks/ ------------>|
  |   X-Api-Key: XXXX...32 chars       |
  |   Content-Type: application/json   |
  |   {"name":"My Svc","timeout":3600} |
  |<--201 {"uuid":"<UUID>", ...}--------|
  |                                    |
  |--POST /ping/<UUID> --------------->|  (cronjob completes)
  |<--200 OK---------------------------|
  |                                    |
  |--POST /ping/<UUID>/fail ---------->|  (job failed)
  |<--200 OK status now "down"---------|
```

### 9.3 Slug-Based Ping (v3)

```
Client                              Server
  |                                    |
  |--POST /api/v3/checks/ ------------>|
  |   {"name":"Backup","slug":"backup"}|
  |<--201 (slug: "backup")-------------|
  |                                    |
  |--POST /ping/<ping-key>/backup/0--->|  (exit_status=0, success)
  |<--200 OK---------------------------|
  |                                    |
  |--POST /ping/<ping-key>/backup/1--->|  (exit_status=1, failure)
  |<--200 OK (status now "down")-------|
```

### 9.4 Integration Setup Flow

```
1. GET  /accounts/login/               -> 200 + csrftoken cookie
2. POST /accounts/login/               -> 302 + sessionid
3. GET  /                              -> 200, extract project UUID
4. GET  /projects/<uuid>/add_email/    -> 200 + csrftoken
5. POST /projects/<uuid>/add_email/    -> 302 (channel created)
      value=notify@example.com&up=true&down=true&csrfmiddlewaretoken=<tok>
```

### 9.5 Check Filtering Rules Setup

```
1. Login (steps 1-2 above)
2. POST /api/v1/checks/                  -> 201 (get check UUID)
3. GET  /checks/<uuid>/details/          -> 200 (extract CSRF from HTML)
4. POST /checks/<uuid>/filtering_rules/  -> 302
      filter_subject=on&filter_body=on&keywords=error+fail+critical&csrfmiddlewaretoken=<tok>
```

### 9.6 Pause and Resume via UI

```
1. Login
2. POST /api/v1/checks/            -> 201
3. GET  /checks/<uuid>/details/    -> 200 (get CSRF from HTML)
4. POST /checks/<uuid>/pause/      -> 302
5. POST /checks/<uuid>/resume/     -> 302
```

### 9.7 API key dedup (`unique` field)

```
POST /api/v1/checks/  {"name":"X","timeout":3600,"grace":60}          -> 201
POST /api/v1/checks/  {"name":"X","timeout":3600,"grace":60,
                       "unique":["name"]}                              -> 200 (existing returned)
POST /api/v1/checks/  {"name":"X","timeout":9999,"grace":60,
                       "unique":["name","timeout"]}                    -> 201 (new, different timeout)
POST /api/v1/checks/  {"name":"X","timeout":9999,"grace":60,
                       "unique":[]}                                    -> 201 (new, empty unique)
```

---

## 10. Error Response Formats

### JSON API Errors (Content-Type: application/json)

```json
{"error": "missing api key"}
{"error": "wrong api key"}
```

### HTTP Status Code Summary

| Status | Meaning in this app |
|---|---|
| 200 | Success (also returned for form validation errors in HTML responses) |
| 201 | Check created successfully |
| 204 | No Content (OPTIONS request) |
| 302 | Redirect: login success, form submit success, logout |
| 400 | Validation error (bad field, malformed UUID, exit_status > 255) |
| 401 | Missing or invalid API key |
| 403 | Missing CSRF token, or unauthenticated POST |
| 404 | Resource not found, disabled integration, wrong badge key |
| 405 | Method not allowed (e.g. PATCH/PUT on list endpoint) |

---

## 11. Implementation Roadmap

Prioritised by test volume and inter-dependencies.

### Phase 1 — Core Authentication (blocks everything else)

| Endpoint | Approx test count |
|---|---|
| `GET /accounts/login/` | 15+ |
| `POST /accounts/login/` | 15+ |
| Session middleware | All auth-required tests |
| CSRF middleware | All form POST tests |
| Cookie storage | All multi-step tests |

### Phase 2 — API Key Validation + Check CRUD

| Endpoint | Tests |
|---|---|
| `POST /api/v1/checks/` | 20+ |
| `GET /api/v1/checks/` | 5+ |
| `GET /api/v1/checks/<uuid>` | 4 |
| `POST /api/v1/checks/<uuid>` (update) | 4 |
| `DELETE /api/v1/checks/<uuid>` | 3 |
| `POST /api/v1/checks/<uuid>/pause` | 2 |
| `POST /api/v1/checks/<uuid>/resume` | 1 |
| `OPTIONS /api/v1/checks/<uuid>` | 1 |
| `PATCH/PUT /api/v1/checks/` (405) | 2 |

### Phase 3 — Ping Endpoints

| Endpoint | Tests |
|---|---|
| `POST /ping/<uuid>` | 5+ |
| `GET /ping/<uuid>` | 2 |
| `HEAD /ping/<uuid>` | 1 |
| `POST /ping/<uuid>/fail` | 1 |
| `POST /ping/<uuid>/start` | 1 |
| `POST /ping/<uuid>/<exit>` | 3 |
| `POST /ping/<pk>/<slug>` | 2 |
| `POST /ping/<pk>/<slug>/<exit>` | 2 |
| Malformed UUID -> 400 | 1 |

### Phase 4 — API Supplementary

| Endpoint | Tests |
|---|---|
| `GET /api/v1/checks/<uuid>/pings/` | 3 |
| `GET /api/v1/checks/<uuid>/pings/<n>/body` | 2 |
| `GET /api/v1/channels/` | 1 |
| `GET /api/v1/badges/` | 1 |
| `GET /badge/...` | 1 |
| `POST /api/v1/bounces/` | 1 |
| `POST /api/v1/notifications/status/` | 1 |

### Phase 5 — API v3

| Endpoint | Tests |
|---|---|
| `POST /api/v3/checks/` (with slug) | 3 |
| `GET /api/v3/checks/` (slug field) | 1 |
| `GET /api/v3/checks/<slug>` | 1 |

### Phase 6 — Front-End / UI

| Endpoint | Tests |
|---|---|
| `GET /` (dashboard) | many |
| `GET /checks/<uuid>/details/` | 4 |
| `POST /checks/<uuid>/filtering_rules/` | 1 |
| `POST /checks/<uuid>/pause/` | 1 |
| `POST /checks/<uuid>/resume/` | 1 |
| `GET /checks/<uuid>/log_events/` | 2 |
| `GET /checks/<uuid>/pings/<n>/` | 1 |
| `GET /checks/<uuid>/transfer/` | 1 |
| `POST /checks/<uuid>/transfer/` | 1 |
| Docs pages (`/docs/`, `/docs/api/`, etc.) | 4 |
| `POST /docs/search/` | 1 |

### Phase 7 — Account Management

| Endpoint | Tests |
|---|---|
| `GET /accounts/profile/` | 2 |
| `POST /accounts/profile/notifications/` | 1 |
| `POST /accounts/profile/appearance/` | 1 |
| `GET/POST /accounts/change_email/` | 2 |
| `GET/POST /accounts/set_password/` | 3 |
| `GET/POST /accounts/close_account/` | 2 |
| `POST /accounts/signup/` | 2 |
| `GET /accounts/signup/csrf/` | 2 |
| `GET /accounts/verify_email/<token>/` | 2 |
| `GET /accounts/unsubscribe/alerts/<token>/` | 1 |
| `GET /accounts/unsubscribe/reports/<token>/` | 1 |
| `POST /accounts/logout/` | 1 |
| `POST /accounts/transfer/` | 2 |

### Phase 8 — Integrations

| Endpoint | Tests |
|---|---|
| `GET/POST /projects/<uuid>/add_email/` | 2 |
| `GET/POST /projects/<uuid>/add_webhook/` | 3 |
| `GET/POST /projects/<uuid>/add_slack/` | 1 |
| `GET /projects/<uuid>/add_googlechat/` | 1 |
| `GET /projects/<uuid>/add_mattermost/` | 1 |
| `GET /projects/<uuid>/add_msteams/` | 1 |
| `GET /projects/<uuid>/add_prometheus/` | 1 |
| `GET /projects/<uuid>/add_zulip/` | 1 |
| `GET /projects/<uuid>/add_signal/` | 1 |
| `GET /projects/<uuid>/add_group/` | 1 |
| Disabled integrations -> 404 | 1 |

### Phase 9 — Payments & Billing

| Endpoint | Tests |
|---|---|
| `GET /pricing/` | 1 |
| `GET /accounts/profile/billing/` | 1 |
| `POST /accounts/profile/billing/` | 1 |
