from django.db import connections


def query_cursor(query_string, *query_args, database='default', cursor=None, **query_kwargs):
    """
    Reusable logic that determines which cursor to use, and executes a query
    by providing either the query_kwargs or query_args (depending on which
    was used). Returns the unmodified cursor.
    """
    if not cursor:
        cursor = connections[database].cursor()
    if query_kwargs:
        cursor.execute(query_string, query_kwargs)
    else:
        cursor.execute(query_string, query_args)
    return cursor


def query(*args, **kwargs):
    """
    Runs a query and returns the results.
    Accepts the same arguments as query_cursor().
    """
    return query_cursor(*args, **kwargs).fetchall()


def query_value(*args, **kwargs):
    """
    Returns the first value from the first row. This is helpful when calling
    functions that return one value.
    Accepts the same arguments as query_cursor().
    """
    return query(*args, **kwargs)[0][0]


def query_to_dicts(*args, **kwargs):
    """
    Runs a query and returns the results as a bunch of dictionaries with
    keys for the column values selected.
    """
    cursor = query_cursor(*args, **kwargs)
    col_names = [desc[0] for desc in cursor.description]
    return [dict(zip(col_names, r)) for r in cursor.fetchall()]


def yield_query_to_dicts(query_string, *query_args, database='default', cursor=None, **query_kwargs):
    """
    Runs a query and produces a generator that returns the results as a
    bunch of dictionaries with keys for the column values selected.
    """
    cursor = query_cursor(*args, **kwargs)
    col_names = [desc[0] for desc in cursor.description]
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        row_dict = dict(zip(col_names, row))
        yield row_dict
    return
