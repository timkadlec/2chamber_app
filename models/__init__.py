from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .core import *
from .library import *
from .auth import Role, RolePermission, Permission, User, PasskeyCredential
from .ensembles import *
from .students import *
from .teachers import *
from .oracle import *
from .players import *
