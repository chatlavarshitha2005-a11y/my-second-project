import os
from flask import Flask, jsonify, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config
from models.database import Base, Employee
from routes import api_bp, pages_bp
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger("ResQAI")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Database engine and scoped session
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        connect_args={"check_same_thread": False} if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"] else {}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    app.db_session = scoped_session(session_factory)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        app.db_session.remove()

    # Auto-seed database if empty
    with app.app_context():
        session = app.db_session()
        try:
            if session.query(Employee).count() == 0:
                logger.info("Initializing and seeding database with sample emergency data...")
                from seed import seed_database
                seed_database(app.config["SQLALCHEMY_DATABASE_URI"])
        except Exception as e:
            logger.error(f"Error checking/seeding database: {e}")
        finally:
            session.close()

    # Template filters
    @app.template_filter("priority_badge")
    def priority_badge(priority):
        p = Config.PRIORITIES.get(priority, Config.PRIORITIES["HIGH"])
        return f'<span class="badge" style="background-color: {p["color"]}; color: #fff;">{p["name"]}</span>'

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(pages_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if "/api/" in str(e):
            return jsonify({"success": False, "error": "Endpoint not found"}), 404
        return render_template("base.html", error_title="404 - Not Found", error_message="The requested page was not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal Server Error: {e}")
        if "/api/" in str(e):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return render_template("base.html", error_title="500 - Server Error", error_message="An internal error occurred. Our engineers have been alerted."), 500

    @app.cli.command("seed-db")
    def seed_db_command():
        """Seeds sample employees, alerts, and cases."""
        from seed import seed_database
        seed_database(app.config["SQLALCHEMY_DATABASE_URI"])
        print("Database seeded successfully.")

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"============================================================")
    print(f" ResQAI — AI-Powered Emergency Alert & Response System")
    print(f" Citizen Safety Portal:        http://127.0.0.1:{port}/citizen")
    print(f" Call-Center Operations Room: http://127.0.0.1:{port}/dashboard")
    print(f" Groq AI Integration:         {'ONLINE' if Config.GROQ_API_KEY else 'LOCAL FALLBACK'}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=True)
