"""Account balance lookup."""


def get_balance(cursor, user_id):
    cursor.execute("SELECT balance FROM accounts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0]
