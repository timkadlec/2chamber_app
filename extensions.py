from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_migrate import Migrate

oauth = OAuth()
login_manager = LoginManager()
migrate = Migrate()