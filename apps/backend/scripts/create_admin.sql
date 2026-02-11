-- ============================================
-- SCRIPT SQL PER CREARE ADMIN E LICENZA
-- ============================================
-- Esegui questo script con psql:
--   psql -U postgres -d trading_db -f create_admin.sql
--
-- Oppure connettiti e incolla i comandi:
--   psql postgresql://postgres:postgres@localhost:5432/trading_db
-- ============================================

-- 1. GENERA UNA PASSWORD HASH BCRYPT
-- IMPORTANTE: Devi generare l'hash della password prima!
-- Puoi farlo con Python:
--   python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('TuaPassword123'))"
--
-- Esempio di hash per la password "Admin123!" (NON usare in produzione!):
-- $2b$12$LQv3c1yqBwEHxYxv2.mqlu7gJgZ7RLOp7pZ3w5b0hFLg5Gh4YAJUa

-- 2. CREA L'UTENTE ADMIN
-- Sostituisci i valori con quelli desiderati
INSERT INTO users (
    email,
    username,
    hashed_password,
    full_name,
    is_active,
    is_verified,
    is_superuser,
    created_at,
    updated_at
) VALUES (
    'admin@example.com',                                              -- Cambia con la tua email
    'admin',                                                           -- Cambia con il tuo username
    '$2b$12$LQv3c1yqBwEHxYxv2.mqlu7gJgZ7RLOp7pZ3w5b0hFLg5Gh4YAJUa',  -- Hash della password
    'Admin User',                                                      -- Nome completo
    true,                                                              -- is_active
    true,                                                              -- is_verified
    true,                                                              -- is_superuser
    NOW(),
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    is_superuser = true,
    is_verified = true,
    is_active = true,
    updated_at = NOW()
RETURNING id, email, username, is_superuser;

-- 3. CREA UNA LICENZA INIZIALE
-- Il codice licenza viene generato manualmente
-- Formato: ADMIN-XXXX-XXXX-XXXX-XXXX
INSERT INTO licenses (
    key,
    name,
    description,
    status,
    is_active,
    max_uses,
    current_uses,
    expires_at,
    created_by,
    created_at,
    updated_at
) VALUES (
    'ADMIN-TEST-0001-2024-INIT',  -- Chiave licenza (cambiala!)
    'Admin License',
    'Licenza iniziale creata tramite setup',
    'active',
    true,
    10,                            -- Max 10 utilizzi
    0,                             -- Nessun utilizzo ancora
    NOW() + INTERVAL '365 days',   -- Scade tra 1 anno
    1,                             -- created_by admin (id=1)
    NOW(),
    NOW()
)
ON CONFLICT (key) DO NOTHING
RETURNING id, key, name, max_uses, expires_at;

-- 4. VERIFICA
SELECT '=== ADMIN CREATI ===' as info;
SELECT id, email, username, is_superuser, is_verified, is_active
FROM users
WHERE is_superuser = true;

SELECT '=== LICENZE DISPONIBILI ===' as info;
SELECT id, key, name, status, current_uses, max_uses, expires_at
FROM licenses
WHERE status = 'active' AND is_active = true;

-- ============================================
-- COMANDI UTILI
-- ============================================

-- Promuovere un utente esistente ad admin:
-- UPDATE users SET is_superuser = true, is_verified = true WHERE email = 'utente@example.com';

-- Revocare privilegi admin:
-- UPDATE users SET is_superuser = false WHERE email = 'utente@example.com';

-- Creare una nuova licenza:
-- INSERT INTO licenses (key, name, status, is_active, max_uses, current_uses, expires_at, created_at, updated_at)
-- VALUES ('LIC-XXXX-XXXX-XXXX-XXXX', 'Pro License', 'active', true, 1, 0, NOW() + INTERVAL '30 days', NOW(), NOW());

-- Vedere tutti gli utenti e le loro licenze:
-- SELECT u.email, u.username, u.is_superuser, l.key as license_key, l.status
-- FROM users u
-- LEFT JOIN licenses l ON u.license_id = l.id;
