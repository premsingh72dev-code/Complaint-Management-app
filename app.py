from flask import Flask, render_template, session, request, jsonify, json, redirect, url_for, send_from_directory
from flask_session import Session
import os
import pymongo
import datetime
from flask_mail import Mail
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
import json
import jwt
import re
import time
import random
import uuid
from emailcodes import OtpEmailMessage, sendRegisterComplaint, adminAcceptRequest, CloseRequest, sendFeedBack, send_otp_email
from dotenv import load_dotenv
load_dotenv() 
import traceback
from Reports import generate_admin_pdf, generate_user_pdf

# <----------- env setup -------->

my_db_url = os.getenv('DATABASE_URL')
secret_key = os.getenv('SECRET_KEY')

EMAIL_ADDRESS = os.getenv('Email_Username')
EMAIL_PASSWORD = os.getenv('Email_Password')
smtp_mail = os.getenv("SMTP_MAIL")

# <---------------- Flask app Setup ----------------->

folder_name = "uploads"

app = Flask(__name__)
app.secret_key = secret_key
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['uploads'] = f"{os.getcwd()}/{folder_name}"
app.config['Records'] = f"{os.getcwd()}/Records"
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB limit
Session(app)

# *************** Mail Setup *************

app.config["MAIL_SERVER"] = smtp_mail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = EMAIL_ADDRESS
app.config['MAIL_PASSWORD'] = EMAIL_PASSWORD
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

# <++++++++++++++++++++++       Logs Code Starts Here      ++++++++++++++++++++++>

def setup_logging():
    log_folder = "Logs"
    os.makedirs(log_folder, exist_ok=True)

    log_date = datetime.date.today().strftime("%d-%m-%Y")
    log_filename = os.path.join(log_folder, f"{log_date}.log")

    app.logger.setLevel(logging.DEBUG)

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_filename for h in app.logger.handlers):
        file_handler = logging.FileHandler(log_filename, mode="a")
        file_handler.setLevel(logging.DEBUG) 

        formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        file_handler.setFormatter(formatter)

        app.logger.addHandler(file_handler)

setup_logging() 

# <--------------------         Logs status check code ---------------->

@app.before_request
def log_request_info():
    app.logger.info(f"➡️ API Called: {request.method} {request.path}")
    app.logger.info(f"🔹 Request Headers: {dict(request.headers)}")

    data = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
    elif request.method == "GET":
        data = request.args.to_dict()

    app.logger.info(f"📩 Request Data: {data}")
    
# <+++++++++++++++++++++++++++++++      Logs Code END Here        ++++++++++++++++++++++++++++++++>

# <===============================           FireBase Setup          ============================>

import firebase_admin
from firebase_admin import credentials, messaging, exceptions


# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# <========================             END         =========================>


# <----------------------    DataBase Code  ---------------------->

client = pymongo.MongoClient(my_db_url)
db = client['AllUsers']
collection1 = db['Admin-Details']
collection2 = db['All-Users']

db2 = client['Complaints-Records']
collection3 = db2['Complaints']
collection31 = db2['Updated-Accepted-Complaints']

db3 = client['Notifications']
collection4 = db3['Send-Notifications']

db4 = client['Feedback']
collection5 = db4['All-Feedbacks']

db5 = client['Reports']
collection6 = db5['Reports']

# <----------------------    Jwt code Here  ---------------------->

def create_jwt(user_id):
    try:
        payload = {
            'user_id': user_id,
            'iat': datetime.datetime.utcnow(), 
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(str(e))
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return f"error of {e}"
    
# >--------------------      Decode Access-Token      ---------------------<

def decode_jwt(token):
    try:
        decoded_payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return {"response": "success", "data": decoded_payload}
    except jwt.ExpiredSignatureError:
        return {"response": "error", "message": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"response": "error", "message": "Invalid token"}

    
# <----------------------       Token Code End        ---------------------->

# <======================   FireBase Code Starts Here   ==========================>

# def send_notification(token, title, body):
#     try:
#         message = messaging.Message(
#             notification=messaging.Notification(
#                 title=title,
#                 body=body,
#             ),
#             token=token,  # The device token
#         )
#         response = messaging.send(message)
#         app.logger.info(f"Notification successfully sent {response}")
#         return {'res':'success', 'msg':response, 'code':200}
#     # except messaging.FirebaseError as e:
#     except exceptions.FirebaseError as e:
#         app.logger.error(f'Error sending message: {e}',exc_info=True)
#         return {'res':"error", 'msg':str(e), 'code':402}

def send_notification(token, title, body):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )
        response = messaging.send(message)
        app.logger.info(f"Notification successfully sent: {response}")
        return {'res': 'success', 'msg': response, 'code': 200}
    
    except exceptions.InvalidArgumentError as e:
        app.logger.error("Notification error: Invalid FCM token", exc_info=True)
        # Optional: Remove token from DB
        return {'res': 'error', 'msg': 'Invalid FCM token', 'code': 400}

    except messaging.UnregisteredError:
        app.logger.warning(f"Unregistered FCM token: {token}")
        # Optionally remove token from your database here
        return {'res': 'error', 'msg': 'Unregistered token - should be deleted', 'code': 410}

    except exceptions.FirebaseError as e:
        app.logger.error(f'Firebase error: {e}', exc_info=True)
        return {'res': 'error', 'msg': str(e), 'code': 402}

    except Exception as e:
        app.logger.error(f'Unexpected error: {e}', exc_info=True)
        return {'res': 'error', 'msg': str(e), 'code': 500}


# <======================   FireBase Code ENDS Here   ==========================>


# <----------------------      All Html Page Render Code        ---------------------->


# <==================   Dashboard Code =====================>

@app.route('/')
def dashboard():
    if session.get('access_token'):
        return render_template("AdminFolder/dashboard.html", token=session['access_token'])
    else:
        app.logger.warning(f'Error Session Not found')
        return render_template("login.html")
    
# <==================   Index All Users Page  Code =====================>

@app.route('/index')
def home():
    if session.get('access_token'):
        users_types = collection1.find_one({'_id':'AllUsers'},{'_id':0})
        return render_template("AdminFolder/home.html", users = users_types, token=session['access_token'])
    else:
        app.logger.warning(f'Error Session Not found')
        return render_template("login.html")
    
# <=======================   API For Number of Users     =====================>

@app.route("/AccountNumbersUsers", methods=['GET', 'POST'])
def AccountsUsers():
    if session.get('access_token'):
        if request.method == 'GET':
            try:
                admin_users = list(collection2.find({'permission':2, 'Role':'admin'}))
                users_types = list(collection2.find({'permission':3, 'Role':'user'}))
                response = {
                    'Admins':len(admin_users),
                    'Users': len(users_types),
                }
                return {'res':response, 'msg':'success', 'code':200}
            
            except Exception as e:
                app.logger.error(f'Error in fetching data {e}',exc_info=True)
                return {'res':'error', 'msg':'Something went wrong', 'code':404}
        else:
            app.logger.warning(f'Error Session Not found')
            return render_template("login.html")


# <==================   AddUsers Code =====================>

@app.route("/Addusers")
def addusers():
    if session.get('access_token'):
        users_types = collection1.find_one({'_id':'AllUsers'},{'_id':0}) 
        return render_template("AdminFolder/AddUsers.html", users = users_types)
    else:
        app.logger.warning(f'Error Session Not found')
        return render_template("login.html")

# <==================   login Page Code =====================>

@app.route("/login")
def login():
    if not session.get("access_token"):
        return render_template("login.html")
    else:
        app.logger.warning(f'Error Session Not found')
        return redirect (url_for('home'))
    

# <==================   All Complaints Page Code =====================>

@app.route("/AllComplaints")
def AllComplaintsRecords():
    if session.get("access_token"):
        print("Access TOken is: ", session.get("access_token"))
        return render_template("AdminFolder/Complaints.html")
    else:
        app.logger.warning(f'Error Session Not found')
        return render_template("login.html")


# <----------------------  Super-Admin Login Verification Code     -------------------------->

@app.route("/loginverification", methods=['GET', 'POST'])
def loginverification():
    try:
        if request.method == 'POST':
            data = request.form.to_dict()

            userdetails = collection2.find_one({"email":data['email'], "password":data['password'], "permission":1,"Role":"SuperAdmin"})
            if userdetails is not None:
                user_id = int(userdetails.get('_id'))
                create_token = create_jwt(user_id)
                print("token is: ", create_token)
                session['access_token'] = create_token  
                app.logger.info(f"Successfully Login ---> {data['email']}")
                return{"res":"success", "msg":"Successfully login", 'code':200}
            else:
                app.logger.warning(f'Invalid Credentials:')
                return{"res":"error", "msg":"Invalid Credentials", 'code':404}
        else:
            return "Invalid Request"
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {"res":'error', "msg":"Something went wrong", 'code':404}
        
# <-----------------------------------  Email Verification Code   ------------------------------------>

@app.route("/checkvalidEmailexists", methods=['GET', 'POST'])
def checkemailvalid():
    if session.get("access_token"):
        try:
            if request.method == "POST":
                data = request.form.to_dict()
                print("Data email: ", data)
                email_check = collection2.find_one({"email":data.get("email")},{"email":1, "_id":0})
                if email_check is None:
                    return {"res":"Not registered", "msg":"Not registered", 'code':200}
                else:
                    return{'res':'already registered',"msg":"already registered", 'code':404}
        except Exception as e:
            app.logger.error(f'Error occurred: {e}',exc_info=True)
            return {'res':str(e)}

# <-------------------------   Admin Registered Sub-Admin And Users   ------------------------------->

@app.route("/AddUsersRecords", methods=['GET', 'POST'])
def AdminaddUsersRecords():
        try:
            if request.method == "POST":
                data = request.form.to_dict()
                print(data)
                # token = data['token']
                # Email Validation:
                email = data.get('email', '')
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    return {'res': 'error', 'code': 400, 'msg': 'Email is not valid!'}, 400
                
                email_check = collection2.find_one({"email":email},{"email":1, "_id":0})
                if email_check is not None:
                    return {'res': 'error', 'code': 400, 'msg': 'Email is Already Registered!'}
                    
                # Phone Number Validation:
                phone = data.get('Phone Number', '')
                if not phone.isdigit() or len(phone) < 10:
                    return {'res': 'error', 'code': 400, 'msg': 'Phone Number is not valid!'}
                
                phone_check = collection2.find_one({"Phone Number":data.get("Phone Number")},{"Email":1, "_id":0})
                if phone_check is not None:
                    return {'res': 'error', 'code': 400, 'msg': 'Phone Number is Already Registered !'}
                else:
                    current_time = time.time()
                    new_account_id = int(current_time * 1000)
                    data['_id'] = str(new_account_id)
                    if data.get('Status') == "on":
                        data['Status'] = "active"
                    else:
                        data['Status'] = "inactive"
                    data['Account Creation Date'] = {
                        "Date":str(datetime.datetime.now().strftime("%d-%m-%Y")),
                        "Time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                        "DateTime": str(datetime.datetime.now())
                    }
                    
                    data['Account Last Login'] = str(datetime.datetime.now())
                    
                    if data['Account Holder'] == "User":
                        data['Role'] = "user"
                        data['permission'] = 3
                    else:
                        data['Role'] = "admin"
                        data['permission'] = 2
                        
                    collection2.insert_one(data)
                    app.logger.info(f"Account Successfully Created, id is : {data['_id']} & Data : {data} ")
                    return {'res':"success", "msg":"Account Successfully Created", "code":200}
            else:
                app.logger.warning(f"Invalid Request")
                return {'res':'error', 'msg':'Invalid Request', 'code':401}
        except Exception as e:
            app.logger.warning(f"Error is: {traceback.format_exc()}")
            app.logger.error(f'Error occurred: {e}',exc_info=True)
            return {'res':str(e)}
    
# <----------------------------     AllUsers Data       -------------------------------->

@app.route("/GetAllUsersRecordsData", methods=['GET', 'POST'])
def GetAllUsersRecordsData():
    try:
        if request.method == "POST":
            user = request.form.to_dict()
            token = user.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_user is not None:                 
                    admindata = list(collection2.find({"Role":{"$eq":"admin"}},{"ID":0}))
                    allUsers = list(collection2.find({"Account Holder":{"$eq":"User"}},{"ID":0}))
                    return {'res':{"Admins":admindata,"users":allUsers},'msg':'success', 'code':200}
                else:
                    app.logger.warning(f"error, User Status is Not Active")
                    return {'res':None, "users":None, 'msg':'error', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {'res':"error", 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':"error", 'msg':'Something went wrong !', 'code':404}

# <-----------------------------------   Account Status Update     ------------------------------------>

@app.route("/AccountStatus", methods=['GET','POST'])
def AccountStatusUpdate():    
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            # print("Data is: ", data)
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            # userid = decode_jwt(data['token'])
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_user is not None:  
                    # print("Data --->", data.get('ID'))
                    user_details = collection2.find_one({"_id":data['ID']},{'Status':1, "_id":1})
                    # print("User Details: ", user_details)
                    if user_details.get('Status') == "active":
                        collection2.update_one({"_id":data['ID']}, {"$set": {"Status":"Deactivated"}})
                    else:
                        collection2.update_one({"_id":data['ID']}, {"$set": {"Status":"active"}})
                    return {"res":"success", "msg":"Account Status Updated", 'code':200}
                else:
                    return jsonify({'res': 'error', 'msg': 'User not found', 'code': 401})
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    

# <-----------------------------------  Account Delete Permanently    ------------------------------------>

@app.route("/DeleteAccount", methods=['GET','POST'])
def DeleteAccount(): 
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                # print("User ID:", user_id)
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_user is not None:
                    collection2.delete_one({"_id":data['ID']})
                    app.logger.info(f"Account Successfully Removed By : {check_user}")
                    return {'res':'success', 'msg':"Account Successfully Removed", "code":200}
                else:
                    app.logger.warning(f"No User Found !, check account status")
                    return {"res":"error", "msg":"User Not Found", "code":404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning("invalid Request")
            return {'res':'error','msg':"Invalid Request !", 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error','msg':"Something went wrong !", 'code':404}
    
    
# <-----------------------------------  Edit Account Details    ------------------------------------>

@app.route("/EditAccountDetails", methods=['GET','POST'])
def EditAccountDetails():
        try:
            if request.method == "POST":
                data = request.form.to_dict()
                token = data.get('token')
                
                if not token:
                    return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
                
                decoded_token = decode_jwt(token)
                
                if decoded_token.get("response") == "success":
                    user_id = str(decoded_token['data']['user_id'])
                    check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                    if check_user is not None:
                        user_details = collection2.find_one({"_id":data.get('ID')})
                        return {'res':user_details, 'msg':'success', 'code':200}
                    else:
                        app.logger.warning(f"error, Account is not active or User not found !")
                        return {'res':None, 'msg':"Invalid Request !", 'code':404}
                else:
                    app.logger.warning(f"Invalid token: {token}")
                    return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
            else:
                app.logger.warning("Invalid Request")
                return {'res':"error", 'msg':"Something went wrong !", 'code':404}
        except Exception as e:
            app.logger.error(f'Error occurred: {e}',exc_info=True)
            return {'res':"error", 'msg':"Something went wrong !", 'code':404}


# <-----------------------------------      Account Details Update     ------------------------------------>

@app.route("/UpdateUserdetails", methods=['GET','POST'])
def UpdateUserAccountDetails():
    try:
        if request.method == "POST":
            user_data = request.form.to_dict()
            print("user Data -->", user_data)
            token = user_data.get('token') 
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_user is not None:
                    # if check_user['Account Holder'] == "User":
                    #     user_data['Role'] = "user"
                    #     user_data['permission'] = 3
                    # elif check_user['Account Holder'] == "":
                    #     user_data['Role'] = "admin"
                    #     user_data['permission'] = 2
                    print("User Data is: ", user_data)  
                    del user_data['token']
                    collection2.update_one({"_id":user_data['ID']},{"$set":user_data})
                    app.logger.info(f"Account Details Successfully Updated !, {user_data}")
                    return {'res':'success', 'msg':'User Details Successfully Updated !', 'code':200}
                else:
                    app.logger.warning("error, User not found, Account is not active.")
                    return {'res':None, 'msg':'Something went wrong !', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.error("error, Invalid Request")
            return {'res':'error','msg':"Invalid Request !", 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error','msg':"Something went wrong !", 'code':404}
    

# <-----------------------------    END    -------------------------------->

    
# <--------------------------   AppLogin Verification   ------------------------->

# @app.route("/loginappverfiy", methods=['GET', 'POST'])
# def loginverifyapp():
#     try:
#         if request.method == "POST":
#             data = request.form.to_dict()
            
#             email = data.get('email')
#             password = data.get('password')
            
#             if not email or not password:
#                 return jsonify({'res': "Not valid", "msg": "Email and Password are required", "code": 400})
            
#             check_user = collection2.find_one({"email":email, "password":password},{'email':1, "_id":1, "DeviceDetails":1, "Name":1, "Status":1,})
            
#             if check_user is None:
#                 app.logger.warning(f"Account is Not Registered or email ID OR Pasword is not valid : {data}")
#                 return {'res':"Not valid", "msg":"Account is Not Registered or email ID OR Pasword is not valid", "code":404}
            
#             elif check_user.get('Status') != "active":
#                 app.logger.warning(f"This Account is Not Active : {data}")
#                 return {'res':"Not valid", "msg":"Account is Not Active please Contact Admin", "code":404}
            
#             # OTP generation
#             if email == "master@gmail.com" and password == "123456":
#                 generate_otp = "123456"
#             else:
#                 generate_otp = str(random.randint(100000, 999999))
                
#                 # Send Notification to user-Device:
                
#                 device_token = check_user.get("DeviceDetails", {}).get('device-token')
                
#                 if device_token is not None:
#                     title = "Authentication OTP"
#                     body = f"Dear {check_user['Name']},Please Enter OTP {generate_otp} to login in Sahayata app."
#                     notification_res = send_notification(device_token, title, body)
#                     print("Response of Notification is: ", notification_res)
#                     if notification_res.get("res") == "success":
#                         Notification = {}
#                         current_time = time.time()
#                         Notification['_id'] = str(int(current_time * 1000))
                        
#                         Notification['title'] = title
#                         Notification['body'] = body
#                         Notification['dates'] = {
#                             "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
#                             "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
#                             "dateTime": str(datetime.datetime.now())
#                         }
#                         Notification['Type'] = "Login OTP"
#                         Notification['Status'] = notification_res
#                         Notification['UserID'] = check_user.get('_id')
#                         collection4.insert_one(Notification)
#                     else:
#                         app.logger.info(f"Notification error, chek the Error")
#                 else:
#                     app.logger.warning(f"Device token not Found for this user --> {check_user.get('Name')}")
                
#                 # Email Send to User Gmail Account
                
#                 user = data['email']
#                 subject = "Verify Your Account"
#                 send_otp_mail = OtpEmailMessage(user, generate_otp, subject)
#                 if send_otp_mail.get('res') == "success":
#                     user_id = check_user['_id']
#                     user_token = create_jwt(user_id)
#                     collection2.update_one({"email":data['email']},{"$set":{
#                         "OTP":generate_otp
#                     }})
#                     app.logger.info(f"Email Successfully Sent to Registered Email : {data['email']}")
#                     return {'res':'success', 'msg':"Email Successfully Sent to Registered Email", 'code':200, "token":user_token}
#                 else:
#                     app.logger.warning(f"error, Email sent failed -->  {data['email']} & error is: {send_otp_mail}")
#                     return {'res':'error', "msg":'Something went Wrong', 'status':404}      
#         else:
#             app.logger.warning("Invalid Request")
#             return {'res':'Invalid Request', 'msg':'Something went Wrong', 'status':404}
#     except Exception as e:
#         app.logger.error(f'Error occurred: {e}',exc_info=True)
#         return {'res':'error', 'msg':'Something went Wrong', 'status':404}


@app.route("/loginappverfiy", methods=['POST'])
def loginverifyapp():
    try:
        data = request.form.to_dict()

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'res': "Not valid", "msg": "Email and Password are required", "code": 400})

        check_user = collection2.find_one(
            {"email": email, "password": password},
            {'email':1, "_id":1, "DeviceDetails":1, "Name":1, "Status":1}
        )

        if check_user is None:
            app.logger.warning(f"Account not registered or invalid credentials: {data}")
            return jsonify({'res':"Not valid","msg":"Invalid Email or Password","code":404})

        if check_user.get('Status') != "active":
            app.logger.warning(f"Account not active: {data}")
            return jsonify({'res':"Not valid","msg":"Account is not active. Contact Admin","code":403})

        # OTP generation
        if email == "master@gmail.com" and password == "123456":
            generate_otp = "123456"
        else:
            generate_otp = str(random.randint(100000, 999999))

        # Send push notification
        device_token = check_user.get("DeviceDetails", {}).get('device-token')

        if device_token:
            title = "Authentication OTP"
            body = f"Dear {check_user['Name']}, Please enter OTP {generate_otp} to login in Sahayata app."

            notification_res = send_notification(device_token, title, body)

            if notification_res.get("res") == "success":
                Notification = {}
                current_time = time.time()
                Notification['_id'] = str(int(current_time * 1000))
                Notification['title'] = title
                Notification['body'] = body
                Notification['Type'] = "Login OTP"
                Notification['Status'] = notification_res
                Notification['UserID'] = check_user.get('_id')

                Notification['dates'] = {
                    "date": datetime.datetime.now().strftime("%d-%m-%Y"),
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "dateTime": str(datetime.datetime.now())
                }

                collection4.insert_one(Notification)

        # Send email OTP
        subject = "Verify Your Account"
        send_otp_mail = OtpEmailMessage(email, generate_otp, subject)

        if send_otp_mail.get('res') == "success":

            user_id = check_user['_id']
            user_token = create_jwt(user_id)

            collection2.update_one(
                {"email": email},
                {"$set": {"OTP": generate_otp}}
            )

            app.logger.info(f"Email successfully sent to {email}")

            return jsonify({
                'res': 'success',
                'msg': "OTP sent successfully",
                'code': 200,
                'token': user_token
            })

        else:
            app.logger.warning(f"Email sending failed: {email}")

            return jsonify({
                'res': 'error',
                'msg': 'Email sending failed',
                'code': 500
            })

    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)

        return jsonify({
            'res': 'error',
            'msg': 'Something went wrong',
            'code': 500
        })

# <-----------------------------------  User OTP Verify    ------------------------------------>

@app.route("/VerifyUserOtp", methods=['GET', 'POST'])
def VerifyUserOtp():
    try:
        if request.method == "POST":
            otp_details = request.form.to_dict()
            print("OTP Details: ", otp_details)
            
            user_token = otp_details.get('token')
            if not user_token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
                
            verify_token = decode_jwt(user_token)
            if verify_token.get("response") == "success":
                user_id = str(verify_token['data']['user_id'])
            
                verify_user = collection2.find_one({"_id":user_id, "Status":"active"},{'email':1, "OTP":1, "_id":1, "Role":1})
                print("verify User: ", verify_user)
                if verify_user is not None:
                    user_otp = otp_details.get('OTP')
                    if user_otp == verify_user['OTP']:
                        collection2.update_one({"_id":user_id}, {"$set":{
                            'Account Last Login': str(datetime.datetime.now())
                        }})
                        collection2.update_one({"_id":user_id},{"$unset":{"OTP":""}})
                        app.logger.info(f"OTP Verified Successfully, {verify_user.get('Role')}")
                        return {'res':'success', 'msg':'OTP Verified Successfully !', 'code':200, "Role":verify_user.get("Role"), "token":user_token}
                    else:
                        app.logger.warning(f"Invalid OTP")
                        return {'res':'error', 'msg':'Invalid OTP', 'code':400}
                else:
                    app.logger.warning(f"Account is Not Valid, check account status")
                    return {'res':'error', 'msg':'Account Not Valid', 'code':400}
            else:
                app.logger.warning(f"Invalid token: {verify_token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':400}
        return {'res':'error', 'msg':'Something went Wrong', 'code':401}
                    
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went Wrong', 'code':400}
    
# <--------------------------   User's Device token registered        ---------------------> 

@app.route("/Registered-device", methods=['GET', 'POST'])
def deviceRegistered():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            # print("Data: ", data)
            
            token = data.get('token')

            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
                
                account_status = collection2.find_one({"_id":user_id, "Status":"active"})
                if account_status is not None:
                    collection2.update_one({"_id":user_id},{"$set":{
                        "DeviceDetails":{
                            "device-token":data['device-token'],
                            "lastUpdated": str(datetime.datetime.now())
                        }
                    }})
                    return {'res':'success', 'msg':'token Updated', 'code':200}
                else:
                    return {'res':'error', 'msg':'invalid account', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':400} 
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went Wrong', 'code':400}


# <-----------------------------------    Generate Complaint Number     ------------------------------------>

def generate_complaint_number():
    timestamp = int(time.time())
    random_number = random.randint(1000, 9999)
    complaint_number = f"CR{timestamp}{random_number}"
    return complaint_number

# <-----------------------------------      Register Complaint       ------------------------------------>

@app.route('/ComplaintRegister', methods=['GET','POST'])
def RegisterComplaint():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            file = request.files.get('file')
            # print("Data is: ", data)
            app.logger.info(f"{data}")
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                userdetails = collection2.find_one({"_id":user_id,"Status":"active"})
                if userdetails is not None:
                    if file and file.filename:  
                        print('File Name is : ', file.filename)
                        file_id = str(uuid.uuid4())
                        new_file_name = f'{file_id}-{file.filename}'
                        print("File New Name is: ", new_file_name)
                        print("dir: ", os.getcwd())
                        data['file'] = str(new_file_name)
                        if not os.path.exists(folder_name):
                            os.makedirs(f"{os.getcwd()}/{folder_name}")
                        file.save(os.path.join(app.config[folder_name], new_file_name))
                    
                    complaint_number = generate_complaint_number()
                    data['Complaint ID'] = str(complaint_number)
                    data['Complaint Status'] = "Open"
                    current_date = datetime.datetime.now()
                    current_time = datetime.datetime.now()
                    data['complaintRegisterDates'] = {
                        "complaintDateTime": str(datetime.datetime.now()),
                        "Date": str(current_date.strftime("%d-%m-%Y")),
                        "Time": str(current_time.strftime("%H:%M:%S")),
                        "Month":str(current_date.strftime("%B")),
                        "Year": str(current_date.strftime("%Y")),
                    }
                    
                    data['DateTime'] = {
                        "DateTime": str(datetime.datetime.now()),
                        "Date": str(current_date.strftime("%d-%m-%Y")),
                        "Time": str(current_time.strftime("%H:%M:%S"))
                    }
                    
                    data['userDetails'] = {
                        "ID":userdetails['_id'],
                        "name":userdetails['Name'],
                        "phoneNumber":userdetails['Phone Number'],
                        "email":userdetails['email'],
                        "address":userdetails['House Number']
                    }
                    del data['token']
                    data['_id'] = str(complaint_number)
                    collection3.insert_one(data)
                    user = userdetails['email']
                    subject = f"Complaint Successfully Registered With Complaint Number: {complaint_number}"
                    send_comp = sendRegisterComplaint(user, subject, complaint_number)
                    app.logger.info(f"{subject}")
                    
                    # <---      Complaint Register Notification     ----->
                    
                    complaint_type = data['Complaint Type']
                    name = userdetails['Name']
                    complaintID = str(complaint_number)
                    response = register_notification(name,complaint_type,complaintID)
                    print("Response is: ", response)
                    if response.get('res')=="success":
                        app.logger.info("Notification Successfully Send")
                    elif response.get('res')=="error":
                        app.logger.error(f"Something went wrong, check code, {response.get('msg')}")
                    return{'res':data, 'msg':'Complaint Register Successfully !', 'code':200}
                else:
                    app.logger.warning(f"error, Account is Not Active, {userdetails}")
                    return{'Res':'error', 'msg':'Account is Not Active', 'code':404}
            else:
                app.logger.warning(f"Token expired: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return{'Res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return{'Res':'error', 'msg':'error', 'code':404}
    
# <---------------------------- send notification to Admin ---------------------------->

def register_notification(name, complaint_type, complaintID):
    try:
        
        admin_details = list(collection2.find({'Account Holder': str(complaint_type), "Status": 'active', 'permission': 2}))
        # print("Admins:", admin_details)
        
        if not admin_details:
            return {'res': 'error', 'msg': 'No active admins found for this complaint type'}
        
        response = "error"
        message = "Notification Error"

        for i in admin_details:
            # print('Admin Name:', i.get('Name', 'Unknown'))
            devicetoken = i.get('DeviceDetails', {}).get('device-token')

            if not devicetoken:
                app.logger.warning(f"Skipping admin {i.get('Name', 'Unknown')} due to missing device token")
                continue
            
            title = "New Complaint Registered"
            body = f"Dear {i.get('Name', 'Admin')}, {name} has submitted a complaint regarding a {complaint_type} issue. Please review and take necessary action."
            
            res = send_notification(devicetoken, title, body) or {}

            # print("Response:", res)
            
            if res.get("res") == "success":
                response = "success"
                message = "Notification Successfully Sent"
                
                Notification = {
                    '_id': str(int(datetime.datetime.utcnow().timestamp() * 1000)),
                    'title': title,
                    'body': body,
                    'Type': "Complaint Registered",
                    'ComplaintID': complaintID,
                    'UserID': str(i.get('_id')),
                    'Status': res,
                    'dates': {
                        "date": datetime.datetime.now().strftime("%d-%m-%Y"),
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "dateTime": str(datetime.datetime.now())
                    }
                }
                collection4.insert_one(Notification)
                app.logger.info("Notification successfully sent in Register Complaint section")
                time.sleep(2)
            else:
                app.logger.warning("Notification was not sent in Register Complaint, check error")
        return {'res': response, 'msg': message}
    except Exception as e:
        app.logger.error(f"Error occurred: {e}", exc_info=True)
        return {'res': 'error', 'msg': str(e), 'code': 404}
     
# <-----------------------------------      EDIT/Get User  Complaints       ------------------------------------>

@app.route("/getUserComplaintdetails", methods=['GET', 'POST'])
def getUsersComplaintsDetails():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
        
                check_complaint = collection3.find_one({"userDetails.ID":user_id, "Complaint ID":data['Complaint ID']},{"complaintRegisterDates":0,"ComplaintModifyDates":0, "_id":0})
                
                if check_complaint:
                    complaint_status = check_complaint
                else:
                    complaint_status = "Not Found"
                return {'res':complaint_status, "msg":"success", 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.error(f'Invalid Request')
            return {"res":"error", "msg":"Invalid Request", "code":402}
    except Exception as e:
        print(traceback.format_exc())
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':"Something went Wrong !", 'code':404}
    
# <-------------------------     Update User Modify Request       -------------------------------->

@app.route("/ModifyUserComplaint", methods=['GET', 'POST'])
def ModifyUserComplaint():
    try:
        if request.method == "POST":
            complaint_data = request.form.to_dict()
            token = complaint_data.get('token')
            
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
                
                check_user = collection2.find_one({'_id':user_id, 'Status':'active'})
                
                if check_user is None:
                    return jsonify({'res': 'error', 'msg': 'User Account is not active', 'code': 401})
                
                file = request.files.get('file')
                if file and file.filename:  
                    file_id = str(uuid.uuid4())
                    new_file_name = f'{file_id}-{file.filename}'
                    complaint_data['file'] = str(new_file_name)
                    if not os.path.exists(folder_name):
                        os.makedirs(f"{os.getcwd()}/{folder_name}")
                    file.save(os.path.join(app.config[folder_name], new_file_name))
                
                del complaint_data['token']
                current_date = datetime.datetime.now()
                current_time = datetime.datetime.now()
                complaint_data['DateTime'] = {
                    "DateTime": str(datetime.datetime.now()),
                    "Date": str(current_date.strftime("%d-%m-%Y")),
                    "Time": str(current_time.strftime("%H:%M:%S"))
                    }
                
                complaint_data['ComplaintModifyDates'] = {
                    "Updated DateTime": str(datetime.datetime.now()),
                    "updatedDate": str(current_date.strftime("%d-%m-%Y")),
                    "UpdatedTime": str(current_time.strftime("%H:%M:%S")),
                    "Month":str(datetime.datetime.now().strftime("%B")),
                    "Year": str(datetime.datetime.now().strftime("%Y")),
                }
                collection3.update_one({"_id":complaint_data['Complaint ID']},{"$set":complaint_data})
                return{'res':complaint_data, "msg":'Complaint Successfully Updated', "code":200,}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {"res":"error", "msg":"Invalid Request", "code":402}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':"Something went Wrong !", 'code':404}

# <-----------------------------------        Get Users Complaints Data      ------------------------------------>

@app.route("/GetcomplaintsData", methods=['GET','POST'])
def GetComplaintsdata():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
        
                check_complaint = list(collection3.find({"userDetails.ID":user_id, "Complaint Status":"Open"},{"complaintRegisterDates":0,"ComplaintModifyDates":0, "_id":0}))

                return {'res':check_complaint, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':400}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Invalid Request', 'code':400}

# <----------------          url for Uploaded files         -------------------------->

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['uploads'], filename)
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'No file found', 'code':404}
    
    
# <-------------------------     User Details   ---------------------------->

@app.route("/getuserdetails", methods=['POST'])
def getUserdetails():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                userData = collection2.find_one({"_id":user_id},{"Name":1, "email":1, "Phone Number":1, "House Number":1, })
                return {"res":userData, "msg":'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':None, 'msg':"Invalid Request", 'code':404}
    except Exception as e:
        print(str(e))
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
# <-----------------------------    Update user Details     ------------------------>

@app.route("/accountdetailsupdate", methods=['POST'])
def updateaccountdetails():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                del data['token']
                collection2.update_one({"_id":user_id},{"$set":data})
                app.logger.info(f"Details Successfully updated, {data}")
                return {'res':"success", 'msg':'Account Details successfully Updated', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
        

# <-----------------------------------      Delete Complaint by user       ------------------------------------>

@app.route("/DeleteComplaint", methods=['GET','POST'])
def DeleteComplaint():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            get_file_name = collection3.find_one({"_id":data['Complaint ID']},{"file":1, "_id":0})
            print("Filename :", get_file_name)
            if get_file_name and 'file' in get_file_name:
                folder_name = "uploads"
                file_name = get_file_name['file']  
                file_path = f"{folder_name}/{file_name}"  

                try:
                    os.remove(file_path)  
                    print("File removed successfully.")
                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except Exception as e:
                    print(f"Error removing file: {e}")
            
            collection3.delete_one({"_id":data['Complaint ID']})
            return {'res':'success', 'msg':'Complaint Successfully Delete', 'code':200}
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':400}

# <-----------------------------------              Admin Code for App             ------------------------------------>

    # <------------------   All Users     ---------------------> 

@app.route("/GetAlladmintypes", methods=['GET','POST'])
def GetAllUsersTypes():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                check_admin = collection2.find_one({"_id":user_id, "Status":"active"},{"_id":1, "Account Holder":1, "permission":1})
                print("check Admin type is: ", check_admin)
                if check_admin is not None:
                    if check_admin.get("permission") == 2 or check_admin.get("permission") == 3:
                        allClients = collection1.find_one({"_id":"Admins"},{"_id":0, "Account Holder":1})
                        return {'res':allClients, 'msg':'Success', 'code':200}
                    elif check_admin.get("permission") == 1 and check_admin.get("Account Holder") == "SuperAdmin":
                        allClients = collection1.find_one({"_id":"AllUsers"},{"_id":0, "Account Holder":1})
                        return {'res':allClients, 'msg':'Success', 'code':200}
                    else:
                        return {'res':'error', 'msg':'permission denied', 'code':404}   
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})     
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':400}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':400}
    

#        <--------------------      All user Details        ------------------->

@app.route("/GetAllUserData", methods=['GET', 'POST'])
def GetAllUserData():
    try:
        if request.method == "POST":
            admintoken = request.form.to_dict()
            
            token = admintoken.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                check_admin = collection2.find_one({"_id":user_id, "Status":"active"},{"_id":1, "Account Holder":1})
                if check_admin is not None:
                    allUsers = list(collection2.find({"Account Holder":"User"},{"_id":1, "Name":1, "email":1, "Phone Number":1, "Account Holder":1, "House Number":1, "Role":1, "ID":1, "Account Creation Date":1, "Branch":1, "gender":1, "Designation":1, "landmark":1}))
                    return {'res':allUsers, 'msg':'success', 'code':200}
                else:
                    allUsers = []
                return {'res':'error', 'msg':'Account is Not Active', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger(f"Invalid Request")
            return{'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return{'res':'error', 'msg':'Something went wrong', 'code':400}

# <-----------------        Get All Open  Complaints Data        ----------------->

@app.route("/getallnewcomplaints", methods=['GET','POST'])
def getallnewcomplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
                check_type = collection2.find_one({'_id':user_id},{"Account Holder":1,"_id":0, "permission":1})
                if check_type.get('permission') == 1:
                    get_all_complaints = list(collection3.find({"Complaint Status":"Open"}).sort("_id", -1))
                    return{'res':get_all_complaints, 'msg':'success', 'code':200}
                else:
                    get_all_complaints = list(collection3.find({"Complaint Type":check_type.get("Account Holder"), "Complaint Status":"Open"}).sort("_id", -1))
                    return{'res':get_all_complaints, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})   
        else:
            return{'res':'error', 'msg':'Invalid Request', 'code':401}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
# <-----------------    Accept User Complaints   ----------------->

@app.route("/AcceptuserComplaint", methods=['GET', 'POST'])
def AcceptuserComplaint():
    try:
        if request.method == "POST":
            accept_data = request.form.to_dict()
            
            token = accept_data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
        
                admin_details = collection2.find_one({"_id":user_id},{"_id":1, "Name":1, "email":1, "Phone Number":1, "Account Holder":1})
                
                if admin_details is None:
                    return {'res':'error', 'msg':'account is not valid', 'code':402}
                
                complaint_user = collection3.find_one({"Complaint ID":accept_data['Complaint ID'], "Complaint Status":"Open"},{"userDetails.name":1, "userDetails.email":1, "Complaint Name":1, "Complaint Type":1, "userDetails.ID":1})
                
                if complaint_user is None:
                    return {'res':'error', 'msg':'Complaint Not found', 'code':402}
                
                account_holder = admin_details.get('Account Holder', None)
                user_complaint_type = complaint_user.get('Complaint Type', None)
                
                if account_holder != user_complaint_type:
                    return {'res':'error', 'msg':f'Another admin can not accept the Complaint', 'code':402}
                
                
                current_date = datetime.datetime.now().strftime("%d-%m-%Y")
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                
                technician_details = {
                    "ID":admin_details.get("_id"),
                    "Name": accept_data.get("admin_name"),
                    "Phone Number": accept_data.get("admin_phone"),
                    "email": admin_details.get("email"),
                    "Date": str(current_date),
                    "Time": str(current_time),
                    "DateTime": str(datetime.datetime.now()),
                    "Complaint": complaint_user.get('Complaint Type')
                }
                
                collection3.update_one({"Complaint ID":accept_data['Complaint ID']}, {"$set":{
                    "Complaint Status":"Accepted",
                    "completion_time": accept_data['completion_time'],
                    "TechnicianDetails":technician_details,
                    "acceptedDateTime": {
                        "DateTime": str(datetime.datetime.now()),
                        "Date": str(current_date),
                        "Time": str(current_time),
                        "Month":str(datetime.datetime.now().strftime("%B")),
                        "Year": str(datetime.datetime.now().strftime("%Y")),
                    }
                }})
                
                userEmail = complaint_user['userDetails']['email']
                subject = f"Request Approved for Complaint No: {accept_data['Complaint ID']}"
                complaint_status = adminAcceptRequest(userEmail, technician_details, subject)
                
                print("<----------      Sending Notifications    ----->")
                
                userID = complaint_user['userDetails']['ID']
                userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                 
                device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                
                if device_token is not None:
                    title = "Complaint Accepted"
                    body = f"Dear {userDetails['Name']}, Your Complaint has been Successfully Accepted By {admin_details['Name']}"
                    notification_res = send_notification(device_token, title, body)
                    print("Response of Notification is: ", notification_res)
                    if notification_res.get("res") == "success":
                        Notification = {}
                        current_time = time.time()
                        Notification['_id'] = str(int(current_time * 1000))
                        
                        Notification['title'] = title
                        Notification['body'] = body
                        Notification['dates'] = {
                            "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                            "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                            "dateTime": str(datetime.datetime.now())
                        }
                        Notification['Type'] = "Complaint"
                        Notification['Status'] = notification_res
                        Notification['ComplaintID'] = accept_data['Complaint ID']
                        Notification['UserID'] = str(userID)
                        collection4.insert_one(Notification)
                        app.logger.info(f"{notification_res}")
                    else:
                        app.logger.warning(f"Notfication error, {notification_res}")
                else:
                    app.logger.warning(f"Device token not Found for this compalaint Number --> {accept_data['Complaint ID']}")
                app.logger.info(f"Complaint Successfully Accepted")
                
                return {'res':'success', 'msg':'Accepted', 'status':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
#   <----------------------------       Complaint Details ----------------------> 


    
    # <------------------------------       Number of Active Complaints    ----------------------------------->

@app.route("/checkComplaintsNumber", methods=['GET','POST'])
def checkComplaintsNumber():
    try:
        if request.method == "POST":
            token_data = request.form.to_dict()
            
            token = token_data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                check_user = collection2.find_one({"_id":user_id, "Status":"active"},{"Account Holder":1, "_id":1, "Name":1, "permission":1})
                print("check user is: ", check_user)
                
                if check_user is not None:
                    total_complaints = {}
                    if check_user.get("permission") == 3:
                        open_complaints = list(collection3.find({"Complaint Status":"Open", "userDetails.ID":check_user['_id']}))
                        approved_complaints = list(collection3.find({"Complaint Status":"Accepted", "userDetails.ID":check_user['_id']}))
                        completed_complaints = list(collection3.find({"Complaint Status":"Completed", "userDetails.ID":check_user['_id']}))
                        rejected_complaints = list(collection3.find({"userDetails.ID":check_user['_id'], 'Complaint Status':'Rejected'}))
                        total_complaints['Open Complaints'] = len(open_complaints)
                        total_complaints['Approved Complaints'] = len(approved_complaints)
                        total_complaints['Completed Complaints'] = len(completed_complaints)
                        total_complaints['Rejected Complaints'] = len(rejected_complaints)
                        
                    elif check_user.get("permission") == 2:
                        open_complaints = list(collection3.find({"Complaint Status":"Open", "Complaint Type":check_user.get('Account Holder')}))
                        approved_complaints = list(collection3.find({"Complaint Status":"Accepted", "Complaint Type":check_user.get('Account Holder'),"TechnicianDetails.ID":check_user['_id']}))
                        completed_complaints = list(collection3.find({"Complaint Status":"Completed", "Complaint Type":check_user.get('Account Holder'),"TechnicianDetails.ID":check_user['_id']}))
                        rejected_complaints = list(collection3.find({"Complaint Status":"Rejected", "Complaint Type":check_user.get('Account Holder'),"TechnicianDetails.ID":check_user['_id']}))
                        total_complaints['Open Complaints'] = len(open_complaints)
                        total_complaints['Approved Complaints'] = len(approved_complaints)
                        total_complaints['Completed Complaints'] = len(completed_complaints)
                        total_complaints['Rejected Complaints'] = len(rejected_complaints)
                        
                    elif check_user.get("permission") == 1:
                        open_complaints = list(collection3.find({"Complaint Status":"Open"}))
                        approved_complaints = list(collection3.find({"Complaint Status":"Accepted"}))
                        completed_complaints = list(collection3.find({"Complaint Status":"Completed"}))
                        rejected_complaints = list(collection3.find({"Complaint Status":"Rejected"}))
                        
                        total_complaints['Open Complaints'] = len(open_complaints)
                        total_complaints['Approved Complaints'] = len(approved_complaints)
                        total_complaints['Completed Complaints'] = len(completed_complaints)
                        total_complaints['Rejected Complaints'] = len(rejected_complaints)
                        
                    return {'res':total_complaints, 'msg':'success', 'code':200}
                else:
                    return {'res':"error", 'msg':'token is not valid', 'code':400}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':"Something went wrong",'code':404}   
    
# <--------------------------       Modify Complaints       ----------------------------->

@app.route("/adminModifyComplaints", methods=['GET','POST'])
def adminModifyComplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            complaint_ID = data.get('Complaint ID')
            complaint_type = data.get("Complaint Type")
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
            
                if check_user is not None:
                    check_complaint_type = collection3.find_one({"_id":complaint_ID, "Complaint Status":"Open"},{"Complaint Type":1, "_id":1,"TechnicianDetails":1, "userDetails":1})
                    if check_complaint_type is not None:    
                        if check_user.get("Account Holder") != "User":
                            user_complaint_type = check_complaint_type.get("Complaint Type")
                            
                            if user_complaint_type != complaint_type:
                                collection3.update_one({"_id":complaint_ID},{"$set":{
                                    "Complaint Type": complaint_type,
                                    "Complaint_modified":True,
                                    "Modification_reason":data.get("Reason"),
                                    "modifiedDates":{
                                        "Date":str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                        "Time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                        "DateTime":str(datetime.datetime.now()),
                                    },
                                    "ModifiedcomplaintAdmin":{
                                        "adminID":check_user.get("_id"),
                                        "adminName": check_user.get("Name"),
                                        "adminEmail": check_user.get("email"),
                                        "adminType": check_user.get("Account Holder"),
                                        "adminPhone": check_user.get("Phone Number"),
                                        "OldComplaintType": check_complaint_type.get("Complaint Type"),
                                        "Reason":data.get("Reason")
                                    }
                                }})
                                
                                # Send Notification to User for Modify Complaint:
                                userID = check_complaint_type['userDetails']['ID']
                                userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                                
                                device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                
                                if device_token is not None:
                                    title = "Complaint Modified"
                                    body = f"Dear {userDetails['Name']}, Your Complaint No. {complaint_ID} has been modified."
                                    notification_res = send_notification(device_token, title, body)
                                    print("Response of Notification is: ", notification_res)
                                    if notification_res.get("res") == "success":
                                        Notification = {}
                                        current_time = time.time()
                                        Notification['_id'] = str(int(current_time * 1000))
                                        
                                        Notification['title'] = title
                                        Notification['body'] = body
                                        Notification['dates'] = {
                                            "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                            "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                            "dateTime": str(datetime.datetime.now())
                                        }
                                        Notification['Type'] = title
                                        Notification['Status'] = notification_res
                                        Notification['ComplaintID'] = complaint_ID
                                        Notification['UserID'] = str(userID)
                                        collection4.insert_one(Notification)
                                        app.logger.info(f"Notification Successfully send ....")
                                    else:
                                        app.logger.warning(f"Notification is not send to {userDetails['Name']}, check error: {notification_res}")
                                else:
                                    app.logger.warning(f"Device token is not found for this Complaint Number :{complaint_ID}")
                                app.logger.info(f"Complaint Successfully Modified.")
                                return {'res':'success', 'msg':'Successfully Request Updated', 'code':200}
                            else:
                                return {'res':'error', 'msg':'Same Complaint can not be Modified', 'code':400}         
                        else:
                            {'res':'error', 'msg':'permission denied', 'code':404}
                    else:
                        return {'res':'error', 'msg':'permission denied', 'code':404}
                else:
                    return {'res':'error', 'msg':'permission denied', 'code':404}   
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})            
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404} 
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':"Something went wrong",'code':404}  
    
# <------------------------------       Admin Code Close Complaints     ------------------------>

# <=============================    OLD Code     ===============================>

# @app.route("/CloseComplaint", methods=['POST'])
# def AdmincloseComplaints():
#     try:
#         if request.method == "POST":
#             data = request.form.to_dict()
#             print("Data -->", data)
            
#             token = data.get('token')
#             if not token:
#                 return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
#             decoded_token = decode_jwt(token)
#             if decoded_token.get("response") == "success":
#                 user_id = str(decoded_token['data']['user_id'])
#                 print("User ID:", user_id)
        
#                 check_user = collection2.find_one({"_id":user_id, "Status":"active", "permission":2})
#                 if check_user is not None:
#                     complaint_status = collection3.find_one({"Complaint ID":data['Complaint ID'], "Complaint Status":"Accepted"})
#                     if complaint_status is not None:
                        
#                         account_holder = check_user.get('Account Holder', None)
#                         user_complaint_type = complaint_status.get('Complaint Type', None)
                
#                         if account_holder != user_complaint_type:
#                             return {'res':'error', 'msg':f'Another admin can not accept the Complaint', 'code':402}
                        
#                         # Send OTP To CLient verify problem solve or Not.
                        
#                         generate_otp = str(random.randint(100000, 999999))
#                         userEmail = complaint_status['userDetails']['email']
#                         print("Emai is --->", userEmail)
#                         subject = f"Close Request OTP For Complaint No: {data['Complaint ID']}"
#                         send_otp = CloseRequest(userEmail, generate_otp, subject)
#                         print("Status of email is: ", send_otp)
#                         if send_otp.get('res') == "success":
#                             collection3.update_one({"Complaint ID":data['Complaint ID']},{"$set":{
#                                 "isClosedOtp":True,
#                                 "Close Request":{
#                                     "OTP": generate_otp,
#                                     "OtpDateTime": str(datetime.datetime.now())
#                                 }
#                             }})
                            
#                             # <-------------------  Notification code    ----------------->
                            
#                             print("<----------      Sending Notifications    ----->")
                            
#                             userID = complaint_status['userDetails']['ID']
#                             userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                            
#                             device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                            
#                             if device_token is not None:
#                                 title = "Otp Recieved"
#                                 body = f"Dear {userDetails['Name']}, please share OTP {generate_otp} with the technician to close your complaint."
#                                 notification_res = send_notification(device_token, title, body)
#                                 print("Response of Notification is: ", notification_res)
#                                 if notification_res.get("res") == "success":
#                                     Notification = {}
#                                     current_time = time.time()
#                                     Notification['_id'] = str(int(current_time * 1000))
                                    
#                                     Notification['title'] = title
#                                     Notification['body'] = body
#                                     Notification['dates'] = {
#                                         "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
#                                         "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
#                                         "dateTime": str(datetime.datetime.now())
#                                     }
#                                     Notification['Type'] = "Close Complaint OTP"
#                                     Notification['Status'] = notification_res
#                                     Notification['ComplaintID'] = data['Complaint ID']
#                                     Notification['UserID'] = str(userID)
#                                     collection4.insert_one(Notification)
#                                 else:
#                                     app.logger.info(f"Notification error, chek the Error")
#                             else:
#                                 app.logger.warning(f"Device token not Found for this compalint --> {data['Complaint ID']}")
                                
#                             app.logger.info(f"Complaint Closing Request Otp has been sent to User.")
#                             return {'res':data, 'msg':'OTP Successfully Send', 'code':200}
#                         else:
#                             return {'res':'error', 'msg':'Server Down, try after sometime.', 'code':404}
#                     else:
#                         return {'res':'error', 'msg':'Complaint Not found !', 'code':404}
#                 else:
#                     return {'res':'error', 'msg':'Permission denied', 'code':404}
#             else:
#                 app.logger.warning(f"Invalid token: {token}")
#                 return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
#         else:
#             return {'res':'error', 'msg':'Invalid Request', 'code':401}
#     except Exception as e:
#         app.logger.error(f'Error occurred: {e}',exc_info=True)
#         return {'res':'error', 'msg':'Something went wrong', 'code':404}

# <------------------------------         Old code end              -------------------------------->

# <---------------------------------                                         ---------------------------->
# <---------------------------------            New Updated Code             --------------------------->

# Calculate date after 2 days:

def after_two_days():
    now = datetime.datetime.now()
    
    date_after_two_days = datetime.datetime.now() + datetime.timedelta(days=2)
    return date_after_two_days.strftime('%d-%m-%Y')

# <------------------------              close complaint with user confirmation                ------------------>

@app.route("/CloseComplaint", methods=['POST'])
def AdmincloseComplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data -->", data)
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
        
                check_user = collection2.find_one({"_id":user_id, "Status":"active", "permission":2})
                if check_user is not None:
                    complaint_status = collection3.find_one({"Complaint ID":data['Complaint ID'], "Complaint Status":"Accepted"})
                    if complaint_status is not None:
                        
                        account_holder = check_user.get('Account Holder', None)
                        user_complaint_type = complaint_status.get('Complaint Type', None)
                
                        if account_holder != user_complaint_type:
                            return {'res':'error', 'msg':f'Another admin can not accept the Complaint', 'code':402}
                        
                        # Send Confirmation to Client to close complaint and verify problem solve or Not.
                        
                        userEmail = complaint_status['userDetails']['email']

                        subject = f"Close Request Confirmation For Complaint No: {data['Complaint ID']}"
                        confirmation_email = CloseRequest(userEmail, subject)
                        print("Status of email is: ", confirmation_email)
                        if confirmation_email.get('res') == "success":
                            
                            autoclose_date = after_two_days()
                            
                            print("the auto close date is: ", str(autoclose_date))
                            
                            collection3.update_one({"Complaint ID":data['Complaint ID']},{"$set":{
                                "isClosed":True,
                                "ComplaintCloseStatus":"Pending",
                                "Close Request":{
                                    "DateTime": str(datetime.datetime.now())
                                },
                                "auto_close_date":str(autoclose_date)
                            }})
                            
                            # <-------------------  Notification code    ----------------->
                            
                            print("<----------      Sending Notifications    ----->")
                            
                            userID = complaint_status['userDetails']['ID']
                            userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                            
                            device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                            
                            if device_token is not None:
                                title = "Complaint Resolved"
                                body = f"Dear {userDetails['Name']}, your complaint has been resolved. Please approve the closure via the app."
                                notification_res = send_notification(device_token, title, body)
                                print("Response of Notification is: ", notification_res)
                                if notification_res.get("res") == "success":
                                    Notification = {}
                                    current_time = time.time()
                                    Notification['_id'] = str(int(current_time * 1000))
                                    
                                    Notification['title'] = title
                                    Notification['body'] = body
                                    Notification['dates'] = {
                                        "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                        "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                        "dateTime": str(datetime.datetime.now())
                                    }
                                    Notification['Type'] = "Close Complaint"
                                    Notification['Status'] = notification_res
                                    Notification['ComplaintID'] = data['Complaint ID']
                                    Notification['UserID'] = str(userID)
                                    collection4.insert_one(Notification)
                                else:
                                    app.logger.info(f"Notification error, chek the Error")
                            else:
                                app.logger.warning(f"Device token not Found for this compalint --> {data['Complaint ID']}")
                                
                            app.logger.info(f"Complaint Closing Request has been sent to User.")
                            return {'res':data, 'msg':'Complaint Closing Request has been sent to User.', 'code':200}
                        else:
                            return {'res':'error', 'msg':'Something went wrong !', 'code':404}
                    else:
                        return {'res':'error', 'msg':'Complaint Not found !', 'code':404}
                else:
                    return {'res':'error', 'msg':'Permission denied', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':401}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}

    
# <========================     Verify OTP For Close Request (OLD Code)    ===================================>

# @app.route("/CloseComplaintVerifyOTP", methods=['GET', 'POST'])
# def CloseComplaintVerifyOTP():
#     try:
#         if request.method == "POST":
#             data = request.form.to_dict()
            
#             token = data.get('token')
#             if not token:
#                 return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
#             decoded_token = decode_jwt(token)
            
#             if decoded_token.get("response") == "success":
#                 user_id = str(decoded_token['data']['user_id'])
#                 print("User ID:", user_id)
            
#                 check_user = collection2.find_one({"_id":user_id, "Status":"active", "permission":2})
#                 if check_user is not None:
#                     complaint_status = collection3.find_one({"Complaint ID":data['Complaint ID'], "Complaint Status":"Accepted", "isClosedOtp":True, "TechnicianDetails.ID":user_id})
#                     # print("Complaint STatus: ", complaint_status)
#                     if complaint_status is not None:
#                         client_OTP = data.get("OTP")
#                         db_otp = complaint_status['Close Request']['OTP']
                        
#                         if client_OTP == db_otp:
#                             collection3.update_one({"Complaint ID":data['Complaint ID']},{"$unset":{
#                                 "Close Request":"",
#                                 "isClosedOtp": ""
#                             }})
#                             collection3.update_one({"Complaint ID":data['Complaint ID']},{"$set":{
#                                 "Complaint Status":"Completed",
#                                 "Close Request":{
#                                     "status":"Closed",
#                                     "verify":True,
#                                     "DateTime":str(datetime.datetime.now())
#                                 },
#                                 "completedDateTime":{
#                                     "Date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
#                                     "Time": str(datetime.datetime.now().strftime("%H:%M:%S")),
#                                     "DateTime": str(datetime.datetime.now()),
#                                     "Month":str(datetime.datetime.now().strftime("%B")),
#                                     "Year": str(datetime.datetime.now().strftime("%Y")),
#                                 }
#                             }})  
#                             subject = f"{data['Complaint ID']} Complaint Successfully Closed."
#                             userID = complaint_status['userDetails']['email']
#                             admin_name = complaint_status['TechnicianDetails']['Name']
#                             closingDate = str(datetime.datetime.now().strftime("%d %B %Y"))
#                             complaint_number = data['Complaint ID']
                            
#                             status_send = sendFeedBack(userID, subject, admin_name, closingDate, complaint_number)
                            
#                             # <------------------       Send Notification       ----------------->
                            
#                             userID = complaint_status['userDetails']['ID']
#                             userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
#                             device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                
#                             if device_token is not None:
#                                 title = "Complaint Successfully Completed"
#                                 body = f"Dear {userDetails['Name']}, Your Complaint No. {data['Complaint ID']} has been Successfully Completed by {admin_name}, Please share your feedback."
#                                 notification_res = send_notification(device_token, title, body)
#                                 # print("Response of Notification is: ", notification_res)
#                                 if notification_res.get("res") == "success":
#                                     Notification = {}
#                                     current_time = time.time()
#                                     Notification['_id'] = str(int(current_time * 1000))
                                    
#                                     Notification['title'] = title
#                                     Notification['body'] = body
#                                     Notification['dates'] = {
#                                         "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
#                                         "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
#                                         "dateTime": str(datetime.datetime.now())
#                                     }
#                                     Notification['Type'] = "Complaint Closed"
#                                     Notification['Status'] = notification_res
#                                     Notification['ComplaintID'] = data['Complaint ID']
#                                     Notification['UserID'] = str(userID)
#                                     collection4.insert_one(Notification)
#                                     app.logger.info(f"Notification has been sent to {userDetails['Name']}")
#                                 else:
#                                     app.logger.warning(f"Notification is not sent, check the error")
#                             else:
#                                 app.logger.warning(f"Device token not Found for this compalint --> {data['Complaint ID']}")
                            
#                             app.logger.info(f"Complaint Successfully Closed {complaint_status}")
#                             return {'res':'success', 'msg':'Complaint Successfully Closed.', 'code':200}
#                         else:
#                             app.logger.warning(f"Invalid OTP")
#                             return {'res':'error', 'msg':'Invalid OTP', 'code':400}
#                     else:
#                         app.logger.warning(f"permission denied, Account Status is Not Active")
#                         return {'res':'error', 'msg':'permission denied', 'code':400}
#                 else:
#                     return {'res':'error', 'msg':'permission denied', 'code':400}
#             else:
#                 app.logger.warning(f"Invalid token: {token}")
#                 return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
#         else:
#             app.logger.warning(f"Invalid Request")
#             return {'res':'error', 'msg':'Invalid Request', 'code':404}
#     except Exception as e:
#         app.logger.error(f'Error occurred: {e}',exc_info=True)
#         return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
    
# <--------------------------------         Code End         --------------------------------->

# <----------------------------                           ------------------------->
# <================        Approve or Rejected Complaints to close(user's code)        =====================>
# <----------------------------                           ------------------------->

@app.route("/CloseComplaintApproveUsers", methods=['GET', 'POST'])
def CloseComplaintApproveUsers():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            # token, complaint_id, ComplaintStatus=Completed/rejected, remarks
            
            user_complaint_status = data.get("ComplaintStatus", None)
            user_remarks = data.get("remarks", None)
            
            if user_complaint_status is None:
                return jsonify({'res': 'error', 'msg': 'Complaint ', 'code': 401})
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
                
                check_user = collection2.find_one({"_id":user_id, "Status":"active", "permission":3})
                if check_user is not None:
                    complaint_status = collection3.find_one({"Complaint ID":data['Complaint ID'], "Complaint Status":"Accepted", "isClosed":True, "userDetails.ID":user_id, "ComplaintCloseStatus":"Pending"})
                    print("Complaint STatus: ", complaint_status)
                    if complaint_status is not None:
                        
                        if user_complaint_status == "Completed":
                            collection3.update_one({"Complaint ID":data['Complaint ID']},{"$unset":{
                                "Close Request":"",
                                "isClosed": "",
                                "ComplaintCloseStatus":""
                            }})
                            
                            collection3.update_one({"Complaint ID":data['Complaint ID']},{"$set":{
                                "Complaint Status":"Completed",
                                "remarks":user_remarks,
                                "Close Request":{
                                    "status":"Closed",
                                    "verify":True,
                                    "DateTime":str(datetime.datetime.now())
                                },
                                "completedDateTime":{
                                    "Date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                    "Time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                    "DateTime": str(datetime.datetime.now()),
                                    "Month":str(datetime.datetime.now().strftime("%B")),
                                    "Year": str(datetime.datetime.now().strftime("%Y")),
                                },
                                "complaint_user_status":"Completed",
                                "User_complaints_status_dates": {
                                    "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                    "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                    "dateTime": str(datetime.datetime.now()),
                                    "Month":str(datetime.datetime.now().strftime("%B")),
                                    "Year": str(datetime.datetime.now().strftime("%Y")),
                                }
                                
                            }})  
                            subject = f"{data['Complaint ID']} Complaint Successfully Closed."
                            userID = complaint_status['userDetails']['email']
                            admin_name = complaint_status['TechnicianDetails']['Name']
                            closingDate = str(datetime.datetime.now().strftime("%d %B %Y"))
                            complaint_number = data['Complaint ID']
                            
                            status_send = sendFeedBack(userID, subject, admin_name, closingDate, complaint_number)
                            
                            # <------------------       Send Notification       ----------------->
                            
                            userID = complaint_status['userDetails']['ID']
                            userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                            device_token = userDetails.get("DeviceDetails", {}).get('device-token')
                
                            if device_token is not None:
                                title = "Complaint Successfully Completed"
                                body = f"Dear {userDetails['Name']}, Your Complaint No. {data['Complaint ID']} has been Successfully Completed by {admin_name}, Please share your feedback."
                                notification_res = send_notification(device_token, title, body)
                                # print("Response of Notification is: ", notification_res)
                                if notification_res.get("res") == "success":
                                    Notification = {}
                                    current_time = time.time()
                                    Notification['_id'] = str(int(current_time * 1000))
                                    
                                    Notification['title'] = title
                                    Notification['body'] = body
                                    Notification['dates'] = {
                                        "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                        "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                        "dateTime": str(datetime.datetime.now())
                                    }
                                    Notification['Type'] = "Complaint Closed"
                                    Notification['Status'] = notification_res
                                    Notification['ComplaintID'] = data['Complaint ID']
                                    Notification['UserID'] = str(userID)
                                    collection4.insert_one(Notification)
                                    app.logger.info(f"Notification has been sent to {userDetails['Name']}")
                                else:
                                    app.logger.warning(f"Notification is not sent, check the error")
                            else:
                                app.logger.warning(f"Device token not Found for this compalint --> {data['Complaint ID']}")
                            
                            app.logger.info(f"Complaint Successfully Closed {complaint_status}")
                            return {'res':'success', 'msg':'Complaint Successfully Closed.', 'code':200}
                        
                        elif user_complaint_status == "Rejected":
                            
                            collection3.update_one({"Complaint ID":data['Complaint ID']},{"$unset":{
                                "Close Request":"",
                                "isClosed": "",
                                "ComplaintCloseStatus":""
                            }})
                            
                            collection3.update_one({"Complaint ID":data['Complaint ID']},{"$set":{
                                "complaint_user_status":"Rejected",
                                "remarks":user_remarks,
                                "User_complaints_status_dates": {
                                    "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                    "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                    "dateTime": str(datetime.datetime.now()),
                                    "Month":str(datetime.datetime.now().strftime("%B")),
                                    "Year": str(datetime.datetime.now().strftime("%Y")),
                                }
                            }})
                            
                            reason = data.get("Reason", None)
                            admin_details = complaint_status.get("TechnicianDetails")
                            admin_ID = admin_details.get("ID")
                            admin_device_token = collection2.find_one({"_id":admin_ID})
                            admin_device_token_id = admin_device_token.get("DeviceDetails", {}).get('device-token')
                            
                            if admin_device_token_id is not None:
                                title = "Complaint Rejected User"
                                body = f"Dear {admin_device_token['Name']}, Complaint No. {data['Complaint ID']} has been Rejected, Please check this Complaint."
                                notification_res = send_notification(admin_device_token_id, title, body)
                                # print("Response of Notification is: ", notification_res)
                                if notification_res.get("res") == "success":
                                    Notification = {}
                                    current_time = time.time()
                                    Notification['_id'] = str(int(current_time * 1000))
                                    
                                    Notification['title'] = title
                                    Notification['body'] = body
                                    Notification['dates'] = {
                                        "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                        "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                        "dateTime": str(datetime.datetime.now())
                                    }
                                    Notification['Type'] = "Complaint Rejected by user"
                                    Notification['Status'] = notification_res
                                    Notification['ComplaintID'] = data['Complaint ID']
                                    Notification['UserID'] = str(admin_ID)
                                    collection4.insert_one(Notification)
                                    app.logger.info(f"Notification has been sent to {admin_device_token['Name']}")
                                else:
                                    app.logger.warning(f"Notification is not sent, check the error")
                            else:
                                app.logger.warning(f"Device token not Found for this Admin --> {admin_device_token['Name']}")
    
                            app.logger.warning(f"Complaint Approved Api Running successfully.")
                            return {'res':'success', 'msg':'Complaint successfully Rejected.', 'code':200}
                    else:
                        app.logger.warning(f"permission denied, Complaint Status is Not Found")
                        return {'res':'error', 'msg':'permission denied', 'code':400}
                else:
                    return {'res':'error', 'msg':'permission denied', 'code':400}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}


# <--------------------------           Code END        ---------------------------->



# <--------------------------------                     --------------------------------------->
# <----------------------------      All User's Pending Complaints for Approval     --------------------------------->
# <--------------------------------                     --------------------------------------->

@app.route("/UsersPendingComplaints", methods=['POST'])
def ApprovalPendingComplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_user is None:
                    return jsonify({'res': 'error', 'msg': 'This Account is Not Active, please contact admin', 'code': 401})
                
                Pending_approval = collection3.find({'userDetails.ID':user_id, "ComplaintCloseStatus":"Pending"})
                
                return {'res':Pending_approval, 'mgs':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})         
        else:
            app.logger.warning("Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        return {'res':'error', 'msg':"Something went wrong", "code":404}
    
# <--------------------------------                     --------------------------------------->
# <--------------------------------      Code END               --------------------------------------->
# <--------------------------------                     --------------------------------------->


# <--------------------------------------  Get  Accept Complaint Details              ---------------------------->

@app.route("/Getacceptedcomplaints", methods=["GET", "POST"])
def Getacceptedcomplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                
                if check_user is None:
                    return jsonify({'res': 'error', 'msg': 'This Account is Not Valid', 'code': 401})
                    
                if check_user.get("permission") == 3:
                    complaint_data = list(collection3.find({"userDetails.ID":user_id, "Complaint Status":"Accepted"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                elif check_user.get("permission") == 2:
                    complaint_data = list(collection3.find({"TechnicianDetails.ID":user_id, "Complaint Status":"Accepted"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                elif check_user.get("permission") == 1:
                    complaint_data = list(collection3.find({"Complaint Status":"Accepted"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                else:
                    return {'res':'error', 'msg':'User Not Found', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning("Invalid Request")
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}

# <--------------------------------     GET Completed Complaints    ---------------------->

@app.route("/getCompletedComplaints", methods=['GET','POST'])
def CompletedComplaints():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
                
                if check_user.get("permission") == 3:
                    complaint_data = list(collection3.find({"userDetails.ID":user_id, "Complaint Status":"Completed"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                elif check_user.get("permission") == 2:
                    complaint_data = list(collection3.find({"TechnicianDetails.ID":user_id, "Complaint Status":"Completed"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                elif check_user.get("permission") == 1:
                    complaint_data = list(collection3.find({"Complaint Status":"Completed"},{"_id":0}).sort("_id", -1))
                    return {'res':complaint_data, 'msg':'Success', 'code':200}
                else:
                    return {'res':'error', 'msg':'User Not Found', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
        
# <---------------------------      All Notifications           ------------------------->

@app.route("/getallnotifications",methods=['POST'])
def getallnotifications():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                check_account = collection2.find_one({"_id":user_id},{"_id":0})
                
                if check_account.get("Role") == "SuperAdmin":
                    notifications = list(collection4.find(sort=[("_id", -1)]))
                else:
                    notifications = list(collection4.find({"UserID": user_id}).sort("_id", -1))
                    
                return {'res':notifications, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
        
# <------------------------------                         --------------------------->
# <------------------------------       Add Feedback Data      --------------------------->
# <------------------------------                         --------------------------->

@app.route("/addfeedback",methods=['GET', 'POST'])
def addfeedback():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)
            
                current_time = time.time()
                new_feedback_id = int(current_time * 1000)
                complaint_admin = collection3.find_one({"Complaint ID":data['ComplaintID']},{"TechnicianDetails":1, "_id":0})
                
                collection5.update_one({"_id":str(new_feedback_id)},{"$set":{"UserID": user_id,
                    "Feedback": data['feedback'],
                    "Ratings": data['Ratings'],
                    "ComplaintID": data['ComplaintID'],
                    "AdminID":complaint_admin['TechnicianDetails']['ID'],
                    "dateTime":{
                        "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                        "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                        "dateTime": str(datetime.datetime.now()),
                    }
                    }},upsert=True)
                collection3.update_one({"Complaint ID":data['ComplaintID']},{"$set":{
                    "feedback_status":True
                }})
                return {'res':'success', 'msg':'Feedback Successfully submitted', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
# <===========================          feedback data         ==============================>

@app.route("/getfeedbackData", methods=['GET','POST'])
def getfeedbackData():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data ",data)
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                userid = str(decoded_token['data']['user_id'])
                
                check_account = collection2.find_one({"_id":userid},{"_id":0, "Role":1})
                print("Account status: ", check_account)
                
                if check_account.get("Role") == "admin":
                    user_type = "AdminID"
                else:
                    user_type = "UserID"
                    
                feedback_data = list(collection5.find({user_type:userid}))
                return {"res":feedback_data, 'msg':'success', 'code':200}  
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
            return {}
        else:
            return {}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
    
# <=====================        Read Notification       ===================>

@app.route("/readnotificationapi", methods=['GET', 'POST'])
def readnotificationapi():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data ", data)
            collection4.update_one({"_id":data['_id']},{"$set":{
                "read_notification":true,
                "dates":{
                    "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                    "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                    "dateTime": str(datetime.datetime.now()),
                }
            }})
            app.logger.info("Notification status Updated")
            return {'res':"success", 'msg':'Notification read status Updated', 'code':200}
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}',exc_info=True)
        return {'res':'error', 'msg':'Something went wrong', 'code':404}
        

# <=============================            Update Password           ===========================>

@app.route("/updatepassword", methods=['GET', 'POST'])
def AccountPasswordUpdate():
    try:
        if request.method == "POST":
            user = request.form.to_dict()
        
            token = user.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            print("Decoded Token Data:", decoded_token)

            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("User ID:", user_id)

                # Check user in MongoDB
                db_user = collection2.find_one({"_id": user_id, "Status": 'active'})
                print("Database user:", db_user)

                if db_user is None:
                    return jsonify({'res': 'error', 'msg': 'User not found or inactive', 'code': 404})

                # Validate password fields
                new_password = user.get('password')
                confirm_password = user.get('confirm_password')

                if not new_password or not confirm_password:
                    return jsonify({'res': 'error', 'msg': 'Password fields are required', 'code': 400})

                if new_password != confirm_password:
                    app.logger.error("Password does not match")
                    return jsonify({'res': 'error', 'msg': 'Password does not match', 'code': 400})

                # Update password in database
                collection2.update_one({"_id": user_id}, {"$set": {
                    "password": new_password,
                    "updatePassword": True,  # Fixed capitalization
                    "passwordModifyDates": {
                        "date": datetime.datetime.now().strftime("%d-%m-%Y"),
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "dateTime": str(datetime.datetime.now()),
                    }
                }})

                app.logger.info("Account Password Updated Successfully")
                return jsonify({'res': 'success', 'msg': 'Password successfully updated', 'code': 200})
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning("Invalid request method for UpdatePassword")
            return jsonify({'res': 'error', 'msg': 'Invalid request', 'code': 405})

    except Exception as e:
        print(traceback.format_exc())
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
    
    
# <==============================    Profile Details    =========================>


@app.route("/ProfileDetails", methods=['GET','POST'])
def ProfileDetails():
    try:
        if request.method == "POST":
            user = request.form.to_dict()
        
            token = user.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                profile_details = collection2.find_one({"_id":user_id}, {"Name":1, "email":1, "Phone Number":1, "password":1, "House Number":1, "gender":1, "Branch":1, "Designation":1, "landmark":1})
                return {'res':profile_details, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
    
    
# <====================================     Complaint Details (Super-admin)     ==================================>

@app.route("/checkComplaintsDetails", methods=['POST'])
def checkComplaintsDetails():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                complaint_type = data.get('Complaint Type')
                complaint_status = data.get('Complaint Status')
                
                complaintsDetails = list(collection3.find({'Complaint Type': complaint_type, 'Complaint Status': complaint_status}).sort("_id", -1))
                return {'res': complaintsDetails, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
    
# <=================================           Number of Users (Superadmins & Users)            =========================> 

@app.route("/totalnumberUsers", methods=['GET','POST'])
def AccountsNumbers():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data is: ", data)
            
            token = data.get('token')
            
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                check_user = collection2.find_one({"_id":user_id}, {"permission":1})
                if check_user:
                    if check_user.get('permission') == 2:
                        total_users = len(list(collection2.find({'Role':'user', 'permission':3})))
                        return {'res':{'Users':total_users}, 'msg':'success', 'code':200}
                    elif check_user.get('permission') == 1:
                        total_users = len(list(collection2.find({'Role':'user', 'permission':3})))
                        total_admins = len(list(collection2.find({'Role':'admin', 'permission':2})))
                        return {'res':{'Users':total_users, 'Admins':total_admins}, 'msg':'success', 'code':200}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
    
    
        
# <================================     Rejects Complaints API            =================================>

@app.route("/ComplaintRejected", methods=['GET', 'POST'])
def ComplaintRejected():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            complaint_ID = data.get('Complaint ID')
            Rejected_reason = data.get('Reason')
            
            if not complaint_ID:
                return jsonify({'res':'error', 'msg':'complaint ID missing', 'code':401})
            
            if not Rejected_reason:
                return jsonify({'res':'error', 'msg':'Rejected reason missing', 'code':401})
            
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                check_admin = collection2.find_one({"_id":user_id, "Status":"active"})
                if check_admin is not None:
                    check_complaint_type = collection3.find_one({"_id":complaint_ID, "Complaint Status":{"$ne": "Completed"}},{"Complaint Type":1, "_id":1, "userDetails":1, "Complaint Status":1})
                    
                    if check_complaint_type is not None:  
                
                        if check_complaint_type.get("Complaint Status") == "Rejected":
                            return jsonify({'res':'error', 'msg':'Complaint is already Rejected', 'code':402})
                        
                        collection3.update_one({"_id": complaint_ID},{"$set":{
                            'Complaint Status': 'Rejected',
                            'Complaint_rejected': True,
                            'Rejected_reason' : Rejected_reason,
                            'Rejected_by': check_admin.get("Name"),
                            'TechnicianDetails':{
                                "ID": check_admin.get('_id'),
                                "Name": check_admin.get("Name"),
                                "email": check_admin.get("email"),
                                "adminType": check_admin.get("Account Holder"),
                                "Phone": check_admin.get("Phone Number"),
                                "Reason":data.get("Reason")
                            },
                            'RejectedDates':{
                                "Date":str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                "Time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                "DateTime":str(datetime.datetime.now()),
                                "Month":str(datetime.datetime.now().strftime("%B")),
                                "Year": str(datetime.datetime.now().strftime("%Y")),
                            }   
                        }})
                        
                        userID = check_complaint_type['userDetails']['ID']
                        userDetails = collection2.find_one({"_id":str(userID)},{"DeviceDetails":1, "Name":1})
                        device_token = userDetails['DeviceDetails']['device-token']
                        
                        title = "Complaint Rejected"
                        body = f"Dear {userDetails['Name']}, Your Complaint No. {complaint_ID} has been Rejected."
                        notification_res = send_notification(device_token, title, body)
                        
                        if notification_res.get("res") == "success":
                            Notification = {}
                            current_time = time.time()
                            Notification['_id'] = str(int(current_time * 1000))
                            
                            Notification['title'] = title
                            Notification['body'] = body
                            Notification['dates'] = {
                                "date": str(datetime.datetime.now().strftime("%d-%m-%Y")),
                                "time": str(datetime.datetime.now().strftime("%H:%M:%S")),
                                "dateTime": str(datetime.datetime.now())
                            }
                            
                            Notification['Type'] = title
                            Notification['Status'] = notification_res
                            Notification['ComplaintID'] = complaint_ID
                            Notification['UserID'] = str(userID)
                            collection4.insert_one(Notification)
                        else:
                            app.logger.warning(f"Notification is not send to {userDetails['Name']}, check error: {notification_res}")
                            
                        return {'res':'success', 'msg':'Complaint Successfully Rejected', 'code':200}
                    else:
                        app.logger.error(f"Complaint Not Found at :{str(datetime.datetime.now())} & Details are: {data}")
                        return {'res':'error', 'msg':'Complaint not found', 'code':404}
                else:
                    app.logger.error(f"Admin Not Found at :{str(datetime.datetime.now())} & Details are: {data}")
                    return {'res':'error', 'msg':'Admin not Valid', 'code':400}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})  
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})        
            
# <================================         Get Rejected Complaints Data          =================================>

@app.route("/getRejectedComplaints", methods=['GET','POST'])
def getRejectedComplaintsDetails():
    try:
        if request.method == "POST":
            data = request.form.to_dict()   
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                check_user = collection2.find_one({"_id":user_id, "Status":"active"})
            
                if check_user is not None:
                    rejected_complaints = {}
                    if check_user.get('Role') == "user" and check_user.get('permission') == 3:
                        rejected_complaints = list(collection3.find({"userDetails.ID":user_id, 'Complaint Status':'Rejected'}).sort("_id", -1))
                    elif check_user.get('Role') == "admin" and check_user.get('permission') == 2:
                        rejected_complaints = list(collection3.find({'Complaint Status':'Rejected', 'TechnicianDetails.ID':user_id}).sort("_id", -1))
                    elif check_user.get('Role') == "SuperAdmin" and check_user.get('permission') == 1:
                        rejected_complaints = list(collection3.find({'Complaint Status':'Rejected'}).sort("_id", -1))
                    app.logger.info(f"Rejected Api status working")
                    return jsonify({'res':rejected_complaints, 'msg':'success', 'code':200})
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})  
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})     
        
# <================================     Reports Create API            =================================>

@app.route("/CreateAdminReports", methods=['POST', 'GET'])
def CreateReports():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data is: ", data)
            
            token = data.get('token')
        
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                from_date = data.get('From')
                to_date = data.get("To")

                complaints_details = list(collection3.find({
                    'Complaint Status': "Completed",
                    "completedDateTime.Date": {"$gte": from_date, "$lte": to_date}
                }))
                
                if complaints_details is None or complaints_details == []:
                    return {'res':'success', 'msg':'No Complaints Found', 'code':404}

                # ComplaintID, Username,  Quarter Number, Complaint-desc AdminName, Resolved Date
                
                userDetails = collection2.find_one({"_id":user_id})
                super_admin = collection2.find_one({"Account Holder":"SuperAdmin", "permission":1},{"Name":1, "email":1})
                   
                Reports = []
                for i in complaints_details:
                    reports_data = {}
                    reports_data['ComplaintID'] = i['Complaint ID']
                    reports_data['Name'] = i['userDetails']['name']
                    reports_data['Address'] = i['userDetails']['address']
                    reports_data['Complaint'] = i['Complaint Name']
                    reports_data['Admin'] = i['TechnicianDetails']['Name']
                    reports_data['ResolvedDate'] = i['completedDateTime']['Date']
                    Reports.append(reports_data)
                
                name = userDetails['Name']
                branch = userDetails['Account Holder']
                authority_name = super_admin['Name']
                reportname = f"{name}.pdf"
                
                report = generate_admin_pdf(Reports, name, branch, authority_name, reportname)
                if report.get('res') == "success":
                    reports_data = {
                        'Name':name,
                        'Branch':branch,
                        'AccountID': userDetails['_id'],
                        'AuthorityName': authority_name,
                        'ReportName':reportname,
                        'DateTime': str(datetime.datetime.now().strftime('%d-%m-%Y %H:%M')),
                        'ReportsData':Reports
                    }
                    collection6.insert_one(reports_data)
                    app.logger.info(f"Report Successfully Generated By {name}")
                    return {'res':'success','msg':reportname, 'code':200} 
                else:
                    app.logger.warning(f"Something went wrong in Reports check error {report}")
                    return {'res':'error', 'msg':'Something went Wrong', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500}) 
    

# <=====================        User's Reports generate Code        ===========================>
    
@app.route("/Usergeneratereports", methods=['GET', 'POST'])
def GenerateUsersReports():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data is: ", data)
            
            token = data.get('token')
        
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                print("user ID: ", user_id)
                
                from_date = data.get('From')
                to_date = data.get("To")
                
                print("From Date is: ", from_date)
                print("To Date is: ", to_date)

                complaints_details = list(collection3.find({
                    'Complaint Status': "Completed",
                    'userDetails.ID':user_id,
                    f"completedDateTime.Date": {"$gte": from_date, "$lte": to_date}
                }))
                
                print("Complaints Details: ", complaints_details)
                
                if complaints_details is None or complaints_details == []:
                    return {'res':'success', 'msg':'No Complaints Found', 'code':404}
                
                # Profile --> Name,Designation, Branch, Active-Date

                # ComplaintID, Complaint-desc,  Resolved By, Time taken,  Resolved Date
                
                profile_details = collection2.find_one({"_id":user_id})
                # super_admin = collection2.find_one({"Account Holder":"SuperAdmin", "permission":1},{"Name":1, "email":1})
                   
                Reports = []
                for i in complaints_details:
                    reports_data = {}
                    reports_data['ComplaintID'] = i['Complaint ID']
                    reports_data['Name'] = i['userDetails']['name']
                    reports_data['Description'] = i['Complaint Name']
                    reports_data['Resolved_by'] = i['TechnicianDetails']['Name']
                    reports_data['time_taken'] = i['completion_time']
                    
                    reports_data['ResolvedDate'] = i['completedDateTime']['Date']
                    Reports.append(reports_data)
                
                name = profile_details['Name']
                designation = profile_details.get('Designation', '')
                branch = profile_details['Account Holder']
                quarter_number = profile_details.get("Address", None)
                account_date = profile_details.get('Account Creation Date','')
                print("Account Date is: ", account_date)
                Active_date = account_date.get('Date', '')
                print("Active Date is: ", Active_date)
                account_holder_id = profile_details.get('_id', '')
                
                reportname = f"{name}.pdf"
                
                report = generate_user_pdf(Reports, name, branch, designation, quarter_number, Active_date,  reportname)
                if report.get('res') == "success":
                    reports_data = {
                        'Name':name,
                        'Branch':branch,
                        'AccountID': account_holder_id,
                        'AuthorityName': None,
                        'ReportName':reportname,
                        'DateTime': str(datetime.datetime.now().strftime('%d-%m-%Y %H:%M')),
                        'ReportsData':Reports,
                    }
                    collection6.insert_one(reports_data)
                    app.logger.info(f"Report Successfully Generated By {name}")
                    return {'res':'success','msg':reportname, 'code':200} 
                else:
                    app.logger.warning(f"Something went wrong in Reports check error {report}")
                    return {'res':'error', 'msg':'Something went Wrong', 'code':404}
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':404}
    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})

# <----------------------------     Download Reports API    --------------------------> 

@app.route("/downloadReports", methods=['GET', 'POST'])
def DownloadReports():
    try:
        if request.method == "POST":
            data = request.get_json()
            
            token = data.get('token')
            file_name = data.get('filename')

            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                app.logger.info(f"File {file_name} successfully downloaded by User {user_id}.")
                return send_from_directory(directory=app.config['Records'], path=file_name, as_attachment=True)

            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            app.logger.warning(f"Invalid Request")
            return jsonify({'res': 'error', 'msg': 'Invalid Request', 'code': 400})

    except Exception as e:
        app.logger.error(f"Error in DownloadReports: {str(e)}")
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
    
    
# <==============================                                               =================================>   
# <==============================               Update Accept Complaint-app             =================================>   
# <==============================                                               =================================>   

@app.route("/updateacceptComplaint", methods=['GET', 'POST'])
def updateAcceptComplaintsaccept():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})

            decoded_token = decode_jwt(token)
            if decoded_token.get("response") == "success":
                user_id = str(decoded_token['data']['user_id'])
                
                admin_details = collection2.find_one({"_id":user_id},{"_id":1, "Name":1, "email":1, "Phone Number":1, "Account Holder":1})
                
                if admin_details is None:
                    return {'res':'error', 'msg':'account is not valid', 'code':402}
                
                complaint_id = data.get('Complaint ID', None)
                completion_time = data.get('completion_time', None)
                
                admin_name = data.get('admin_name', None)
                admin_phone = data.get('admin_phone', None)
                
                current_date = datetime.datetime.now().strftime("%d-%m-%Y")
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                
                complaints_data = collection3.find_one({"Complaint ID":complaint_id, "Complaint Status":"Accepted"})
                
                if complaints_data is None:
                    return {'res':'error', 'msg':'Complaint Not found', 'code':402}
                
                account_holder = admin_details.get('Account Holder', None)
                user_complaint_type = complaints_data.get('Complaint Type', None)
                
                if account_holder != user_complaint_type:
                    return {'res':'error', 'msg':f'Another admin can not accept the Complaint', 'code':402}
                
                current_time_id = time.time()
                            
                complaints_data['_id'] = str(int(current_time_id * 10000))
                complaints_data['UpdatedDetails'] = {
                    "new_completion_time": completion_time,
                    'admin_name_new': admin_name,
                    'admin_phone_Number': admin_phone,
                    'Date':current_date,
                    "Time":current_time 
                }
                
                collection31.insert_one(complaints_data)
                
                collection3.update_one({"Complaint ID":complaint_id, "Complaint Status":"Accepted"},{
                    "$set":{
                        "completion_time": completion_time,
                        "TechnicianDetails.ID": user_id, 
                        "TechnicianDetails.Name": admin_name, 
                        "TechnicianDetails.Phone Number": admin_phone,
                        
                        "acceptedDateTime":{
                            "DateTime": str(datetime.datetime.now()),
                            "Date": str(current_date),
                            "Time": str(current_time),
                            "Month":str(datetime.datetime.now().strftime("%B")),
                            "Year": str(datetime.datetime.now().strftime("%Y")),
                        }
                    }
                })
                 
                app.logger.info(f"Complaint Details Successfully Updated by {admin_name} for Complaint number is: {complaint_id}")
                return jsonify({'res': 'success', 'msg': 'Complaint Details Successfully Updated.', 'code': 200})

            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})  
        else:
            app.logger.warning(f"Invalid Request")
            return jsonify({'res': 'error', 'msg': 'Invalid Request', 'code': 400})
            
    except Exception as e:
        app.logger.error(f"Error : {str(e)} and {traceback.format_exc()}")
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 500})
        
# <==============================                                        =================================>    
# <==============================           DashBoard API's              =================================>
# <==============================                                        =================================>   

# <==============================               DashboardComplaintsData             =================================>   

@app.route("/DashboardComplaintsData", methods=['GET','POST'])
def DashboardComplaintsData():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            token = data.get('token')
            if not token:
                return jsonify({'res': 'error', 'msg': 'Token is missing', 'code': 401})
            
            decoded_token = decode_jwt(token)
            
            if decoded_token.get("response") == "success":
                user_id = decoded_token['data']['user_id']
                
                check_user = collection2.find_one({"_id": str(user_id), "Status": "active"},{"Account Holder": 1, "_id": 1, "Name": 1, "permission": 1})
                
                if check_user is not None:
                    if check_user.get("permission") == 1:
                        total_complaints = {}

                        if data.get('type') == "today":

                            today_date = datetime.datetime.now().strftime("%d-%m-%Y")  
                            
                            open_complaints = list(collection3.find({"Complaint Status": "Open", "complaintRegisterDates.Date": today_date}))
                            approved_complaints = list(collection3.find({"Complaint Status": "Accepted", "acceptedDateTime.Date": today_date}))
                            completed_complaints = list(collection3.find({"Complaint Status": "Completed", "completedDateTime.Date": today_date}))
                            rejected_complaints = list(collection3.find({"Complaint Status": "Rejected", "RejectedDates.Date": today_date}))

                            total_complaints['Open Complaints'] = len(open_complaints)
                            total_complaints['Approved Complaints'] = len(approved_complaints)
                            total_complaints['Completed Complaints'] = len(completed_complaints)
                            total_complaints['Rejected Complaints'] = len(rejected_complaints)

                        elif data.get('type') == "month":
                            
                            current_month = str(datetime.datetime.now().strftime("%B"))
                            current_year = str(datetime.datetime.now().strftime("%Y"))

                            open_complaints = list(collection3.find({
                                "Complaint Status": "Open", 
                                "complaintRegisterDates.Month": current_month,
                                "complaintRegisterDates.Year": current_year
                            }))
                        
                            approved_complaints = list(collection3.find({
                                "Complaint Status": "Accepted",
                                "acceptedDateTime.Month": current_month,
                                "acceptedDateTime.Year": current_year,
                                
                            }))
                            
                            completed_complaints = list(collection3.find({
                                "Complaint Status": "Completed", 
                                "completedDateTime.Month": current_month,
                                "completedDateTime.Year": current_year,
                            }))
                            
                            rejected_complaints = list(collection3.find({
                                "Complaint Status": "Rejected", 
                                "RejectedDates.Month": current_month,
                                "RejectedDates.Year": current_year,
                            }))

                            total_complaints['Open Complaints'] = len(open_complaints)
                            total_complaints['Approved Complaints'] = len(approved_complaints)
                            total_complaints['Completed Complaints'] = len(completed_complaints)
                            total_complaints['Rejected Complaints'] = len(rejected_complaints)
                    
                        else:
                            open_complaints = list(collection3.find({"Complaint Status": "Open"}))
                            approved_complaints = list(collection3.find({"Complaint Status": "Accepted"}))
                            completed_complaints = list(collection3.find({"Complaint Status": "Completed"}))
                            rejected_complaints = list(collection3.find({"Complaint Status": "Rejected"}))

                            total_complaints['Open Complaints'] = len(open_complaints)
                            total_complaints['Approved Complaints'] = len(approved_complaints)
                            total_complaints['Completed Complaints'] = len(completed_complaints)
                            total_complaints['Rejected Complaints'] = len(rejected_complaints)

                        return jsonify({'res': total_complaints, 'msg': 'success', 'code': 200})
                    else:
                        return jsonify({'res': "error", 'msg': 'Token is not valid', 'code': 400})
            else:
                app.logger.warning(f"Invalid token: {token}")
                return jsonify({'res': 'error', 'msg': 'Invalid token', 'code': 402})
        else:
            return jsonify({'res': 'error', 'msg': 'Invalid Request', 'code': 404})

    except Exception as e:
        app.logger.error(f'Error occurred: {e}', exc_info=True)
        return jsonify({'res': 'error', 'msg': "Something went wrong", 'code': 404})

# <==============================              Open Complaints Page             =================================>  

@app.route("/OpenComplaints")
def OpenComplaintspage():
        if session.get('access_token'):
            current_month = datetime.datetime.now().strftime("%B")
            current_year = datetime.datetime.now().strftime("%Y")
            openComplaints = list(collection3.find({'Complaint Status':'Open', 'complaintRegisterDates.Month':str(current_month), 'complaintRegisterDates.Year':str(current_year)}).sort("_id", -1))
            return render_template("AdminFolder/openComplaints.html", token=session['access_token'], OpenComplaints=openComplaints)
        else:
            return render_template("login.html")
 
# <==============================              Approved Complaints Page             =================================>

@app.route("/ApprovedComplaints")
def ApprovedComplaintspage():
    if session.get('access_token'):
        current_month = datetime.datetime.now().strftime("%B") # "acceptedDateTime.Month":str(current_month)
        current_year = datetime.datetime.now().strftime("%Y")
        approved_complaints = list(collection3.find({'Complaint Status':'Accepted', "acceptedDateTime.Month":str(current_month), "acceptedDateTime.Year":str(current_year)}).sort("_id", -1))
        return render_template("AdminFolder/approved.html", token=session['access_token'], approvedcomplaints=approved_complaints)
    else:
        return render_template("login.html")
    
   
# <==============================              Completed Complaints Page             =================================>  

@app.route("/completedcomplaintsdata") 
def CompletedComplaintspage():  
    if session.get('access_token'):
        current_month = datetime.datetime.now().strftime("%B") # "completedDateTime.Month":str(current_month)
        current_year = datetime.datetime.now().strftime("%Y")
        completed_complaints = list(collection3.find({'Complaint Status':'Completed', "completedDateTime.Month":str(current_month), "completedDateTime.Year":str(current_year)}).sort("_id", -1))
        return render_template("AdminFolder/Complete.html", token=session['access_token'], completed=completed_complaints)
    else:
        return render_template("login.html")
 
# <==============================              Rejected Complaints Page             =================================>   

@app.route("/rejectedComplaintsdata")
def RejectedComplaintspage():
    if session.get('access_token'):
        current_month = datetime.datetime.now().strftime("%B")
        current_year = datetime.datetime.now().strftime("%Y")
        rejected_complaints = list(collection3.find({'Complaint Status':'Rejected', 'RejectedDates.Month':str(current_month), 'RejectedDates.Year':str(current_year)}).sort("_id", -1))
        return render_template("AdminFolder/RejectedComplaints.html", token=session['access_token'], rejected=rejected_complaints)
    else:
        return render_template("login.html")

# <==============================       feedback graph api     =================================>


@app.route("/feedbackgraphdata", methods=['GET', 'POST'])
def feedbackgraphdata():
    
    from collections import defaultdict
    
    if session.get('access_token'):
        try:
            if request.method == "GET":
                feedbacks = list(collection5.find({}))

                all_feedbacks = []
                feedback_summary = defaultdict(lambda: {"total_ratings": 0, "count": 0})

                for i in feedbacks:
                    complaint_type = collection3.find_one({"_id": i['ComplaintID']}, {"Complaint Type": 1})
                    
                    i['ComplaintType'] = complaint_type.get('Complaint Type', 'Unknown') if complaint_type else "Unknown"
                    
                    all_feedbacks.append(i)

                    complaint_type_name = i['ComplaintType']
                    feedback_summary[complaint_type_name]["total_ratings"] += float(i['Ratings'])
                    feedback_summary[complaint_type_name]["count"] += 1
                
                admins = list(feedback_summary.keys())
                average_ratings = [
                    round(data["total_ratings"] / data["count"], 2) for data in feedback_summary.values()
                ]                    
                return jsonify({'res': 'success', 'code': 200, 'data': {'Admins': admins, "Average_Ratings": average_ratings}})
            
            return jsonify({'res': 'error', 'msg': 'Invalid Request', 'code': 402})

        except Exception as e:
            print('Error:', traceback.format_exc())
            return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 404})
    
    return render_template("login.html")
    
# <==============================       Forget Password Page     =================================>

@app.route("/forgetpassword", methods=['GET', 'POST'])
def forgetpasswordPage():
    return render_template("forget.html")


# <==============================       Forget  API     =================================>

@app.route("/checkUseraccountisvalid", methods=['GET', 'POST'])
def userAccountisvalid():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data is: ", data)
            check_email = collection2.find_one({"email":data.get('Email')})
            
            if check_email is None:
                return {'res':'error', 'msg':'Email-id is not Registered, please check', 'code':404}
            
            if check_email:
                otp_number = str(random.randint(100000, 999999))
                print('OTP Number is: ', otp_number)
                user_email = data.get('Email')
                
                forget_otpmail = send_otp_email(user_email, otp_number)
                
                print("response is: ", forget_otpmail)
                
                if forget_otpmail == True:
                    collection2.update_one({'email':data.get('Email')},{"$set":{
                        'forget_OTP':otp_number,
                    }})
                    app.logger.info(f"Forget Password Request Successfully Sent to {user_email}")
                    return {'res':'success', 'msg':user_email, 'code':200}
                else:
                    return {'res':'error', 'msg':"Something went Wrong, try after sometime", 'code':404}
            else:
                return {'res':'error', 'msg':'Account is not Registered', 'code':404}
        else:
            return {'res':'error', 'msg':'Invalid Request', 'code':400}    
    except Exception as e:
        print('Error:', traceback.format_exc())
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 404})
    
# <==============================       OTP Page     =================================>

@app.route("/CheckOtpvalidation", methods=['GET'])
def OtpValidationPage():
    if request.method == "GET":
        data = request.args.get('Usermail', None)
        print("Data is: ", data)
        return render_template("Verifyotp.html", user=data)
      
# <==============================       OTP Validation check otp API     =================================>

@app.route('/verifyuserOtpvalidate', methods=['POST'])
def verifyuserOtpvalidate():
    try:
        
        if request.method == "POST":
            data = request.form.to_dict()
            
            email = data.get('email', None)
            if email is None:
                return {'res':'error', 'msg':'session Timeout', 'code':402}
            
            print("Data is: ", data)
            
            forget_OTP = data.get('forget_OTP')
            
            # Email, forget_OTP
            check_otp = collection2.find_one({'email':email, 'forget_OTP':forget_OTP})
            if check_otp:
                forget_otp_db = check_otp.get('forget_OTP')
                print("The Db otp is: ", forget_otp_db)
                if forget_otp_db == forget_OTP:
                    print("OTP MAtched .....")
                    collection2.update_one({"email":email},{"$unset":{
                        "forget_OTP":""
                    }})
                    app.logger.info(f"Password Successfully Forget {datetime.datetime.now()}")
                    return{'res':'success', 'msg':'OTP Successfully Verified', 'code':200}
                else:
                    app.logger.warning({f"Otp is not valid, {datetime.datetime.now()}"})
                    return{'res':'Invalid OTP', 'msg':'Invalid OTP, try again !', 'code':404}
            else:
                return{'res':'Invalid OTP', 'msg':'Invalid OTP, try again !', 'code':404}
        else:
            return{'res':'error', 'msg':'Invalid Request, try again !', 'code':404}
    except Exception as e:
        print('Error:', traceback.format_exc())
        return jsonify({'res': 'error', 'msg': 'Something went wrong', 'code': 404})
        
    
# <==============================       Change  Password Page     =================================>

@app.route("/changepassword", methods=['GET', 'POST'])
def changepasswordPage():
    if request.method == "GET":
        data = request.args.get('args', None)
        print("Data is: ", data)
    return render_template("Changepassword.html", usermail=data)
  
# <==============================      Update  Password API     =================================>

@app.route("/updatemasterPassword", methods=['GET', 'POST'])
def masterpasswordUpdate():
    try:
        if request.method == "POST":
            data = request.form.to_dict()
            print("Data is: ", data)
            
            email = data.get('Email')
            
            if email is None:
                return {'res':'error', 'msg':'Something went wrong', 'code':404}
            
            password = data.get('password')
            password2 = data.get('confirm password')
            
            if password != password2:
                return {'res':'Invalid Password', 'msg':'Password and confirm password are not matching.', 'code':404}
            
            if password == password2:
                collection2.update_one({'email':email},{"$set":{
                    "password": password
                }})
                app.logger.info(f"Password Successfully Updated at {datetime.datetime.now()}")
                return {'res':'success', 'msg':'Password Successfully updated', 'code':200}
        else:
            app.logger.warning(f"Invalid Request at {datetime.datetime.now()}")
            return {'res':'error', 'msg':"Something went wrong", 'code':404}
    except Exception as e:
        app.logger.info(f"Something went wrong, {traceback.format_exc()}")
        return {'res':'error', 'msg':"Something went wrong", 'code':404}

# <=================================            END               =================================>

# 🔹 Logout API (Expire Token)
# @app.route('/logout', methods=['POST'])
# def logout():
#     token = request.headers.get('Authorization')  # Get token from request headers
#     if token:
#         token_blacklist.add(token)  # Add token to blacklist
#         return jsonify({"msg": "Token has been revoked"}), 200
#     return jsonify({"msg": "Token is required"}), 400
    
# <-----------------------------------          logout Code             ------------------------------------>

@app.route("/logout")
def logout():
    session.pop('access_token', None) 
    app.logger.warning(f'Session logout')
    return render_template("login.html")

# <-----------------------------                 The END                -------------------------------->

if __name__ == '__main__':
    app.run(port='80', host='0.0.0.0', debug=False)


