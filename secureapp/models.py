"""
This file defines the database models.
Everything below is stored inside the SQLCipher-encrypted database file.
"""

from pydal.validators import *

from py4web.core import utcnow

from .common import Field, db

# A tiny demo table only meaningful to a logged-in user
db.define_table(
    "secure_note",
    Field("user_id", "reference auth_user", readable=False, writable=False),
    Field("body", "text", requires=IS_NOT_EMPTY(), label="Secure note"),
    Field("created_on", "datetime", readable=False, writable=False, default=utcnow),
)

db.commit()
