from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
import re
import requests

app = Flask(__name__)
app.secret_key = "rjdk8741tao"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "Deva"
app.config["MYSQL_PASSWORD"] = "rjdk8741tao"
app.config["MYSQL_DB"] = "mut_funds"
mysql = MySQL(app)


def strong_pass(Password):
    if len(Password) < 8:
        return False
    if (
        not re.search(r"[a-z]", Password)
        or not re.search(r"[A-Z]", Password)
        or not re.search(r"\d", Password)
    ):
        return False
    else:
        return True


class user:
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


class signup(FlaskForm):
    username = StringField(
        "username", validators=[InputRequired(), Length(min=4, max=25)]
    )
    password = PasswordField("password", validators=[InputRequired()])
    submit = SubmitField("signup")


class login(FlaskForm):
    username = StringField(
        "username", validators=[InputRequired(), Length(min=4, max=25)]
    )
    password = PasswordField("password", validators=[InputRequired()])
    submit = SubmitField("login")


@app.route("/")
def home():
    return render_template("form.html")


def is_logged_in():
    return session.get("user_id")


@app.route("/signup", methods=["GET", "POST"])
def signin():
    form = signup()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if not strong_pass(password):
            flash(
                "Note:<br> Password must be at least 8 characters long <br> Must contain an upper case, lowercase and a number :(",
                "danger",
            )
            return redirect(url_for("signin"))
        hashed_pass = generate_password_hash(password)
        cur = mysql.connection.cursor()
        cur.execute("select id from users where username=%s", (username,))
        old_user = cur.fetchone()
        if old_user:
            cur.close()
            flash("Username already taken, Please try different one.", "danger")
            return render_template("signup.html", form=form)
        cur.execute(
            "insert into users (username,password) values (%s,%s)",
            (username, hashed_pass),
        )
        mysql.connection.commit()
        cur.close()
        flash("SignUp SUCCESSFUL", "success")
        return redirect(url_for("login_user"))
    return render_template("signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login_user():
    form = login()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        cur = mysql.connection.cursor()
        cur.execute(
            "select id, username, password from users where username=%s", (username,)
        )
        userdata = cur.fetchone()
        cur.close()
        if userdata:
            real_pass = userdata[2]
            if check_password_hash(real_pass, password):
                current_user = user(
                    id=userdata[0], username=userdata[1], password=userdata[2]
                )
                session["user_id"] = current_user.id
                flash("Login Successful", "success")
                return redirect(url_for("getfund"))
            else:
                flash("Invalid Credentials", "danger")
                return render_template("login.html", form=form)
        else:
            flash("User not found!")
            return render_template("login.html", form=form)
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logging Out", "success")
    return redirect(url_for("signin"))


url = "https://api.mfapi.in/mf/"


@app.route("/getfund", methods=["GET", "POST"])
def getfund():
    if not is_logged_in():
        return redirect(url_for("login_user"))

    if request.method == "POST":
        code = request.form.get("code")
        amount = request.form.get("amount")
        units = request.form.get("units")
        userid = session.get("user_id")
        cur = mysql.connection.cursor()
        cur.execute("select username from users where id=%s", (userid,))
        userdata = cur.fetchone()
        cur.close()
        if userdata:
            username = userdata[0]
            cur = mysql.connection.cursor()
            cur.execute(
                "insert into fund (username,code,amount,units) values (%s,%s,%s,%s)",
                (username, code, amount, units),
            )
            mysql.connection.commit()
            cur.close()
            flash("Fund data added successfully", "success")
        else:
            flash("User data not found!", "danger")
        return redirect(url_for("display"))
    return render_template("fund.html")


@app.route("/display", methods=["GET", "POST"])
def display():
    if not is_logged_in():
        return redirect(url_for("login_user"))
    list_details = []
    userid = session.get("user_id")
    cur = mysql.connection.cursor()
    cur.execute("select username from users where id=%s", (userid,))
    userdata = cur.fetchone()
    cur.close()
    if userdata:
        username = userdata[0]
        cur = mysql.connection.cursor()
        cur.execute("select * from fund where username=%s", (username,))
        details = cur.fetchall()
        cur.close()
        if details:
            for detail in details:
                username = detail[0]
                code = str(detail[1])
                amount = detail[2]
                units = detail[3]
                id = detail[4]
                new_url = url + code
                data_fund = requests.get(new_url)
                f_h = data_fund.json().get("meta")["fund_house"]
                nav = float(data_fund.json().get("data")[0].get("nav"))
                c_val = nav * units
                growth = c_val - float(amount)
                final = {
                    "name": username,
                    "fund_house": f_h,
                    "inv_amount": amount,
                    "units": units,
                    "nav": nav,
                    "cur_value": c_val,
                    "growth": growth,
                    "id": id,
                }
                list_details.append(final)
        return render_template("display.html", details=list_details)
    return render_template("display.html", details=list_details)


@app.route("/delete/<id>", methods=["POST"])
def delete(id):
    if request.method == "POST":
        if is_logged_in():
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM fund WHERE id = %s", (id,))
            mysql.connection.commit()
            cur.close()
            flash("Record deleted successfully", "success")
    return redirect(url_for("display"))

#
# @app.route("/edit/<id>", methods=["GET", "POST"])
# def edit(id):
#     if request.method == "POST":
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT * FROM fund WHERE id = %s", (id,))
#         data = cur.fetchone()
#         cur.close()
#         code = request.form.get("code")
#         amount = request.form.get("amount")
#         units = request.form.get("units")
#         cur = mysql.connection.cursor()
#         cur.execute(
#             "UPDATE fund SET code =%s,amount=%s,units=%s WHERE id = %s",
#             (code, amount, units, id),
#         )
#         mysql.connection.commit()
#         cur.close()
#         return render_template("edit.html", data=data)
#     return redirect(url_for("display"))


# @app.route("/edit/<id>", methods=["GET", "POST"])
# def edit(id):
#     if request.method == "POST":
#         code = request.form.get("code")
#         amount = request.form.get("amount")
#         units = request.form.get("units")
#         cur = mysql.connection.cursor()
#         if (code, amount, units) != None:
#             cur.execute(
#                 "UPDATE fund SET code =%s,amount=%s,units=%s WHERE id = %s",
#                 (code, amount, units, id),
#             )
#             mysql.connection.commit()
#             cur.close()
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT * FROM fund WHERE id = %s", (id,))
#         data = cur.fetchone()
#         cur.close()
#         return render_template("edit.html", data=data)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if request.method == "POST":
        code = request.form.get("code")
        amount = request.form.get("amount")
        units = request.form.get("units")
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE fund SET code =%s,amount=%s,units=%s WHERE id = %s",
            (code, amount, units, id),
        )
        mysql.connection.commit()

        flash("User updated", "success")
        return redirect(url_for("display"))
    cur = mysql.connection.cursor()
    cur.execute("select * from fund where id=%s", (id,))
    data = cur.fetchone()
    return render_template("edit.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
