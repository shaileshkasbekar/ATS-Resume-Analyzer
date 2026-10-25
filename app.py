import os

from flask import Flask, redirect, flash, request, render_template, session

from config import Config
from security import init_security

from routes.auth import auth
from routes.upload import upload
from routes.dashboard import dashboard
from routes.history import history
from routes.general_analyzer import general_analyzer
from routes.job_match import job_match
from routes.assistant import assistant
from routes.reports import reports
from routes.versions import versions
from routes.jobs import jobs
from routes.career import career
from routes.workspace import workspace


app = Flask(__name__)

app.config.from_object(Config)

if not app.config["SECRET_KEY"]:
    raise ValueError("SECRET_KEY not found in .env")

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

init_security(app)

for blueprint in (auth, upload, dashboard, history, general_analyzer, job_match,
                  assistant, reports, versions, jobs, career, workspace):
    app.register_blueprint(blueprint)


@app.route("/")
def home():
    return redirect("/dashboard" if "user_id" in session else "/login")


# =========================================
# Error pages
# =========================================

@app.errorhandler(413)
def file_too_large(error):
    flash("File is too large. Maximum size is 5 MB.", "danger")
    return redirect(request.path)


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message="The request was invalid or your session expired. Please go back and try again."), 400


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="This page does not exist, or you do not have access to it."), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("error.html", code=500, message="Something went wrong on our side. Please try again."), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
