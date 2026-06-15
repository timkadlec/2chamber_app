from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

oauth = OAuth()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()