from ..extensions import db
from ..models import AuditLog


def write_audit(action, performed_by):
    db.session.add(AuditLog(action=action, performed_by=performed_by))

