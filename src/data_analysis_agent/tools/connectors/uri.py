"""Dataset URI value object.

Parses a dataset URI and, crucially, exposes a ``display()`` that strips credentials. EVERY log
line, stored ``connection_error``, template field, and surfaced exception must use ``display()`` —
the raw URI (with any password) is read only at connect time inside a connector.

Forms:
- internal: ``parquet:///{name}`` (scheme ``parquet``, empty authority, path = URL-encoded name)
- external: ``{type}://{user}:{pass}@{host}:{port}/{db}`` (e.g. ``postgresql://u:p@h:5432/sales``)
"""
from __future__ import annotations

from urllib.parse import unquote, urlsplit


class DatasetURI:
    """Credential-aware parse of a dataset URI; ``display()`` never reveals the password."""

    def __init__(self, raw: str) -> None:
        self._raw = raw or ""
        self._parts = urlsplit(self._raw)

    @property
    def scheme(self) -> str:
        return self._parts.scheme

    @property
    def host(self) -> str | None:
        return self._parts.hostname

    @property
    def port(self) -> int | None:
        return self._parts.port

    @property
    def username(self) -> str | None:
        return self._parts.username

    @property
    def has_password(self) -> bool:
        return self._parts.password is not None

    @property
    def is_internal(self) -> bool:
        """True for the internal ``parquet`` scheme (no host, no credentials)."""
        return self._parts.scheme == "parquet"

    @property
    def database(self) -> str:
        """The database / logical name (URL-decoded path segment)."""
        return unquote(self._parts.path.lstrip("/"))

    def raw(self) -> str:
        """The raw URI INCLUDING any credentials — use only inside a connector at connect time."""
        return self._raw

    def display(self) -> str:
        """A credential-free rendering safe for logs, templates, errors, and storage."""
        parts = self._parts
        if not parts.hostname and not parts.username:  # internal parquet:///name
            return f"{parts.scheme}:///{parts.path.lstrip('/')}"
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.scheme}://{host}{port}{parts.path}"

    def __str__(self) -> str:  # never leak credentials via str()
        return self.display()
