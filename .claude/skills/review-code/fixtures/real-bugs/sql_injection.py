"""User lookup by name."""


def find_user(cursor, name):
    cursor.execute("SELECT id FROM users WHERE name = '%s'" % name)
    return cursor.fetchone()
