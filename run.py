import click

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Administrator

app = create_app()


@app.cli.command("create-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--employee-id", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(name, email, employee_id, password):
    """Create an administrator without hardcoding credentials."""
    if Administrator.query.filter(
        (Administrator.email == email.lower()) | (Administrator.employee_id == employee_id.upper())
    ).first():
        raise click.ClickException("An administrator with that email or employee ID already exists.")
    admin = Administrator(name=name.strip(), email=email.lower(), employee_id=employee_id.upper())
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Administrator {admin.employee_id} created.")


if __name__ == "__main__":
    app.run(debug=True)

