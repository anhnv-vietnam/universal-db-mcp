-- Schema and seed data for the testing SQLite database.
DROP TABLE IF EXISTS test_records;
CREATE TABLE test_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    value INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO test_records (name, category, value, created_at) VALUES
    ('alpha', 'control', 10, '2024-01-01T00:00:00Z'),
    ('beta', 'control', 15, '2024-02-01T00:00:00Z'),
    ('gamma', 'experiment', 22, '2024-03-05T00:00:00Z');
