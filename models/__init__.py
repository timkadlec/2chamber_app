from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .core import *
from .library import *
from .auth import *
from .ensembles import *
from .students import *
from .teachers import *
from .oracle import *
