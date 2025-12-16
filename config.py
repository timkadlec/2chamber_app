import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env file
load_dotenv("/etc/skh/.env")

def construct_oracle_db_uri(user, password, host, port, service_name):
    if not all([user, password, host, port, service_name]):
        return None
    return f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service_name}"



def construct_sqlite_db_uri(db_file):
    return f"sqlite:///{db_file}"


def construct_mysql_db_uri(user, password, host, port, db_name):
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"


def construct_postgres_db_uri(user, password, host, port, db_name):
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


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
    SQLALCHEMY_DATABASE_URI = construct_postgres_db_uri(
        user=os.environ.get('POSTGRES_DB_USER'),
        password=os.environ.get('POSTGRES_DB_PSWD'),
        host=os.environ.get('POSTGRES_DB_HOST'),
        port=os.environ.get('POSTGRES_DB_PORT'),
        db_name=os.environ.get('POSTGRES_DB_NAME')
    )
    DEBUG = True


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = construct_postgres_db_uri(
        user=os.environ.get('POSTGRES_DB_USER'),
        password=os.environ.get('POSTGRES_DB_PSWD'),
        host=os.environ.get('POSTGRES_DB_HOST'),
        port=os.environ.get('POSTGRES_DB_PORT'),
        db_name=os.environ.get('POSTGRES_DB_NAME')
    )
    DEBUG = False
