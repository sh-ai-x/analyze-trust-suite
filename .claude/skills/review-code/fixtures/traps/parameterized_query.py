"""Ledger memo search using a bound parameter."""


def search_ledger(cursor, keyword):
    cursor.execute("SELECT * FROM ledger WHERE memo LIKE ?", ("%" + keyword + "%",))
    return cursor.fetchall()
