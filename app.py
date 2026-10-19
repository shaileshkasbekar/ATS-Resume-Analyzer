import os

from routes.upload import upload
from flask import Flask, redirect, flash, request
from config import Config
from routes.auth import auth
from routes.dashboard import dashboard
from routes.history import history
from routes.general_analyzer import general_analyzer
from routes.job_match import job_match

app = Flask(__name__)

app.config.from_object(Config)

if not app.config["SECRET_KEY"]:
    raise ValueError("SECRET_KEY not found in .env")

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
app.register_blueprint(auth)
app.register_blueprint(upload)
app.register_blueprint(dashboard)
app.register_blueprint(history)
app.register_blueprint(general_analyzer)
app.register_blueprint(job_match)

@app.route("/")
def home():
    return redirect("/login")


@app.errorhandler(413)
def file_too_large(error):
    flash("File is too large. Maximum size is 5 MB.", "danger")
    return redirect(request.path)

if __name__ == "__main__":
    app.run(debug=True)