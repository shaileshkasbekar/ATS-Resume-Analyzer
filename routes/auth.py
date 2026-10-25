import re

from flask import Blueprint, render_template, request, session, redirect, flash
from models.database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

from security import rate_limit

auth = Blueprint("auth", __name__)


MIN_PASSWORD_LENGTH = 8

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


@auth.route("/register", methods=["GET", "POST"])
@rate_limit("register", 5, 600, "/register")
def register():

    if request.method == "POST":

        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Validate input

        if not 2 <= len(fullname) <= 100:
            flash("Please enter your full name.", "danger")
            return redirect("/register")

        if not EMAIL_PATTERN.match(email) or len(email) > 100:
            flash("Please enter a valid email address.", "danger")
            return redirect("/register")

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return redirect("/register")

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO users(full_name, email, password)
        VALUES(%s, %s, %s)
        """

        values = (fullname, email, hashed_password)

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.IntegrityError:

            flash("An account with this email already exists.", "danger")
            return redirect("/register")

        finally:

            cursor.close()
            connection.close()

        flash("Registration Successful! Please Login.", "success")
        return redirect("/login")

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
@rate_limit("login", 10, 300, "/login")
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT * FROM users
        WHERE email = %s
        """

        values = (email,)

        cursor.execute(query, values)

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        # Check if user exists and password matches
        if user and check_password_hash(user["password"], password):

            # New session on login (prevents session fixation)
            session.clear()
            session.permanent = True

            session["user_id"] = user["user_id"]
            session["fullname"] = user["full_name"]

            flash("Login Successful!", "success")
            return redirect("/dashboard")

        else:
            flash("Invalid Email or Password!", "danger")
            return redirect("/login")

    return render_template("login.html")


@auth.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully.", "success")
    return redirect("/login")
