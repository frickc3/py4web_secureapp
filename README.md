# VaultApp — a py4web app on a SQLCipher-encrypted database

A minimal [py4web](https://github.com/web2py/py4web) application where **every
user record is stored inside a SQLCipher (AES-256) encrypted SQLite file**,
with register / login / logout flows powered by py4web's built-in `Auth`.

```
┌─────────────────────────────────────────────────────────────┐
│  browser ──▶ py4web (secureapp) ──▶ pyDAL custom adapter    │
│                 Auth middleware      sqlcipher://secure.db  │
│                 (sessions, forms)        │                  │
│                                          ▼                  │
│                                  SQLCipher driver           │
│                                  databases/secure.db        │
│                                  (AES-256 at rest)          │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

* Python 3.10+
* `pip install py4web sqlcipher3`

## Run

```bash
cd webapp
python -m py4web run .
```

Then open **http://127.0.0.1:8000** 

## What it demonstrates

* **Register** — POST form at `/secureapp/auth/register`
  (username, email, password + confirmation; PBKDF2 password hashing happens
  inside `Auth`/`CRYPT` before anything touches the database).
* **Login** — `/secureapp/auth/login` (username or email + password).
  Sessions are signed+encrypted cookies keyed by a generated secret in
  `private/session_key.txt`.
* **Logout** — `/secureapp/auth/logout` clears the session.
* **Guarded pages** — `@authenticated()` (from `common.py`) redirects any
  anonymous request to the login page with `?next=…` round-trip.
* **Encrypted storage** — a `secure_note` table only the logged-in user can
  read/write, stored in the ciphered db file.

## How the SQLCipher wiring works

pyDAL has no SQLCipher dialect, so the app registers one at import time:

1. **Driver** — `secureapp/sqlcipher_adapter.py` injects the `sqlcipher3`
   module into `pydal.drivers.DRIVERS`.
2. **Adapter** — subclasses pyDAL's SQLite adapter, registered for the
   `sqlcipher://` URI scheme. On *every* connection it immediately executes
   `PRAGMA key = '<key>'` before anything else, then probes
   `SELECT count(*) FROM sqlite_master` so a wrong key fails fast with a
   clear message instead of corrupt-looking errors later.
3. **Key management** — `secureapp/settings.py`:
   * `SQLCIPHER_KEY` environment variable (recommended in production), or
   * auto-generated `secureapp/private/db_key.txt` on first run.

> **Losing the key file = losing the database.** Back up
> `private/db_key.txt` and restrict who can read it. The key never appears
> in the database files themselves.

### Verified at-rest properties

| access | result |
|---|---|
| file header | random bytes — no `SQLite format 3` magic |
| stdlib `sqlite3` open | `DatabaseError: file is not a database` |
| SQLCipher without key | `DatabaseError: ... hmac check failed for pgno=1` |
| SQLCipher with wrong key | same `hmac check failed` |
| SQLCipher with `private/db_key.txt` key | full read/write access |

## Key files

```
webapp/
└─ secureapp/
   ├─ sqlcipher_adapter.py   ← pyDAL SQLCipher dialect (driver + adapter)
   ├─ settings.py            ← DB URI, key loading, auth options
   ├─ common.py              ← registers dialect, builds DAL/Auth/session
   ├─ models.py              ← auth_user (from Auth) + secure_note demo table
   ├─ controllers.py         ← index (public), secure (login required)
   ├─ templates/             ← layout, auth card, index, secure pages
   ├─ private/               ← secrets (auto-generated): db_key.txt, session_key.txt
   └─ databases/             ← secure.db (AES-encrypted) + migration files
```

## Adjusting security

* Real password strength: set `PY4WEB_MODE=any` (non-development) → entropy 50, or edit
  `PASSWORD_ENTROPY` in `settings.py`.
* Email verification flow: set `VERIFY_EMAIL = True` and fill the `SMTP_*` vars
  in `settings.py`.
* Key rotation: SQLCipher supports `PRAGMA key` + `ATTACH ... KEY` rekey — see
  https://discuss.zetetic.net (docs) before attempting.

## Notes / gotchas found in the wild

* If a top-level `pathlib-1.0.1` backport package is installed in user
  site-packages it can shadow the stdlib `pathlib` for anything that prepends
  user-site to `sys.path` — uninstall it if you see
  `ImportError: cannot import name 'Sequence' from 'collections'`.
* py4web's scaffold `__init__.py` imports `controllers` *before* `models`,
  so any table your controllers reference at request time must be defined in
  `models.py` (as here) — importing it in the controller is fine too.
* Do **not** mix `@action()/@action.uses()` with the `ActionFactory`
  decorators (`@unauthenticated()`, `@authenticated()`); the factory already
  registers the route and would raise `RouteMethodError`.
