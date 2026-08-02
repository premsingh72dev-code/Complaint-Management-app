from fpdf import FPDF
import datetime
import traceback
import os

reports = f"{os.getcwd()}/Records"

# <------------------------------       Admin Reports generate Code     --------------------------->

class ReportsPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(True, margin=15)  

    def header(self):
        """Modern Header with Logo & Title"""
        try:
            self.image(f"logo.jpg", 10, 8, 25)  
        except:
            print("Warning: Logo image not found, skipping logo.")

        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Completed Complaints Report", ln=True, align="C")
        self.ln(5)  

    def footer(self):
        """Footer with Page Number"""
        self.set_y(-15)
        self.set_font("Arial", "I", 10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_table(self, data, name, branch, authority_name):
        """Add Table with Proper Alignment"""
        self.set_font("Arial",'B', 12)
        
        self.cell(0, 10, f"Generated On: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align="C")
        self.ln(5) 
        self.cell(0, 10, f"Name: {name}", ln=True, align="L")
        self.cell(0, 10, f"Branch: {branch}", ln=True, align="L")
        self.cell(0, 10, f"Authority Name: {authority_name}", ln=True, align="L")
        self.ln(8)  
        
        left_margin = 5  # Adjust this value to move the table more left
        self.set_x(left_margin)

        self.set_fill_color(30, 144, 255)  # Blue Header
        self.set_text_color(255)  # White text
        self.set_font("Arial", "B", 10)

        col_widths = [30, 26, 25, 70, 25, 27]
        headers = ["Complaint ID", "UserName", "Quarter No.", "Description", "Resolved By", "Resolved Date"]

        for i in range(len(headers)):
            self.cell(col_widths[i], 10, headers[i], border=1, align="C", fill=True)
        self.ln()
        
        self.set_font("Arial", "", 8)
        self.set_text_color(0)

        for index, row in enumerate(data):
            
            self.set_x(left_margin) # Set left margin 
            
            if index % 2 == 0:
                self.set_fill_color(230, 240, 255)  # Light Blue for even rows
            else:
                self.set_fill_color(255, 255, 255)  # White for odd rows
            print("Row :", row)
            try:
                self.cell(col_widths[0], 10, row.get("ComplaintID", ""), border=1, align="C", fill=True)
                self.cell(col_widths[1], 10, row.get("Name", ""), border=1, align="L", fill=True)
                self.cell(col_widths[2], 10, row.get("Address", ""), border=1, align="C", fill=True)
                self.cell(col_widths[3], 10, row.get("Complaint", ""), border=1, align="L", fill=True)
                self.cell(col_widths[4], 10, row.get("Admin", ""), border=1, align="L", fill=True)
                self.cell(col_widths[5], 10, row.get("ResolvedDate", ""), border=1, align="C", fill=True)
                self.ln()
            except Exception as e:
                print(traceback.format_exc())
                print(f"Error in row {index}: {e}")


# Generate PDF Function
def generate_admin_pdf(data, name, branch, authority_name, reportname):
    try:
        pdf = ReportsPDF()
        pdf.add_page()
        pdf.add_table(data, name, branch, authority_name)
        pdf.output(f"{reports}/{reportname}")
        return {'res':'success','msg':'pdf generated successfully', 'code':200}
    except Exception as e:
        print(traceback.format_exc())
        return {'res':'error', 'code':404, 'msg':str(e), 'error':traceback.format_exc()}

#  <==========================           User Reports Download COde            ======================================>

class UsersPDFReports(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(True, margin=15)

    def header(self):
        """Modern Header with Logo & Title"""
        try:
            self.image(f"logo.jpg", 10, 8, 25)
        except:
            print("Warning: Logo image not found, skipping logo.")

        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "User Complaints Report", ln=True, align="C")
        self.ln(5)

    def footer(self):
        """Footer with Page Number"""
        self.set_y(-15)
        self.set_font("Arial", "I", 10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_table(self, Reports, name, branch, designation, quarter_number, Active_date):
        """Add Table with Proper Alignment"""
        self.set_font("Arial",'B', 12)
        
        self.cell(0, 10, f"Generated On: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align="C")
        self.ln(5)

        # Profile Details
        self.set_font("Arial",'B', 12)
        self.cell(0, 8, f"Profile Details:", ln=True)
        self.set_font("Arial", '', 10)
        self.cell(0, 8, f"Name: {name}", ln=True)
        self.cell(0, 8, f"Branch: {branch}", ln=True)
        self.cell(0, 8, f"Designation: {designation}", ln=True)
        self.cell(0, 8, f"Quarter No: {quarter_number}", ln=True)
        self.cell(0, 8, f"Active From: {Active_date}", ln=True)
        self.ln(8)

        # Increase Table Width from Left
        left_margin = 5  # Shift more left
        self.set_x(left_margin)

        # Table Headers
        self.set_fill_color(30, 144, 255)
        self.set_text_color(255)
        self.set_font("Arial", "B", 10)

        col_widths = [35, 70, 35, 30, 30]  # Increase column width
        headers = ["Complaint ID", "Description", "Resolved By", "Lead Time", "Resolved Date"]

        for i in range(len(headers)):
            self.cell(col_widths[i], 10, headers[i], border=1, align="C", fill=True)
        self.ln()

        # Table Data
        self.set_font("Arial", "", 8)
        self.set_text_color(0)

        for index, row in enumerate(Reports):
            self.set_x(left_margin)

            if index % 2 == 0:
                self.set_fill_color(230, 240, 255)
            else:
                self.set_fill_color(255, 255, 255)

            try:
                self.cell(col_widths[0], 10, row.get("ComplaintID", ""), border=1, align="C", fill=True)
                self.cell(col_widths[1], 10, row.get("Description", ""), border=1, align="L", fill=True)
                self.cell(col_widths[2], 10, row.get("Resolved_by", ""), border=1, align="C", fill=True)
                self.cell(col_widths[3], 10, row.get("time_taken", ""), border=1, align="L", fill=True)
                self.cell(col_widths[4], 10, row.get("ResolvedDate", ""), border=1, align="C", fill=True)
                self.ln()
            except Exception as e:
                print(traceback.format_exc())
                print(f"Error in row {index}: {e}")

# Generate PDF Function
def generate_user_pdf(Reports, name, branch, designation, quarter_number, Active_date,  reportname):
    try:
        pdf = UsersPDFReports()
        pdf.add_page()
        pdf.add_table(Reports, name, branch, designation, quarter_number, Active_date)
        pdf.output(f"{reports}/{reportname}")
        return {'res':'success','msg':'pdf generated successfully', 'code':200}
    except Exception as e:
        print(traceback.format_exc())
        return {'res':'error', 'code':404, 'msg':str(e), 'error':traceback.format_exc()}
