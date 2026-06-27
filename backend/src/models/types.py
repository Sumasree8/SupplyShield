"""
Dialect-portable column types.

The application targets PostgreSQL in production (native UUID + JSONB), but the
test suite and lightweight local runs use SQLite. These types render the optimal
native type per dialect while accepting both ``str`` and ``uuid.UUID`` inputs:

  - ``GUID``        -> PostgreSQL ``UUID``,  others ``CHAR(32)``
  - ``JSONColumn()`` -> PostgreSQL ``JSONB``, others generic ``JSON``

Using these instead of importing from ``sqlalchemy.dialects.postgresql`` keeps
the ORM models importable and creatable under both databases, and tolerant of
the string IDs that arrive from URL path parameters.
"""
import uuid

from sqlalchemy import JSON, CHAR
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Stores as PostgreSQL ``UUID`` natively, and as ``CHAR(32)`` (hex, no dashes)
    elsewhere. Accepts ``uuid.UUID`` or ``str`` on bind and always returns a
    ``uuid.UUID`` on load.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


def JSONColumn():
    """JSON column type — JSONB on PostgreSQL, generic JSON elsewhere."""
    return JSON().with_variant(JSONB(), "postgresql")
