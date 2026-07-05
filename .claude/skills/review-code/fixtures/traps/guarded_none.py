"""Name lookup with an explicit missing-row guard."""


def get_name(cursor, user_id):
    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]
