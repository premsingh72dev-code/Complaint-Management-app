import os
import json
import smtplib
from email.message import EmailMessage
from email.utils import formataddr,make_msgid
from dotenv import load_dotenv
load_dotenv()
import datetime 

EMAIL_ADDRESS = os.getenv('Email_Username')
EMAIL_PASSWORD = os.getenv('Email_Password')


# <---------------------------          Email OTP Code        --------------------------->

SENDER_NAME = "Complaint Management System"

def OtpEmailMessage(user, OTP, subject):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = formataddr((SENDER_NAME, EMAIL_ADDRESS))
    msg['To'] = user
    msg['Reply-To'] = EMAIL_ADDRESS
    msg['Date'] = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    msg['Message-ID'] = make_msgid()

    text_content = f"""\
Dear User,

We have received a request to verify your email address. Please use the following One-Time Password (OTP) to complete your verification process:

OTP: {OTP}

This OTP is valid for the next 10 minutes. If you did not request this, please ignore this email.

Regards,
{SENDER_NAME}
    """

    try:
        msg.set_content(text_content)

        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return {"res": "success", "message": "Email sent successfully!"}

    except Exception as e:
        print(f"Error occurred while sending email: {str(e)}")
        return {"res": "error", "message": f"Failed to send email: {str(e)}"}

        
# <--------------------------       Send Register Complaint Email   ---------------------------->

def sendRegisterComplaint(user, subject, complaint_number):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user
    html_content = f'''
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complaint Registered Confirmation</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f9f9f9;
            color: #333;
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background-color: #007bff;
            color: #fff;
            padding: 10px 15px;
            border-radius: 8px 8px 0 0;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }}
        .content {{
            padding: 20px;
            line-height: 1.6;
        }}
        .content p {{
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            padding: 10px;
            font-size: 14px;
            color: #777;
        }}
        .footer a {{
            color: #007bff;
            text-decoration: none;
        }}
        .highlight {{
            font-weight: bold;
            color: #007bff;
        }}
        .complaint-number {{
            font-size: 18px;
            color: #d9534f;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            Complaint Registered Successfully
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>Your complaint has been successfully registered with us. We appreciate you bringing this to our attention.</p>
            <p>Your complaint number is: <span class="complaint-number">{complaint_number}</span></p>
            <p>We are currently reviewing your issue and will get back to you shortly.</p>
            <p>If you have any further questions, please feel free to contact us.</p>
            <p>Thank you for reaching out to us.</p>
            <p class="highlight">Best Regards,<br>{SENDER_NAME}</p>
        </div>
        <div class="footer">
            <p> {SENDER_NAME} </p>
        </div>
    </div>
</body>
</html> 
    
    '''

    try:
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls() 
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return {"res": "success", "message": "Email sent successfully!"}
    except Exception as e:
        print(f"Error occurred while sending email: {str(e)}")
        return {"res": "error", "message": f"Failed to send email: {str(e)}"}
    
# <--------------------------       Admin Accept the Request       ------------------------>

def adminAcceptRequest(userEmail,technician_details,subject):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = userEmail
    html_content =  f'''
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Request Accepted</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background-color: #4caf50;
            color: white;
            padding: 15px;
            border-radius: 10px 10px 0 0;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }}
        .content {{
            padding: 20px;
            line-height: 1.8;
        }}
        .content p {{
            margin: 10px 0;
        }}
        .details {{
            margin: 15px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4caf50;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            font-size: 14px;
            color: #777;
        }}
        .footer a {{
            color: #4caf50;
            text-decoration: none;
        }}
        .technician-info {{
            font-size: 16px;
            margin: 5px 0;
        }}
        .button {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background-color: #4caf50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }}
        @media only screen and (max-width: 600px) {{
            .email-container {{
                padding: 15px;
            }}
            .header {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            Request Accepted
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>Your request has been successfully accepted. Below are the details of the technician assigned to your request:</p>
            <div class="details">
                <p class="technician-info"><strong>Technician Name:</strong> {technician_details['Name']}</p>
                <p class="technician-info"><strong>Phone Number:</strong> {technician_details['Phone Number']}</p>
                <p class="technician-info"><strong>Service Date:</strong> {datetime.datetime.now().strftime("%B %d, %Y")} </p>
                <p class="technician-info"><strong>Service Type:</strong> {technician_details['Complaint']} </p>
            </div>
            <p>Please keep this information for your reference. If you have any questions, feel free to contact us.</p>
        </div>
        <div class="footer">
            <p>{SENDER_NAME}</p>
        </div>
    </div>
</body>
</html>

    
    '''
    try:
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls() 
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return {"res": "success", "message": "Email sent successfully!"}
    except Exception as e:
        print(f"Error occurred while sending email: {str(e)}")
        return {"res": "error", "message": f"Failed to send email: {str(e)}"}
    

    
# <------------------------         OTP for Request Closure      ------------------------> 

def CloseRequest(user, subject):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user
    html_content = f'''
        <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Complaint Closure Notification</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
                color: #333;
            }}
            .email-container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background-color: #28a745;
                color: #fff;
                padding: 10px 15px;
                border-radius: 8px 8px 0 0;
                text-align: center;
                font-size: 24px;
                font-weight: bold;
            }}
            .content {{
                padding: 20px;
                line-height: 1.6;
            }}
            .content p {{
                margin: 10px 0;
            }}
            .highlight {{
                font-weight: bold;
                color: #17a2b8;
            }}
            .footer {{
                text-align: center;
                padding: 10px;
                font-size: 14px;
                color: #777;
            }}
            .footer a {{
                color: #28a745;
                text-decoration: none;
            }}
            @media only screen and (max-width: 600px) {{
                .email-container {{
                    padding: 15px;
                }}
                .header {{
                    font-size: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                Complaint Completed
            </div>
            <div class="content">
                <p>Dear User,</p>
                <p>We are pleased to inform you that your complaint has been successfully resolved and marked as completed by our team.</p>
                <p>To finalize the process, please open the mobile app and confirm the closure of this request.</p>
                <p><strong>Note:</strong> If you did not raise this complaint or have any concerns regarding the resolution, kindly contact our support team immediately .</p>
                <p class="highlight">Thank you for your patience and for using our services.</p>
            </div>
            <div class="footer">
                <p>{SENDER_NAME}</p>
            </div>
        </div>
    </body>
    </html>
    '''
    try:
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls() 
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return {"res": "success", "message": "Email sent successfully!"}
    except Exception as e:
        print(f"Error occurred while sending email: {str(e)}")
        return {"res": "error", "message": f"Failed to send email: {str(e)}"}

# at <a href="mailto:support@example.com">support@example.com</a>
    
# <--------------------     Close Complaint Email   ------------------------------->

def sendFeedBack(userID, subject, admin_name, closingDate, complaint_number):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = userID
    html_content = f'''
    <!DOCTYPE html>
<html>
<head>
    <title>Complaint Successfully Closed</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333;">
    <table align="center" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 600px; margin: 20px auto; padding: 0; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <tr>
            <td style="background-color: #0073e6; color: white; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; border-radius: 10px 10px 0 0;">
                Complaint Successfully Closed
            </td>
        </tr>
        <tr>
            <td style="padding: 20px; line-height: 1.6;">
                <p>Dear User,</p>
                <p>Your complaint has been closed successfully. We appreciate your patience and cooperation.</p>
                <p>Please share your feedback in the feedback section of our app to help us improve our services.</p>
                <table style="width: 100%; background-color: #f9f9f9; padding: 15px; border-left: 4px solid #0073e6; border-radius: 5px; margin: 15px 0;">
                    <tr>
                        <td><strong>Complaint Number:</strong> {complaint_number}</td>
                    </tr>
                    <tr>
                        <td><strong>Resolution Date:</strong> {closingDate}</td>
                    </tr>
                    <tr>
                        <td><strong>Technician Involved:</strong> {admin_name}</td>
                    </tr>
                </table>
                <p>We strive to continuously improve our service and would love to hear your feedback.</p>
            </td>
        </tr>
        <tr>
            <td style="padding: 15px; text-align: center; font-size: 14px; color: #777;">
                <p>{SENDER_NAME}</p>
            </td>
        </tr>
    </table>
</body>
</html>

    '''
    try:
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            return {"res": "success", "message": "Email sent successfully!"}
    except Exception as e:
        print(f"Error occurred while sending email: {str(e)}")
        return {"res": "error", "message": f"Failed to send email: {str(e)}"}
    
    
# <==============================               Forget Password OTP              =================================>

def send_otp_email(user_email, otp):
    msg = EmailMessage()
    msg['Subject'] = 'Forget Password OTP'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user_email

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; text-align: center; background: #f8f9fa; padding: 20px;">
        <div style="max-width: 500px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); margin: auto;">
            <h2 style="color: #007bff;">Forgot Password OTP</h2>
            <p>Use the following OTP to reset your password:</p>
            <h1 style="background: #007bff; color: white; display: inline-block; padding: 10px 20px; border-radius: 5px;">{otp}</h1>
            <p>This OTP is valid for 10 minutes.</p>
        </div>
    </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("Email sending failed:", e)
        return False
