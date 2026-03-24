# postgress
sudo apt update
sudo apt upgrade
sudo apt install postgresql postgresql-contrib

### Allow Remote Connections
Edit postgresql.conf:Find the file (usually in /etc/postgresql/16/main/) and locate listen_addresses.Bash

Change:
```
# listen_addresses = 'localhost'
# To:
listen_addresses = '*'
```

Edit pg_hba.conf
This file controls client authentication. Add a line at the end to allow your specific IP address or a range
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             0.0.0.0/0               md5
```

### password 
Before connecting remotely, ensure you have set a strong password for the default postgres user by opening the postgres prompt
```sudo -u postgres psql``` 
and typing ```\password postgres.```

or
```ALTER USER postgres WITH PASSWORD 'your_extremely_secure_password';```
**Dont forget semicolns ; at the end**



### update firewall
sudo ufw allow 5432/tcp

### restart and verify
sudo systemctl restart postgresql

---



 ### create the .env
Set real values:
```
SECRET_KEY=generate-a-64-char-random-string
JWT_EXPIRY_HOURS=24
DATABASE_PATH=/opt/nurser/nurser.db
BULKSMS_USERNAME=your_bulksms_username
BULKSMS_PASSWORD=your_bulksms_password
agent_mail_nurser=am_us_...your_agentmail_key
agentmail_inbox_id=nurser@agentmail.to
support_email=you@yourdomain.com
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run with systemd (production)

Create `/etc/systemd/system/nurser.service`:

```ini
[Unit]
Description=nurser API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/nurser
ExecStart=/opt/nurser/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5
EnvironmentFile=/opt/nurser/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable nurser
sudo systemctl start nurser
sudo systemctl status nurser
```

### 6. Nginx reverse proxy (optional but recommended)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then add HTTPS with certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## API Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /health | No | Health check |
| POST | /auth/register | No | Register (name, phone, password) |
| POST | /auth/verify-phone | No | Verify OTP |
| POST | /auth/login | No | Login → sets JWT cookie |
| POST | /auth/logout | No | Clear JWT cookie |
| POST | /auth/resend-otp | No | Resend OTP |
| GET | /users/me | Yes | Get current user profile |
| PATCH | /users/me | Yes | Update profile |
| POST | /users/me/password | Yes | Change password |
| GET | /teams | Yes | List my teams |
| POST | /teams | Yes | Create team |
| GET | /teams/{id} | Yes | Get team details |
| PATCH | /teams/{id} | Yes | Update team (admin) |
| DELETE | /teams/{id} | Yes | Delete team (admin) |
| GET | /teams/{id}/notices | Yes | Get team notices |
| PATCH | /teams/{id}/notices | Yes | Update notices (contributor+) |
| GET | /teams/{id}/members | Yes | List members |
| PATCH | /teams/{id}/members/{uid} | Yes | Change role (admin) |
| DELETE | /teams/{id}/members/{uid} | Yes | Remove member (admin) |
| POST | /teams/{id}/invite | Yes | Generate invite code (admin) |
| POST | /teams/join/{code} | Yes | Join via invite code |
| GET | /teams/{id}/event-types | Yes | List event types |
| POST | /teams/{id}/event-types | Yes | Create event type (admin) |
| PATCH | /teams/{id}/event-types/{tid} | Yes | Update event type (admin) |
| DELETE | /teams/{id}/event-types/{tid} | Yes | Delete event type (admin) |
| POST | /events | Yes | Log an event |
| GET | /events?team_id=X | Yes | List events (timeline) |
| GET | /events/{id} | Yes | Get single event |
| PATCH | /events/{id} | Yes | Edit event |
| DELETE | /events/{id} | Yes | Delete event |
| POST | /notifications/subscribe | — | Stub (returns 501) |
| POST | /support/feedback | Yes | Send feedback via AgentMail |

---

## Frontend Pages

All pages are served by the FastAPI server from `frontend/`.
**Always open the app via `http://localhost:8001`** — do not open the `.html` files directly from disk.
Opening files via `file://` breaks session persistence because browsers block same-site cookies across schemes.

| File | Description |
|------|-------------|
| `login.html` | Phone + password login, register, OTP verification |
| `contributor.html` | Main nurse view — event grid, timeline, pinned note, shift toggle |
| `admin.html` | Team admin — event types, members, invite codes |
| `profile.html` | User profile, change password, logout |

### Flow
1. Open `login.html` — register with name + phone + password
2. Enter the OTP code (printed to terminal in dev, sent via BulkSMS in prod)
3. Lands on `contributor.html` — the main nursing view
4. Tap ⚙️ to manage teams, create a team, or join via invite code
5. Team admin opens `admin.html?team_id=X` from the ⚙️ gear menu

### `API_BASE`
All pages use `const API_BASE = 'http://localhost:8001'` at the top of their `<script>` block.
To point to a production server, change this value in each file (or add a shared `config.js`).

---

## Database

- SQLite file at `DATABASE_PATH` (default: `nurser.db`)
- 6 tables: `users`, `teams`, `team_memberships`, `event_types`, `events`, `invite_codes`
- Created automatically on first startup
- To reset: delete `nurser.db` and restart

## BulkSMS Setup

1. Create account at https://www.bulksms.com
2. Copy your username and password to `.env` as `BULKSMS_USERNAME` and `BULKSMS_PASSWORD`
3. In dev, set `BULKSMS_USERNAME=placeholder` — OTPs will print to the console instead

## AgentMail Support Email

Support feedback from the app is sent via AgentMail to the address in `support_email`.
- Requires `agent_mail_nurser` API key in `.env`
- Inbox: `agentmail_inbox_id` (e.g. `nurser@agentmail.to`)
