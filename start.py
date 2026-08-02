from os import system

# def filerun():
#     system("screen -dmSL Notification -Logfile notification.log sudo /home/myapp/app/venv/bin/python3 notify.py")
def filerun():
    system("screen -dmSL Notification -Logfile notification.log  /home/myapp/app/venv/bin/python3 notify.py")
    
filerun()