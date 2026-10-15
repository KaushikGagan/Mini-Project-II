from pathlib import Path

from flask import Flask, render_template

from config import Config
from .extensions import db, mail, migrate


def create_app(config_object=Config):
    config_object.validate()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["GENERATED_CERTIFICATES_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    from .routes.citizen import citizen_bp
    from .routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(_error):
        return render_template("errors/413.html"), 413

    return app

