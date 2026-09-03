# Dubble - Sprint 2: Seed & SDK Architecture Refactor

**Goal:** Fix two architectural decisions from Phase 1 that don't match standard self-custodial practice, plus the P0/P1 blockers found in the audit.

**Started:** 2026-08-01
**Status:** Active (pre-work ✅, Task A ✅, Task B ✅, tests ✅)

---

## Why This Sprint

Research uncovered two issues with the Phase 1 architecture:

| Issue | Phase 1 Approach | Standard Practice | Risk |
|-------|------------------|-------------------|------|
| Seed derivation | `PBKDF2(password)` — mnemonic derived from credentials | Random BIP39 mnemonic, encrypted with password, stored in DB | Password change = wallet loss. No seed backup possible. KDF changes break all wallets. |
| SDK lifecycle | Shared in-memory cache per user + background event loop thread | `default_server_config` — one SDK per request, build/disconnect | Thread safety risk. Memory leak. Unnecessary complexity. SDK has an official server mode. |

Both are fixable and independent — can be done in either order.

---

## Pre-work: Audit Blockers (P0/P1)

The Sprint 2 audit found the app was non-functional and had a security gap. Fixed first:

- [x] **P0 — `user_loader` 500s:** `app/__init__.py` returned the raw `User` model instead of `LoginUser`, so `current_user.is_authenticated` raised `AttributeError` on every protected route. Fixed by wrapping in `LoginUser`.
- [x] **P0 — JS CSRF broken:** `static/app.js` reads `X-CSRFToken` from a meta tag that never existed on dashboard pages, so all JS POSTs would 400. Fixed by adding `<meta name="csrf-token">` to `base.html`.
- [x] **P1 — `confirm_payment` auth gap:** `/api/confirm/<hash>` let any logged-in user mark *any* pending invoice paid (crediting a bubble without payment) and never verified against the SDK. Now scoped to the current user (`confirm_payment(user_id, ...)`). Real SDK payment verification is deferred to Sprint 3.

---

## Task A: Random Mnemonic + Encrypted Storage

### Current Flow

```
Register → PBKDF2(password) → Seed.ENTROPY(entropy) → wallet
Login    → PBKDF2(password) → reproduce same mnemonic → connect SDK
```

### Target Flow

```
Register → os.urandom(32) → BIP39 mnemonic → encrypt with password → DB
         → show mnemonic to user: "write this down"
Login    → load encrypted mnemonic from DB → decrypt with password → connect SDK
```

### Implementation

- [x] **A1. Random mnemonic on registration** — `app/auth.py:generate_mnemonic()` uses `os.urandom(32)` → 24-word BIP39 mnemonic (`Mnemonic.to_mnemonic`). No longer derived from credentials.
- [x] **A2. Encrypt mnemonic with password-derived key** — AES-256-GCM (`cryptography`) with PBKDF2-SHA256 key derivation (100,000 iterations, per-user 16-byte salt). Payload = `base64(nonce || ciphertext || tag)` stored in `Wallet.mnemonic_encrypted`; salt hex in `Wallet.encryption_salt`.
- [x] **A3. Decrypt mnemonic on login** — `app/routes/auth_routes.py:login()` decrypts with password + stored salt, then hands the mnemonic to the SDK layer. Wrong password cannot unlock (fails auth-tag).
- [x] **A4. Show mnemonic once after registration** — new `app/templates/backup_mnemonic.html` displays the phrase with a warning and a mandatory "I have written down my recovery phrase" acknowledgment, then redirects to login.
- [ ] **A5. Password change flow** — deferred to Sprint 3.

### Design note: per-session mnemonic cache

Decryption needs the password, which is not available after login. The SDK layer keeps a short-TTL in-memory cache (`app/lightning.py`, keyed by `user_id`, 1h TTL, evicted on logout). This avoids storing the password or mnemonic in the client-side Flask session cookie. A server restart forces re-login (acceptable pre-alpha).

### Files Changed

- `app/models.py` — `Wallet.mnemonic_encrypted` (Text), `Wallet.encryption_salt` (String(32))
- `app/auth.py` — `generate_mnemonic()`, `encrypt_mnemonic()`, `decrypt_mnemonic()`; `register_user()` returns the mnemonic
- `app/routes/auth_routes.py` — registration renders backup page; login decrypts + caches; logout drops cache; safe `next` redirect
- `app/templates/backup_mnemonic.html` — new; `static/style.css` — mnemonic box styles
- `requirements.txt` — `cryptography>=42`

### Backward Compatibility

- [x] **Old DB dropped** (`instance/Dubble.db`, `data/wallets/`) — existing Phase-1 users must re-register. Pre-alpha, acceptable.

---

## Task B: Switch to Breez SDK Server Mode

### Current Flow

```
Login → get_sdk() checks _sdk_instances[user_id]
     → not found → _connect_sdk() → asyncio.run(connect())
     → cached in global dict forever
     → every operation fetches cached instance

Background: daemon thread runs asyncio.run_forever()
All async calls submitted via run_coroutine_threadsafe()
```

### Target Flow

```
Login → build SDK → do work → disconnect()
Next request → build fresh SDK → do work → disconnect()

No background thread. No global SDK cache. No threading.Lock.
```

### Implementation

- [x] **B1. `default_server_config`** — `app/lightning.py:_build_sdk()` uses `default_server_config(Network.MAINNET)` (`background_tasks_enabled=False`).
- [x] **B2. `SdkBuilder`** — `SdkBuilder(config=config, seed=seed)` → `await builder.with_default_storage(storage_dir=...)` → `await builder.build()`.
- [x] **B3. Manual `sync_wallet()`** — called once after connect so `get_info()` returns fresh balance (verified working against real Spark mainnet).
- [x] **B4. Global cache/loop removed** — `_sdk_instances`, `_lock`, `_loop`, `_loop_thread` all deleted. Each op builds SDK → works → `await sdk.disconnect()` in a `finally`.
- [x] **B5. Sync Flask wrapper** — `_run()` creates a per-call event loop (`asyncio.new_event_loop()` + `run_until_complete` + close). No thread safety concerns.

### Files Changed

- `app/lightning.py` — full rewrite to server mode + mnemonic cache
- `app/bubble.py`, `app/routes/*` — function signatures unchanged, no edits required for Task B

### Verification

- [x] Real SDK connect + sync + `get_info` against Spark mainnet (balance 0 on fresh wallet)
- [x] Full flow via test client: register → login → blow → **real `lnbc` invoice generated** (mock: False)

---

## Tests

- [x] `tests/conftest.py` — app fixture (temp SQLite, CSRF on, price mocked), register/login/API helpers
- [x] `tests/test_auth.py` — encrypted wallet creation, 24-word mnemonic, login + protected routes, wrong password, logout
- [x] `tests/test_encryption.py` — round-trip, unique salts/ciphertexts, wrong-password and tamper rejection
- [x] `tests/test_bubbles.py` — blow/confirm/double flow (mock mode), ownership enforcement, CSRF required on API, withdraw, pop

**Result: 17 passed.** `pytest` added to `requirements.txt`.

---

## Migration / Cleanup

- [x] Old DB dropped, `data/wallets/` removed (re-register required)
- [x] Full walkthrough: register → back up mnemonic → login → blow (real invoice) → double → withdraw

---

## Rollback Plan

If things break:
- `git checkout -- app/ static/ requirements.txt`
- `pip uninstall cryptography`
- Drop DB and recreate
- Revert to `main` branch (pre-sprint state still has the old cached-SDK + derived-mnemonic code)

---

## Sprint 3: Close the Security Gaps

**Goal:** Close the three security gaps deferred from Sprint 2. No MCP wrapper — that stays parked.

**Started:** 2026-09-01
**Status:** Shipped

### Task 1 — Real payment verification in `confirm_payment`

**Problem:** `confirm_payment` trusted the client POST — any logged-in user could flip any *own* invoice to paid without actually paying, crediting a bubble for nothing. The P1 ownership check from Sprint 2 stopped cross-user abuse, but the verify-vs-pay gap remained.

**Fix:**
- `app/bubble.py:confirm_payment` now calls `check_received_payment(user_id, invoice.payment_request)` against the Breez SDK **before** flipping `status='paid'`.
- If the SDK reports no matching payment → returns `400 'Payment not yet received'`, invoice stays `pending`.
- If the SDK errors (node down etc.) → surfaced as `400` with the SDK error; balance untouched.
- Only on confirmed receipt does the bubble get credited.

**Tests:** mock-mode `check_received_payment` returns `paid: True` (matches existing behavior), so the happy path is unchanged. New hermetic tests cover the not-yet-paid, on-receipt-credit, and SDK-error branches.

### Task 2 — Server-side sessions for the mnemonic cache

**Problem:** The decrypted mnemonic lived in a module-level `dict[int, tuple]` keyed by user_id — shared server-side, but lost on restart and tracked only by an opaque TTL. Not tied to the user's session.

**Fix:**
- Replaced `_mnemonics` dict with the **server-side session** via `flask-session` (CacheLib `FileSystemCache`, dir `instance/sessions/`, 1h timeout).
- `cache_mnemonic` / `get_cached_mnemonic` / `drop_mnemonic` now read/write `flask.session` (`_dubble_mnemonic`, `_dubble_mnemonic_at`).
- The mnemonic **never appears in the client cookie** — verified by a test asserting the encrypted seed isn't in `Set-Cookie`.
- Logout still calls `drop_mnemonic`, clearing the session.
- Accepted tradeoff (September scope): filesystem sessions are per-process; a server restart with cleared `instance/` forces re-login. Production hardening (Redis/Postgres sessions) is Sprint 4.

**Files:** `requirements.txt` (+`flask-session`), `app/config.py` (CacheLib session config), `app/__init__.py` (init `Session()`), `app/lightning.py`.

### Task 3 — Change-password endpoint

**Problem:** No way to change a password. Since the wallet mnemonic is encrypted with a password-derived key, a naive password change would strand the wallet under the old key.

**Fix:**
- `app/auth.py:change_password(user, old, new)` — verifies the old password **and** that it decrypts the mnemonic, then re-encrypts the mnemonic with the new password and updates the bcrypt hash in a single `db.session.commit()` (atomic rekey).
- `GET/POST /change-password` (`app/routes/auth_routes.py`), `@login_required`. On success clears the mnemonic session and forces re-login.
- `app/templates/change_password.html` + a link in the index header menu.

**Atomicity:** decryption happens *before* any write; mnemonic + hash update in one commit, so a partial failure can't leave a wallet the new password can't unlock.

**Tests:**
- Success rekeys the wallet (old hash changes, new password decrypts a valid 24-word mnemonic).
- Old password fails to log in after the change; new password works.
- Wrong current password rejected (stays on page, 200).
- Mismatched confirmation rejected.
- Mnemonic not present in the client cookie.

### Verification

- `pytest`: **25 passed** (17 Sprint-2 + 8 new).
- Automated suite is **money-free** — all payment logic runs in mock mode. The real `check_received_payment` against a funded mainnet wallet is a **manual walkthrough** on the prefunded node.

### Sprint 4 Candidates (deferred, not dropped)

- Alembic migrations + PostgreSQL
- Redis/Postgres-backed sessions (production hardening)
- **MCP server wrapper** (balance, invoice, pay, wallet state — driven from `.md` spec) — parked by decision on 2026-09-01
- Real-manual-payment continuous verification / CI integration

