-- Crevio Bot — Cloudflare D1 schema
-- Run this once in Cloudflare Dashboard -> D1 -> your DB -> Console
-- (paste the whole file and execute)

CREATE TABLE IF NOT EXISTS users (
    telegram_id     INTEGER PRIMARY KEY,
    first_name      TEXT NOT NULL,
    username        TEXT,
    balance         REAL NOT NULL DEFAULT 0,
    total_spent     REAL NOT NULL DEFAULT 0,
    total_minutes   REAL NOT NULL DEFAULT 0,
    joined_channel  INTEGER NOT NULL DEFAULT 0,
    has_rated       INTEGER NOT NULL DEFAULT 0,
    ref_by          INTEGER,
    ref_count       INTEGER NOT NULL DEFAULT 0,
    ref_earning     REAL NOT NULL DEFAULT 0,
    api_key         TEXT UNIQUE,
    active_call_id  INTEGER,
    phone_number    TEXT,
    joining_date    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id       TEXT UNIQUE NOT NULL,
    telegram_id  INTEGER NOT NULL,
    type         TEXT NOT NULL,          -- 'call' | 'deposit'
    amount       REAL NOT NULL,
    method       TEXT,                   -- 'INR' | 'TRX' | NULL for calls
    status       TEXT NOT NULL,          -- 'success' | 'failed' | 'completed'
    detail_json  TEXT,                   -- extra info as JSON text
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_deposits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id      INTEGER NOT NULL,
    method           TEXT NOT NULL,      -- 'INR' | 'TRX'
    requested_amount REAL NOT NULL,      -- amount user must pay (unique for TRX)
    razorpay_order_id TEXT,
    status           TEXT NOT NULL DEFAULT 'pending', -- 'pending'|'paid'|'expired'
    created_at        TEXT NOT NULL,
    expires_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id   INTEGER NOT NULL,
    number        TEXT NOT NULL,
    edesy_call_id TEXT,
    status        TEXT NOT NULL DEFAULT 'ongoing', -- 'ongoing'|'completed'|'failed'
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    duration_sec  INTEGER NOT NULL DEFAULT 0,
    cost          REAL NOT NULL DEFAULT 0,
    via_api       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(telegram_id);
CREATE INDEX IF NOT EXISTS idx_calls_user ON calls(telegram_id);
CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_deposits(status);
