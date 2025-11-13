-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) DEFAULT 'patient', -- e.g. 'patient', 'admin', 'dentist'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- CHAT SESSIONS TABLE
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    status          VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'completed', 'abandoned'
    metadata        JSONB,
    last_message_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_started_at
    ON chat_sessions (user_id, started_at DESC);

-- APPOINTMENTS TABLE
CREATE TABLE IF NOT EXISTS appointments (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_session_id  UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    start_time       TIMESTAMPTZ NOT NULL,
    end_time         TIMESTAMPTZ NOT NULL,
    status           VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'confirmed', 'cancelled', 'rescheduled'
    notes            TEXT,
    provider_name    VARCHAR(255),
    location         VARCHAR(255),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_provider_time
    ON appointments (provider_name, start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_user_time
    ON appointments (user_id, start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_status_time
    ON appointments (status, start_time);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_type     VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created_at
    ON chat_messages (chat_session_id, created_at);
