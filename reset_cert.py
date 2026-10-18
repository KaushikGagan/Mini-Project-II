from run import app
with app.app_context():
    from backend.app.extensions import db
    rows = db.session.execute(db.text(
        'SELECT c.certificate_id, c.pdf_path, c.document_id, a.reference_number, a.application_id, a.status '
        'FROM certificates c JOIN applications a ON a.application_id=c.application_id'
    )).fetchall()
    print('CERTS:', rows)
    docs = db.session.execute(db.text(
        'SELECT document_id, application_id, stored_path, mime_type FROM application_documents'
    )).fetchall()
    print('DOCS:', docs)

    if rows:
        for cert_id, pdf_path, doc_id, ref, app_id, status in rows:
            # Reset certificate so it can be regenerated with merge
            db.session.execute(db.text('DELETE FROM certificates WHERE certificate_id=:id'), {'id': cert_id})
            db.session.execute(db.text("UPDATE applications SET status='Approved' WHERE application_id=:id"), {'id': app_id})
        db.session.commit()
        print('DONE: certificates deleted, applications reset to Approved. Re-issue from admin panel.')
    else:
        print('No certificates found.')
