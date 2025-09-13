import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env file
load_dotenv(os.path.join(basedir, '.env'))


def construct_oracle_db_uri(user, password, host, port, service_name):
    return f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service_name}"


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ORACLE_URL = construct_oracle_db_uri(
        user=os.environ.get('ORACLE_DB_USER'),
        password=os.environ.get('ORACLE_DB_PSWD'),
        host=os.environ.get('ORACLE_DB_HOST'),
        port=os.environ.get('ORACLE_DB_PORT'),
        service_name=os.environ.get('ORACLE_DB_SERVICE_NAME')
    )
    SQLALCHEMY_BINDS = {}
    if ORACLE_URL:
        SQLALCHEMY_BINDS["oracle"] = ORACLE_URL


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    DEBUG = True


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    DEBUG = False
