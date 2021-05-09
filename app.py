from flask import Flask, redirect, url_for, render_template, request, session
from datetime import timedelta
import os
import pathlib
import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
import datetime

app = Flask(__name__)
#app.config = ['SQLALCHEMY_DATABASE_URI'] = "mysql://username:password@server/db"

app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "alpha"
app.config['MYSQL_DB'] = "maindb"

mysql = MySQL(app)
app.secret_key = "IceCream"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID= "770675422913-ljcnbrn1v4iig8o8augpq7hjg5lm4q65.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:8080/authorize"
)


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
        #redirect dashbord html
    else:
        #redirect home html
        return redirect("/home")
@app.route("/home")
def home():

    if "user" in session:
        return redirect(url_for("dashboard"))
        #check if authenticated and redirect dashbord
    return render_template("home.html")


@app.route("/login")
def login():
    # if "user" in session:
    #     return redirect(url_for("dashboard"))
    # else:
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/authorize")
def authorize():
    if "user" in session:
       return redirect(url_for("dashboard"))

    flow.fetch_token(authorization_response=request.url)

    if (not (session["state"] == request.args["state"])):
        return redirect(url_for("dashboard"))

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    session["user"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["image"] = id_info.get("picture")
    session["mail"] = id_info.get("email")
    
    cur=mysql.connection.cursor()
    resultvalue=cur.execute("SELECT * FROM USERS WHERE user_id=%s", (session["user"],))
    if (resultvalue==0):
        print(resultvalue)
        cur.execute("INSERT INTO USERS(user_id,email_id,name) VALUES(%s,%s,%s)", (session["user"],session["mail"],session["name"],))
        mysql.connection.commit()
    cur.close()

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html")
    else:
        return redirect(url_for("home"))


@app.route("/profile", methods = ["POST","GET"])
def profile():
    if "user" in session:
        if request.method == "POST":
            userDetails = request.form
            gender = userDetails['gender']
            dob = userDetails['dob']
            cur=mysql.connection.cursor()
            if(dob!=""):
                cur.execute("UPDATE USERS SET dob=%s WHERE user_id=%s",(dob,session["user"],))
            else :
                cur.execute("UPDATE USERS SET dob=NULL WHERE user_id=%s",(session["user"],))
                
            if(gender!=None):
                cur.execute("UPDATE USERS SET gender=%s WHERE user_id=%s",(gender,session["user"],))
            else :
                cur.execute("UPDATE USERS SET gender=NULL WHERE user_id=%s",(session["user"],))
            mysql.connection.commit()
            cur.close()

        cur=mysql.connection.cursor()
        resultvalue=cur.execute("SELECT * FROM USERS WHERE user_id=%s", (session["user"],))
        
        row = cur.fetchone()
        gender = row[4]
        dob = row[3]
        mysql.connection.commit()
        cur.close()
        name = session["name"]
        mail=session["mail"]
        imageurl=session["image"]
        return render_template("profile.html", name = session["name"],mail=session["mail"],imageurl=session["image"], dob=dob , gender=gender)
    else:
        return redirect(url_for("home"))

@app.route("/booking")
def booking():
    if "user" in session:
        
        cur = mysql.connection.cursor()
        cur.execute("select * from counsellor")
        result = cur.fetchall()
        mysql.connection.commit()
        cur.close()
        return render_template("booking.html",tb = result) 

    else:
        return redirect(url_for("home"))
    


@app.route("/logout")
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect(url_for("index"))
  
@app.route("/slot/<id>")
def slot(id):
    if "user" in session:
        cur = mysql.connection.cursor()
        cur.execute("Select * from appointment where user_id=%s",(session["user"],))
        res=cur.fetchall()
        cur.close()
        if(len(res)>0):
            return render_template("alreadybooked.html")
        
        session["counsellor_id"] = id
        print(session["counsellor_id"])
        cur = mysql.connection.cursor()
        dct = {"Monday":[],"Tuesday":[],"Wednesday":[],"Thursday":[],"Friday":[],"Saturday":[],"Sunday":[]}
        cur.execute("select day_available,time_slot,flag from day_availability where counsellor_id = %s",(id,))
        result = cur.fetchall()
        for row in result:
            dct[row[0]].append([row[1],row[2]==1])
        
        # for row in result:
        #     dct[row].sort()
        print(dct)
        mysql.connection.commit()
        cur.close()
        l=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        # d={
        #     "Monday":[["12",True],["23",False]],
        #     "Tuesday":[["121",False],["34",True]],
        #     "Wednesday":[["12",True],["23",False]],
        #     "Thursday":[["12",True],["23",False]],
        #     "Friday":[["12",True],["23",False]],
        #     "Saturday":[["12",True],["23",False]],
        #     "Sunday":[["12",True],["23",False]]
        # }
        date_lst = []
        day_lst = []
        for i in range(1,8):
            Day_Date = datetime.datetime.today() + datetime.timedelta(days=i)
            date_lst.append(Day_Date.strftime('%Y-%m-%d'))
            day_lst.append(l[Day_Date.weekday()])
        return render_template("slot.html", ls=day_lst, d=dct,date_lst = date_lst, inc=datetime.timedelta(minutes=45))
    else:
        return redirect(url_for("home"))

@app.route("/mysession", methods = ["POST","GET"])
def mysession():
    if "user" in session:
        if request.method == "POST":
            slotDetail = request.form
            print((slotDetail['btnradio']))
            time,date,day = (slotDetail['btnradio']).split('@')
            print(day)
            session["day"] = day
            session["time"]=time
            counsellor_id = session["counsellor_id"]
            session["booked_counsellor"]=counsellor_id
            user_id = session["user"]
            cur = mysql.connection.cursor()
            
            if(counsellor_id=="1"):
                meetlink="https://meet.google.com/atr-jafq-gqt"
            if(counsellor_id=="2"):
                meetlink="https://meet.google.com/ddf-dmbb-kya"
            cur.execute("INSERT INTO APPOINTMENT(Counsellor_Id,User_ID,Start_Time,Date,meet_link) VALUES(%s,%s,%s,%s,%s)",(counsellor_id,user_id,time,date,meetlink,))
            cur.execute("update day_availability set flag=1 where day_available = %s AND time_slot=%s  AND counsellor_id=%s",(day,time,counsellor_id,))
            mysql.connection.commit()
            cur.close()
        uid=session["user"]
        cur = mysql.connection.cursor()
        cur.execute("select * from ( SELECT * from APPOINTMENT natural join counsellor where user_id=%s) as a",(session["user"],))
        res=cur.fetchone()
        if (res!=0 and res!=None ):
            
            A_date=res[4]
            A_time=res[3]
            name=res[7]
            meet_link=res[5]
            
            enable = True
            # from datetime import date
            # import datetime
            # todays = datetime.datetime.now()
            # from datetime import datetime
            #A_time = datetime.strptime(str(A_time),"%H:%M:%S")
            #A_date = datetime.strptime(str(A_date),"%Y-%m-%d")
            # C_time = todays.time()
            # C_date = todays.date()
            # print(type(C_time))
            # print(type(C_date))
            # print(type(todays.min+A_date+A_time))
            # print(type(A_date))
            # #
            
            #C_date = todays.strptime(date,"%Y-%m-%d")
            #if(A_date==C_date and C_time-(A_time+A_date)>datetime.timedelta(seconds=1) and C_time-(A_time+A_date) <=datetime.timedelta(hours=1)):
             #   enable=True     

            return render_template("mysessions.html",time=A_time,date=A_date,name=name,meet_link=meet_link,enable=enable)
        return render_template("nosession.html")
    else:
        return redirect(url_for("home"))
@app.route("/delete", methods = ["POST"])
def delete():
    if request.method == "POST":
        day= session["day"]
        time=session["time"]
        booked_counsellor=session["booked_counsellor"]
        cur = mysql.connection.cursor()
        cur.execute("update day_availability set flag=0 where day_available = %s AND time_slot=%s AND counsellor_id=%s",(day,time,booked_counsellor,))
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM appointment WHERE user_id=%s",(session["user"],))
        cur.close()
        mysql.connection.commit()
        session.pop("day")
        session.pop("time")

    return redirect(url_for("mysession"))

# @app.route("/mysessions")
# def mysessions():
#     if "user" in session:
#         uid=session["user"]
#         cur = mysql.connection.cursor()
#         cur.execute("select * from ( SELECT * from APPOINTMENT natural join counsellor where user_id=%s) as a",(session["user"],))
#         res=cur.fetchone()
#         if (res!=0 ):
            
#             date=res[4]
#             time=res[3]
#             name=res[7]
#             meet_link=res[5]

#             return render_template("mysessions.html",time=time,date=date,name=name,meet_link=meet_link)
#         return render_template("booking.html")

#     else:
#         return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True,port=8080)
