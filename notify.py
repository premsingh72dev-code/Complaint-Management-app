import os
import pymongo
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
load_dotenv() 
import traceback
import time
import threading


# <----------- env setup -------->

my_db_url = os.getenv('DATABASE_URL')


# <========================         FireBase Setup          =========================>

import firebase_admin
from firebase_admin import credentials, messaging

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

db3 = client['Notifications']
collection4 = db3['Send-Notifications']

# <--------------------         ---------------------->

# <======================   FireBase Code Starts Here   ==========================>

def send_notification(token, title, body):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,  # The device token
        )
        response = messaging.send(message)
        
        return {'res':'success', 'msg':response, 'code':200}
    except messaging.FirebaseError as e:
        return {'res':"error", 'msg':str(e), 'code':402}

# <--------------------         ---------------------->

def send_notification_Reminder(users):
    try:
        technician_id = users.get('TechnicianDetails', {}).get('ID')
        complaint_id = users.get('Complaint ID')
        user_details = collection2.find_one({'_id':technician_id},{'Name':1, 'DeviceDetails':1})
        device_token = user_details.get('DeviceDetails', {}).get('device-token')
        
        user_name = users.get('userDetails',{}).get('name') 
        
        if device_token is not None:
            title = "🔔 Pending Complaint Reminder 🔔"
            body = f"Complaint {complaint_id} for {user_name} is still pending. Please ensure it is completed by today! ✅."
            notification_res = send_notification(device_token, title, body)
            if notification_res.get("res") == "success":
                Notification = {}
                current_time = time.time()
                Notification['_id'] = str(int(current_time * 1000))
                
                Notification['title'] = title
                Notification['body'] = body
                Notification['dates'] = {
                    "date": str(datetime.now().strftime("%d-%m-%Y")),
                    "time": str(datetime.now().strftime("%H:%M:%S")),
                    "dateTime": str(datetime.now())
                }
                Notification['Type'] = "Complaint Accept Notification"
                Notification['Status'] = notification_res
                Notification['ComplaintID'] = complaint_id
                Notification['UserID'] = str(technician_id)
                collection4.insert_one(Notification)
                collection3.update_one({'_id':complaint_id},{"$set":{
                    "reminder_status":True,
                    "ReminderDateTime":{
                        "date": str(datetime.now().strftime("%d-%m-%Y")),
                        "time": str(datetime.now().strftime("%H:%M:%S")),
                        "dateTime": str(datetime.now())
                    }
                }})
                return {'status':"success", 'code':200}
            else:
                return {'status':'error', 'code':404, 'msg':'something went wrong'}
        else:
            return {'status':'error', 'code':404, 'msg':'device token not found'}
    except Exception as e:
        print("error", traceback.format_exc())
        return {'status':'error', 'code':404, 'msg':str(e)}
    
    

def send_reminders_admin():
    print("Admin Send Reminder Code Execution started ...")
    while True:
        try:
            accepted_complaints = list(collection3.find({"Complaint Status":"Accepted"}))
            today_date = datetime.now().strftime("%d-%m-%Y")
            
            if accepted_complaints:
                for i in accepted_complaints:
                    check_complaints_type = i.get("completion_time", "")
                    reminder_status = i.get('reminder_status', None)
                    # print("Reminder Status is: ", reminder_status)
                    
                    if reminder_status is None:
                        if check_complaints_type.endswith('day') or check_complaints_type.endswith('days'):
                            print("Running on days")
                            
                            accept_date = i.get('acceptedDateTime', {}).get("Date")
                            total_days = i.get('completion_time')
                            given_date = datetime.strptime(accept_date, "%d-%m-%Y")
                            
                            print("Given date is: ", given_date)
                            
                            select_day = ''
                            
                            if 'day' in check_complaints_type:
                                select_day = check_complaints_type.replace('day', '')
                            else:
                                select_day = check_complaints_type.replace('days', '')
                            
                            select_day = "".join(filter(str.isdigit, check_complaints_type))
                            print("the selected day is: ", select_day)
                            
                            future_date = given_date + timedelta(days=int(select_day))

                            print("Future date is: ", future_date.strftime("%d-%m-%Y"))
                            
                            if today_date == future_date.strftime("%d-%m-%Y"):
                                print("the day is today, send notification, code executed ...")
                                print('User is: ', i)
                    
                                res = send_notification_Reminder(i)
                                print("Response is: ", res.get('status'))
                        
                        elif "hour" in check_complaints_type or "hours" in check_complaints_type:
                            
                            print("<-------------- Running on hours --------------->")

                            accept_date = i.get('acceptedDateTime', {}).get("Date")
                            accept_time = i.get('acceptedDateTime', {}).get("Time")
                            selected_date_time = i.get('acceptedDateTime', {}).get("DateTime")
                            complete_time = i.get('completion_time')

                            # Extract only numeric hours from completion_time
                            select_hours = "".join(filter(str.isdigit, check_complaints_type))

                            print("<========================       ======================>")
                            
                            today_current_time = datetime.now()
                            current_time = datetime.strptime(selected_date_time, "%Y-%m-%d %H:%M:%S.%f")
                            
                            current_date_today = today_current_time.strftime("%d-%m-%Y")
                            current_today_time = today_current_time.strftime("%H:%M")
                            
                            future_time = current_time + timedelta(hours=int(select_hours))
                            
                            # print("The Current Time is: ", current_time)
                            # print("Time is: ", future_time)
                            # print(f"Date & Time after {select_hours} hours:", future_time.strftime("%Y-%m-%d %H:%M:%S"))
                            
                            notification_date = future_time.strftime("%d-%m-%Y")
                            notification_time = future_time.strftime("%H:%M")
                            
                            # print("notification_date is: ", notification_date)
                            # print("the current_date is: ", current_date_today)
                            
                            # print("notification_time is: ", notification_time)
                            # print("current_today_time is: ", current_today_time)
                            
                            
                            if current_date_today == notification_date:
                                
                                if current_today_time == notification_time:
                                    print("Time 's up code started....")
                                    res = send_notification_Reminder(i)
                                    print("Response is:", res.get('status'))
                                else:
                                    pass
                            else:
                                pass    
                time.sleep(30)
            else:
                pass
        except Exception as e:
            print(traceback.format_exc())
            print("error ", str(e))  
            
        
# run the daily code:

def check_completed_complaints():
    print("Auto Complete Complaint Code Execution started ...")
    while True:
        accepted_complaints = list(collection3.find({"Complaint Status":"Accepted", "isClosed":True}))
        today_date = str(datetime.now().strftime("%d-%m-%Y"))
        # print("Today date is: ", today_date)
        # print("Complaints is: ", accepted_complaints)
        
        for i in accepted_complaints:
            print('running ...')
            complaint_close_date = i.get("auto_close_date", None)
            
                
            print("the complaint_close_date is: ", complaint_close_date)
            if today_date == complaint_close_date:
                complaint_ID = i.get("Complaint ID", None)
                
                user_id = i.get('userDetails', {}).get('ID')
                user_details = collection2.find_one({'_id':user_id})
                username = user_details.get("Name")
                device_token = user_details.get("DeviceDetails",{}).get('device-token')
                
                collection3.update_one({"Complaint ID":complaint_ID},{"$unset":{
                    "Close Request":"",
                    "isClosed": "",
                    "ComplaintCloseStatus":""
                    }})
                            
                collection3.update_one({"Complaint ID":complaint_ID},{"$set":{
                    "Complaint Status":"Completed",
                    "remarks":"Completed",
                    "Close Request":{
                        "status":"Closed",
                        "verify":True,
                        "DateTime":str(datetime.now())
                    },
                    "complaint_user_status":"Completed",
                    "completed_by":"autoCompleted",
                    "completedDateTime":{
                        "Date": str(datetime.now().strftime("%d-%m-%Y")),
                        "Time": str(datetime.now().strftime("%H:%M:%S")),
                        "DateTime": str(datetime.now()),
                        "Month":str(datetime.now().strftime("%B")),
                        "Year": str(datetime.now().strftime("%Y")),
                    },
                    "User_complaints_status_dates": {
                        "date": str(datetime.now().strftime("%d-%m-%Y")),
                        "time": str(datetime.now().strftime("%H:%M:%S")),
                        "dateTime": str(datetime.now()),
                        "Month":str(datetime.now().strftime("%B")),
                        "Year": str(datetime.now().strftime("%Y")),
                    }
                }})  
                
                if device_token is not None:
                    
                    title = "Complaint Successfully Completed"
                    body = f"Dear {username}, Your Complaint No. {complaint_ID} has been Successfully Completed,Please share your feedback."
                    notification_res = send_notification(device_token, title, body)
                    # print("Response of Notification is: ", notification_res)
                    if notification_res.get("res") == "success":
                        Notification = {}
                        current_time = time.time()
                        Notification['_id'] = str(int(current_time * 1000))
                        Notification['title'] = title
                        Notification['body'] = body
                        Notification['dates'] = {
                            "date": str(datetime.now().strftime("%d-%m-%Y")),
                            "time": str(datetime.now().strftime("%H:%M:%S")),
                            "dateTime": str(datetime.now())
                        }
                        Notification['Type'] = "Complaint Closed"
                        Notification['Status'] = notification_res
                        Notification['ComplaintID'] = complaint_ID
                        Notification['UserID'] = str(user_id)
                        collection4.insert_one(Notification)
                    else:
                        print(f"Notification is not sent, check the error")
                else:
                    print("Device token is not found, please check the error...")
                print("Complaint successfully closed.... ")
            else:
                print()
                print("No Complaints found...",complaint_close_date)
        time.sleep(5)
        
complete_complaints = threading.Thread(target=check_completed_complaints)
reminders_code = threading.Thread(target=send_reminders_admin)

complete_complaints.start()
reminders_code.start()
    
       