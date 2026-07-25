# Dubble - Sprint Plan: Phase 1

**Goal:** Wire real Breez SDK Lightning to the bubble flow — generate real invoices, confirm real payments, real withdrawals.

**Started:** 2026-07-24
**Status:** Active

---

## Sprint 1: Real Lightning Flow

### Tasks

- [ ] Add `storage_dir` column to `Wallet` model (e.g. `data/wallets/{user_id}`)
- [ ] Update `auth.py` `register_user()` to set `storage_dir` on wallet creation
- [ ] Update `auth_routes.py` login to derive mnemonic and connect SDK
- [ ] Update `auth_routes.py` logout to disconnect SDK
- [ ] Update `bubble.py` to pass `user_id` to all lightning calls
- [ ] Update `bubble_routes.py` if needed for new function signatures
- [ ] Delete old test DB and re-run full flow
- [ ] Test: register → login → blow bubble (real invoice) → confirm → double → withdraw
- [ ] Verify mock fallback still works when SDK unavailable
- [ ] Update `requirements.txt` to add `mnemonic`

### Key Decisions

- **Seed derivation:** PBKDF2(password + username, server_salt) — mnemonic never stored, reproducible from credentials
- **SDK connection:** cached in memory per user_id, created on login, destroyed on logout
- **Storage:** each user gets `data/wallets/{user_id}/` for SDK state
- **Mock mode:** still works when SDK unavailable (graceful fallback)

### Risk

- User forgets password → wallet inaccessible (correct self-custodial model — warn during registration)
- Server restart → users need to re-login to reconnect SDK (acceptable for v1)

---

## After Sprint 1

- Payment polling improvements (check pending invoices against real SDK)
- Error handling for failed payments
- Balance sync on login
- User-facing warnings about password recovery
