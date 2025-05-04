-- Migración inicial para NGX Agents
-- Crea las tablas necesarias para la persistencia de usuarios y conversaciones

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE,
    api_key TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para búsqueda rápida por api_key
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

-- Tabla de conversaciones (historial de mensajes)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'agent')),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para búsqueda y ordenamiento eficiente
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
