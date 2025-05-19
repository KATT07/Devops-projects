"""
Tables view in DB

User : username password uid
Message : timestamp sentuid recieveduid

Grafana server
Total Messages sent - mysql - timestamp + data
Total Users Registered - mysql - timestamp + data
Pi chart users sending most messages - py script running every time updating number - mysql
Pi chart users recieving most messages - py script running every time updating number - mysql
format for this
username - message count

Things to take input for registering
+ name
+ dob
+ username
+ email
+ phoneno
+ password(2x confirm password)
+ address (integrate Google Maps for pinpoint location)
"""

import time
import hashlib
import mysql.connector
from flask import Flask, render_template, request, make_response

app = Flask(__name__)

mydb = mysql.connector.connect(
    host="localhost",
    user="xxx",
    password="xxx",
    database='xxx'
)

mycursor = mydb.cursor()


@app.route("/delete.html")
def delete():
    q = "select username,password from users;"
    mycursor.execute(q)
    result = mycursor.fetchall()
    for i in result:
        if request.cookies.get('username') == i[0] and request.cookies.get('password') == i[1]:
            q = "delete from users where username=%s;"
            vals = (request.cookies.get('username'),)
            mycursor.execute(q, vals)
            q = "delete from messages where sender=%s OR reciever=%s"
            vals = (request.cookies.get('username'), request.cookies.get('username'))
            mycursor.execute(q, vals)
            mydb.commit()
            return "Delete Complete"
    return "Unauthorized access"


@app.route("/details.html")
def details():
    q = "select * from users;"
    mycursor.execute(q)
    result = mycursor.fetchall()
    for i in result:
        if request.cookies.get('username') == i[0] and request.cookies.get('password') == i[5]:
            site = '''<html>
            <h1><ul>'''
            for j in i:
                site += "<li>" + j + "</li>" + "\n"
            site += '''<button onclick="window.location.href='/delete.html'">Delete Account</button></ul></h1>
            </html>'''
            return site
    return "Unauthorized access"


@app.route("/home.html")
def home():
    q = "select username,password from users;"
    mycursor.execute(q)
    result = mycursor.fetchall()
    for i in result:
        if request.cookies.get('username') == i[0] and request.cookies.get('password') == i[1]:
            return render_template('home.html')
    return "Unauthorized access"


@app.route("/received.html")
def recieve():
    q = "select username,password from users;"
    mycursor.execute(q)
    result = mycursor.fetchall()
    for i in result:
        if request.cookies.get('username') == i[0] and request.cookies.get('password') == i[1]:
            site = '''<html>
            <h2><ul>
            '''
            q = "select * from messages where reciever = %s order by timestamp desc;"
            vals = (request.cookies.get('username'),)
            mycursor.execute(q, vals)
            result = mycursor.fetchall()
            for i in result:
                site += "<li>" + str(i[1]) + ":  " + str(i[3]) + "  </li>" + "\n"
            site += '''</ul></h2>
            </html>'''
            return site
    return "Unauthorized access"


@app.route("/send.html", methods=['GET', 'POST'])
def send():
    q = "select username,password from users;"
    mycursor.execute(q)
    result = mycursor.fetchall()
    for i in result:
        if request.cookies.get('username') == i[0] and request.cookies.get('password') == i[1]:
            if request.method == "POST":
                q = "insert into messages values(%s,%s,%s,%s);"
                message = request.form.get('message')
                username = request.form.get('username')
                vals = (str(time.time()), request.cookies.get('username'), username, message)
                mycursor.execute(q, vals)
                mydb.commit()
                return "Send Successful"
            else:
                return render_template('send.html')
    return "Unauthorized access"


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/login.html", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        q = "select username,password from users;"
        mycursor.execute(q)
        result = mycursor.fetchall()
        for i in range(len(result)):
            if result[i][0].lower().strip() == username.lower().strip() and result[i][1] == hashlib.sha256(
                    password.encode("utf-8")).hexdigest():
                response = make_response(render_template('login_success.html'))
                response.set_cookie("username", username)
                response.set_cookie("password", result[i][1])
                return response
        return "Wrong Credentials"
    else:
        return render_template('login.html')


@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        dob = request.form.get('dob')
        username = request.form.get('username')
        email = request.form.get('email')
        phno = request.form.get('phoneno')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        address = request.form.get('address')
        print(name, " ", dob, " ", username, " ", email, " ", phno, " ", password, "=", confirm_password, " ", address)
        if password != confirm_password:
            return "Password is not Equal to Confirm Password"
        else:
            q = "select username from users;"
            mycursor.execute(q)
            result = mycursor.fetchall()
            for i in result:
                print(i)
                if username == i[0]:
                    return "Username is already registered please login"
            hashed_password = (hashlib.sha256(password.encode("utf-8"))).hexdigest()
            q = "insert into users values(%s,%s,%s,%s,%s,%s,%s);"
            vals = (username, name, dob, email, phno, hashed_password, address)
            print(username, name, dob, email, phno, hashed_password, address)
            mycursor.execute(q, vals)
            mydb.commit()
            return "Account Registered successfully now click login"
    else:
        return render_template('register.html')


if __name__ == '__main__':
    print(mydb)
    app.run(host="0.0.0.0")
