import json

import asyncpg

__all__ = ("init_db",)


async def init_connection(connection):
    """Initialize an :class:`asyncpg.connection.Connection` with
    custom type encoding and decoding for ``JSONB`` columns.

    Parameters
    ----------
    connection: asyncpg.connection.Connection
        The connection to initalize.
    """
    await connection.set_type_codec(
        "jsonb",
        schema="pg_catalog",
        encoder=json.dumps,
        decoder=json.loads,
        format="text",
    )


async def init_db(user, password, host, port, database):
    """Initialize an :class:`asyncpg.pool.Pool` with the given credentials.

    Every connection created using the returned pool uses custom encoders
    and decoders for ``JSONB`` columns, returning and accepting dictionaries
    and lists respectively.

    Parameters
    ----------
    user: str
        The user to connect to the database with.
    password: str
        The password of the database user.
    host: str
        The host to connect to.
    port: str
        The port to connect to.
    database: str
        The database to connect to.

    Returns
    -------
    asyncpg.pool.Pool
        The connection pool.
    """
    uri = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return await asyncpg.create_pool(uri, init=init_connection)
