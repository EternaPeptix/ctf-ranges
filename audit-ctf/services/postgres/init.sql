-- A plausible little application schema so the box looks real.
CREATE TABLE IF NOT EXISTS customers (
    id    serial PRIMARY KEY,
    name  text,
    email text,
    tier  text
);
INSERT INTO customers (name, email, tier) VALUES
    ('Ada Lovelace',   'ada@example.com',   'gold'),
    ('Alan Turing',    'alan@example.com',  'silver'),
    ('Grace Hopper',   'grace@example.com', 'gold');

-- Audit note (organizer joke): the 'postgres' superuser password is 'postgres'.
COMMENT ON DATABASE postgres IS 'prod replica — rotate creds (ticket OPS-4412)';
