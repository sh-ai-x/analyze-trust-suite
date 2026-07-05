"""Row counter restricted to a fixed set of tables."""

_ALLOWED_TABLES = {"accounts", "ledger"}


def count_rows(cursor, table):
    if table not in _ALLOWED_TABLES:
        raise ValueError("unknown table")
    cursor.execute("SELECT COUNT(*) FROM %s" % table)
    return cursor.fetchone()[0]
