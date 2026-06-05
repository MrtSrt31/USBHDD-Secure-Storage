# USBHDD Secure Storage

A self-hosted, secure file storage and sharing system built with Python/Flask. Designed to serve files from external drives or any local directory over a local network via HTTPS, with encrypted thumbnails, an admin panel, user management, and multi-language support (English / Turkish).

---

## Features

- **HTTPS by default** — auto-generates a self-signed TLS certificate on first run
- **First-run setup wizard** — create the admin account and first share directly from the browser
- **Admin panel** — manage users, shares, and per-user folder permissions
- **Role-based access** — `admin` and `user` roles with granular share permissions
- **Brute-force protection** — automatic IP banning after repeated failed login attempts
- **Encrypted thumbnail cache** — image thumbnails stored encrypted with Fernet AES-128
- **Encrypted file index** — background night-mode scanner indexes all files with Fernet encryption
- **Media viewer** — in-browser image and video viewer with keyboard navigation
- **File upload & folder creation** — authenticated users can upload files and create directories
- **CSRF protection** — all forms are protected via Flask-WTF
- **Secure data folder** — all sensitive files (DB, certs, cache) stored in `data/` with `700`/`600` permissions
- **Multi-language UI** — English and Turkish, switchable at runtime via `/lang/<code>`

---

## Requirements

- Python 3.9+
- pip packages listed below

```
flask
flask-wtf
pillow
cryptography
gunicorn
werkzeug
```

Install all dependencies:

```bash
pip install flask flask-wtf pillow cryptography gunicorn werkzeug
```

---

## Running

### Development (Flask built-in server)

```bash
python backend.py
```

### Production (Gunicorn)

```bash
python run.py
```

The server starts on port **8143** by default (auto-increments if busy).  
Open `https://<your-ip>:8143` in your browser.

> **Note:** Your browser will show a certificate warning because the certificate is self-signed. This is expected — click "Advanced → Proceed" to continue.

---

## First-Time Setup

1. Open the app in your browser — you will be redirected to `/setup`
2. Create an admin username and password
3. Add a share name and pick a folder path from your machine or connected drive
4. Click **Complete** — you will be redirected to the login page
5. Log in with your admin credentials

---

## Project Structure

```
.
├── backend.py        # Main application (all routes, logic, HTML templates)
├── run.py            # Gunicorn launcher with network discovery
├── setup.py          # Build/packaging script
├── Beni_oku.txt      # Turkish notes file
├── .gitignore
├── data/             # Auto-created at runtime — NOT committed to git
│   ├── cert.pem      # TLS certificate (600)
│   ├── key.pem       # TLS private key (600)
│   ├── s9x_secure_storage.db  # SQLite database (600)
│   └── cache/        # Encrypted thumbnail cache (700)
└── README.md
```

---

## Security Notes

| Measure | Detail |
|---|---|
| Transport | HTTPS with auto-generated self-signed cert |
| Passwords | Werkzeug `pbkdf2:sha256` hashing |
| Sessions | Secure, HttpOnly, SameSite=Lax cookies |
| CSRF | Flask-WTF token on all POST forms |
| Thumbnails | Fernet AES-128 encrypted on disk |
| File index | Fernet AES-128 encrypted paths & names |
| Data folder | `700` (dir) / `600` (files) POSIX permissions |
| Brute-force | Failed attempts tracked per IP, auto-ban applied |

> The `data/` directory is excluded from git via `.gitignore`. Never commit `cert.pem`, `key.pem`, or the `.db` file.

---

## Language Support

The UI supports **English** and **Turkish**. Switch language by visiting:

- `/lang/en` — Switch to English
- `/lang/tr` — Switch to Turkish

The selected language is stored in the session and persists until changed or logged out.

---

## Changelog

### v1.0.2 — UI Improvements

#### CSS (global)

- **Custom scrollbars** — slim, styled to match the dark theme
- **Better file cards** — square `aspect-ratio:1` thumbnails instead of fixed height; smoother hover with layered shadow + translate
- **List view** — new `.view-list` class for a compact row layout, persisted to `localStorage`
- **Drag-drop overlay** — full-page overlay with animated border when dragging files over the browser window
- **Upload toast** — non-blocking notification in the corner (uploading / success / error)
- **Custom confirm dialog** — replaces browser `confirm()` with a modal that matches the app's style
- **Empty state** — friendly message + icon when a folder has no files
- **Light theme polish** — section header backgrounds + drop overlay tint
- **Navbar** — slightly taller, better focus ring on search input, search-clear button
- **Buttons** — added `active` state scaling, cleaner hover colors (no `filter:brightness` hack)
- **Monitor bar** — multi-color gradient + `background-position` animation instead of `scaleX`

#### Login & Setup pages

- **Password show/hide toggle** — 👁 button inside the input
- **Loading state** — submit button disables and shows `…` on click to prevent double-submit
- **Better sizing** — card uses `max-width: calc(100vw - 32px)` for small screens

#### File Browser (`/`)

- **Grid ↔ List toggle** — button in navbar, state saved across page loads
- **Search clear button** — ✕ appears inside the search bar when there's a query
- **Drag-and-drop upload** — drop any file anywhere on the page; uses the existing `/upload/` endpoint with the CSRF token from the existing form
- **Custom delete confirmation** — modal instead of `window.confirm()`, with filename shown
- **Empty folder state** — shown when folder has no items
- **Media viewer** — now shows filename at top and `1 / N` counter at bottom; keyboard arrows still work

#### Admin Panel

- **Section headers** — background differentiates them from content rows
- **Better monitor** — calls `updateMonitor()` immediately on load instead of waiting 2 s
- **Readable HTML** — template is properly indented (no functional change)

---

## Contributors

- **[MrtSrt31](https://github.com/MrtSrt31)** — creator & maintainer

---

## License

MIT License — use freely, attribution appreciated.
