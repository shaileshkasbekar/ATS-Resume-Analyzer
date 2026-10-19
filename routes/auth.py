from flask import Blueprint, render_template, request, session, redirect, flash
from models.database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

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
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

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