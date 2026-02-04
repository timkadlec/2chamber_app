from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_migrate import Migrate
import boto3

oauth = OAuth()
login_manager = LoginManager()
migrate = Migrate()

def init_s3(app):
    app.extensions["s3"] = boto3.client(
        "s3",
        endpoint_url=app.config["S3_ENDPOINT_URL"],
        aws_access_key_id=app.config["S3_ACCESS_KEY"],
        aws_secret_access_key=app.config["S3_SECRET_KEY"],
        region_name=app.config.get("S3_REGION", "us-east-1"),
    )

def get_s3():
    from flask import current_app
    s3 = current_app.extensions.get("s3")
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Did you call init_s3(app)?")
    return s3

