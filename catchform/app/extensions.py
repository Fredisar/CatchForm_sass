"""Extensions Flask instanciées une seule fois et initialisées via l'app factory."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Connecte-toi pour accéder à ton tableau de bord."
login_manager.login_message_category = "error"
