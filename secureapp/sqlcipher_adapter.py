"""
SQLCipher support for pyDAL.

pyDAL ships an SQLite adapter but no SQLCipher dialect, so this module
registers both:

1. the ``sqlcipher3`` driver (a Python binding for the SQLCipher-enabled
   SQLite amalgamation, https://pypi.org/project/sqlcipher3/) into pyDAL's
   driver table,
2. a ``SQLCipher`` adapter for URIs of the form

       sqlcipher://<filename>

   Additional options:
   * ``folder=...``          - passed to DAL() as usual (db files live here)
   * ``adapter_args={"key": <passphrase>}``  - the encryption key
   * ``adapter_args={"engine_plagmams": [...], ...}`` optional pragmas

The key is applied with ``PRAGMA key`` on every new connection, and a
``SELECT`` against ``sqlite_master`` is executed immediately to verify the
key: with a wrong key SQLCipher raises ``DatabaseError: ... hmac check
failed`` the moment any page is decrypted, so this gives an early and
clear failure instead of confusing errors later.
"""

from os.path import join as pjoin

# Attach the driver to pydal. Must be imported before DAL() is created.
try:
    import sqlcipher3.dbapi2 as _sqlcipher_driver
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "The 'sqlcipher3' package is required for SQLCipher support. "
        "Install it with:  pip install sqlcipher3"
    ) from exc

#from pydal.adapters import adapters
from pydal.backend_base import adapters
#from pydal.adapters.sqlite import SQLite
from pydal.backend_base import SQLAdapter

register_sqlcipher = adapters.register_for("sqlcipher")


@register_sqlcipher
class SQLCipher(SQLAdapter):
    """Adapter for sqlcipher:// URIs, reusing pyDAL's SQLite internals."""

    dbengine = "sqlcipher"
    drivers = ("sqlcipher3",)

    def _initialize_(self):
        self.pool_size = 0
        super(SQLCipher, self)._initialize_()
        self.dbpath = self.uri.split("://", 1)[1]
        if self.dbpath[0] != "/":
            self.dbpath = pjoin(self.folder, self.dbpath)

    def connector(self):
        # sqlite.Connection subclass is ABI-compatible with sqlite3, and
        # accepts the same kwargs (check_same_thread, detect_types, ...)
        return self.driver.connect(self.dbpath, **self.driver_args)

    def after_connection(self):
        key = self.adapter_args.get("key")
        if not key:
            raise RuntimeError(
                "SQLCipher adapter requires an encryption key "
                "(pass adapter_args={'key': ...} to DAL)"
            )
        if not isinstance(key, str):
            raise RuntimeError("SQLCipher key must be a str")

        # PRAGMA key MUST be the first statement executed on the connection
        self.execute("PRAGMA key = %s;" % "'%s'" % key.replace("'", "''"))

        # probe:decrypting page 1 fails loudly when the key is wrong
        try:
            self.execute("SELECT count(*) FROM sqlite_master;")
        except Exception as exc:
            raise RuntimeError(
                "SQLCipher: cannot decrypt the database with the provided key "
                "(wrong key, non-SQLCipher file, or corruption): %s" % exc
            ) from exc

        # optional extra pragmas (e.g. cipher_page_size, kdf_iter, ...)
        for pragma in self.adapter_args.get("pragmas", ()):
            self.execute("PRAGMA %s;" % pragma)

        super(SQLCipher, self).after_connection()
