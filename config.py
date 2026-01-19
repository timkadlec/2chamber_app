import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env file
load_dotenv(".env")


def _enc(x):
    return quote_plus(str(x)) if x is not None else None

def construct_oracle_db_uri(user, password, host, port, service_name):
    if not all([user, password, host, port, service_name]):
        return None
    return f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service_name}"

def construct_sqlite_db_uri(db_file):
    return f"sqlite:///{db_file}"

def construct_mysql_db_uri(user, password, host, port, db_name):
    if not all([user, password, host, port, db_name]):
        return None
    return f"mysql+pymysql://{_enc(user)}:{_enc(password)}@{host}:{port}/{db_name}"

def construct_postgres_db_uri(user, password, host, port, db_name):
    if not all([user, password, host, port, db_name]):
        return None
    return f"postgresql+psycopg://{_enc(user)}:{_enc(password)}@{host}:{port}/{db_name}"


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
    OAUTH_TENANT_ID = os.environ.get("OAUTH_TENANT_ID")
    if ORACLE_URL:
        SQLALCHEMY_BINDS["oracle"] = ORACLE_URL

    SQLALCHEMY_DATABASE_URI = construct_postgres_db_uri(
        user=os.environ.get('POSTGRES_DB_USER'),
        password=os.environ.get('POSTGRES_DB_PSWD'),
        host=os.environ.get('POSTGRES_DB_HOST'),
        port=os.environ.get('POSTGRES_DB_PORT'),
        db_name=os.environ.get('POSTGRES_DB_NAME')
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
