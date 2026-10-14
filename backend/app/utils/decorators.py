from functools import wraps

from flask import flash, redirect, session, url_for


def citizen_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "citizen_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.citizen_login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            flash("Administrator sign-in is required.", "error")
            return redirect(url_for("auth.admin_login"))
        return view(*args, **kwargs)
    return wrapped

