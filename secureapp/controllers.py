"""
Controllers.

URLs (with app folder = ./webapp and app name = secureapp):
  /secureapp/index           -> index()  (public home)
  /secureapp/secure          -> secure() (login required, demo of data in SQLCipher)
  /secureapp/auth/register   -> Auth registration form     (exposed by auth.enable())
  /secureapp/auth/login      -> Auth login form
  /secureapp/auth/logout     -> Auth logout
  /secureapp/auth/profile    -> Auth profile editor        (login required)

NOTE: @unauthenticated() / @authenticated() are ActionFactory decorators that
register the route AND attach fixtures AND bind a template of the same name
(views/index.html, views/secure.html). Do NOT mix them with @action/@action.uses.
"""

from py4web.utils.form import Form, FormStyleBootstrap5

from .common import auth, authenticated, db, flash, unauthenticated


@unauthenticated()
def index():
    user = auth.get_user()
    return dict(user=user)


@authenticated()
def secure():
    """Protected page. Everything written here is stored in the
    SQLCipher-encrypted database file on disk."""
    user = auth.get_user()
    # a form for writing notes into the encrypted db (no automatic DB write)
    form = Form(db.secure_note, dbio=False, formstyle=FormStyleBootstrap5)
    if form.accepted:
        db.secure_note.insert(user_id=user["id"], body=form.vars.get("body") or "")
        flash.set("Note stored in the encrypted database", _class="success")
        form = Form(db.secure_note, dbio=False, formstyle=FormStyleBootstrap5)

    notes = db(db.secure_note.user_id == user["id"]).select(
        orderby=~db.secure_note.created_on
    )
    return dict(user=user, form=form, notes=notes)
