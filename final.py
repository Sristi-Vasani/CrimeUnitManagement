import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import hashlib
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from streamlit_folium import folium_static
import folium
import geopy.geocoders
from geopy.geocoders import Nominatim
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
import io
import plotly.graph_objects as go

# Set page config with a modern theme
st.set_page_config(
    page_title="CrimeSync - Crime Management System",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🕵️"
)

# Custom CSS for enhanced UI
st.markdown("""
    <style>
    .main {background-color: #f0f2f6;}
    .sidebar .sidebar-content {background-color: #2c3e50; color: white;}
    .stButton>button {background-color: #3498db; color: white; border-radius: 5px; padding: 8px 16px;}
    .stButton>button:hover {background-color: #2980b9;}
    .stTextInput>div>input, .stTextArea>textarea {border-radius: 5px; border: 1px solid #3498db; padding: 8px;}
    .stSelectbox>div>select {border-radius: 5px; border: 1px solid #3498db; padding: 8px;}
    .card {background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .notification {background-color: #27ae60; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;}
    .prompt {background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;}
    h1, h2, h3 {color: #2c3e50;}
    </style>
""", unsafe_allow_html=True)

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'Sristi@08'  
MYSQL_DB = 'crime_management'

EMAIL_ADDRESS = 'sambhavgame@gmail.com'  # Replace with your email
EMAIL_PASSWORD = 'ssvkj2006'   # Replace with your app-specific password

# Initialize MySQL connection
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )

conn = init_connection()

# Geocoder for mapping
geolocator = Nominatim(user_agent="crimesync_system")

def hash_password(password):
    """Hashes a password with a random salt."""
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

def verify_password(stored_password, provided_password):
    """Verifies a stored password against one provided by user."""
    stored_hash, salt = stored_password.split(':')
    return stored_hash == hashlib.sha256((provided_password + salt).encode()).hexdigest()

def execute_query(query, params=None, fetch=True):
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        if fetch and cursor.description:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        return result
    except Exception as e:
        st.error(f"Database Error: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()

def execute_procedure(proc_name, params=None):
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.callproc(proc_name, params)
        else:
            cursor.callproc(proc_name)
        results = []
        for result in cursor.stored_results():
            results.append(result.fetchall())
        conn.commit()
        return results if results else None
    except Exception as e:
        st.error(f"Procedure Error: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()

def send_reset_email(email, reset_token):
    """Send a password reset email."""
    subject = "CrimeSync - Password Reset"
    reset_url = f"http://localhost:8501/?reset_token={reset_token}"
    body = f"Click the link to reset your password: {reset_url}\nThis link expires in 1 hour."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        st.markdown('<div class="notification">Password reset link sent to your email!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to send email: {e}")

def check_permission(required_roles):
    """Check if the current user has the required role."""
    if 'user' not in st.session_state:
        st.error("Please log in to access this feature.")
        return False
    if st.session_state.user['role'] not in required_roles:
        st.error("You do not have permission to access this feature.")
        return False
    return True

def login():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🔒 Login to CrimeSync")
    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn"):
            query = "SELECT * FROM Users WHERE username = %s"
            user = execute_query(query, (username,))
            if user and verify_password(user[0]['password'], password):
                st.session_state.user = user[0]
                st.markdown('<div class="notification">Logged in successfully!</div>', unsafe_allow_html=True)
                st.rerun()
            else:
                st.error("Invalid username or password")
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/3062/3062634.png", caption="CrimeSync", width=150)
    st.markdown("[Register](#register) | [Forgot Password](#forgot-password)", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def register():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📝 Register to CrimeSync")
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username", key="reg_username")
            password = st.text_input("Password", type="password", key="reg_password")
            email = st.text_input("Email", key="reg_email")
        with col2:
            role = st.selectbox("Role", ["User", "Officer"], key="reg_role")
            department = st.text_input("Department (optional)", key="reg_dept")
            phone_number = st.text_input("Phone Number (optional)", key="reg_phone")
        submit = st.form_submit_button("Register")
        if submit:
            if execute_query("SELECT * FROM Users WHERE username = %s", (username,)):
                st.error("Username already exists")
            elif execute_query("SELECT * FROM Users WHERE email = %s", (email,)):
                st.error("Email already exists")
            else:
                hashed_password = hash_password(password)
                query = """
                INSERT INTO Users (username, password, email, role, status, department, phone_number)
                VALUES (%s, %s, %s, %s, 'Active', %s, %s)
                """
                if execute_query(query, (username, hashed_password, email, role, department or None, phone_number or None), fetch=False):
                    st.markdown('<div class="notification">Registration successful! Please log in.</div>', unsafe_allow_html=True)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def forgot_password():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🔑 Forgot Password")
    with st.form("forgot_form"):
        email = st.text_input("Enter your email", key="forgot_email")
        submit = st.form_submit_button("Send Reset Link")
        if submit:
            user = execute_query("SELECT * FROM Users WHERE email = %s", (email,))
            if user:
                reset_token = secrets.token_urlsafe(32)
                reset_expiry = datetime.now() + timedelta(hours=1)
                query = "UPDATE Users SET reset_token = %s, reset_expiry = %s WHERE email = %s"
                execute_query(query, (reset_token, reset_expiry, email), fetch=False)
                send_reset_email(email, reset_token)
            else:
                st.error("Email not found")
    st.markdown('</div>', unsafe_allow_html=True)

def reset_password():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🔄 Reset Password")
    reset_token = st.query_params.get("reset_token", [""])[0]
    if not reset_token:
        st.error("No reset token provided.")
        return
    with st.form("reset_form"):
        new_password = st.text_input("New Password", type="password", key="reset_new")
        confirm_password = st.text_input("Confirm Password", type="password", key="reset_confirm")
        submit = st.form_submit_button("Reset Password")
        if submit:
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return
            user = execute_query("SELECT * FROM Users WHERE reset_token = %s AND reset_expiry > %s", (reset_token, datetime.now()))
            if user:
                hashed_password = hash_password(new_password)
                query = "UPDATE Users SET password = %s, reset_token = NULL, reset_expiry = NULL WHERE reset_token = %s"
                execute_query(query, (hashed_password, reset_token), fetch=False)
                st.markdown('<div class="notification">Password reset successfully! Please log in.</div>', unsafe_allow_html=True)
                st.query_params = {}
                st.rerun()
            else:
                st.error("Invalid or expired reset token")
    st.markdown('</div>', unsafe_allow_html=True)

def show_map(city, zip_code):
    """Display a map using Folium based on city and zip code."""
    location_str = f"{city}, {zip_code}"
    try:
        location = geolocator.geocode(location_str)
        if location:
            m = folium.Map(location=[location.latitude, location.longitude], zoom_start=12)
            folium.Marker([location.latitude, location.longitude], popup=location_str).add_to(m)
            folium_static(m)
        else:
            st.warning(f"Could not geocode location: {location_str}")
    except Exception as e:
        st.error(f"Error generating map: {e}")

def generate_pdf_report(case_id, results):
    """Generate a PDF report from case data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"CrimeSync Detailed Case Report - Case ID: {case_id}", styles['Title']))
    story.append(Spacer(1, 12))

    case_data = results[0][0] if results[0] else {}
    story.append(Paragraph("Case Details", styles['Heading2']))
    case_text = f"Case No: {case_data.get('Case_no', 'N/A')}<br/>Crime Type: {case_data.get('Crime_Type', 'N/A')}<br/>Status: {case_data.get('Status', 'N/A')}<br/>Description: {case_data.get('Description', 'N/A')}<br/>Story: {case_data.get('Story', 'N/A')}"
    story.append(Paragraph(case_text, styles['BodyText']))
    if case_data.get('Forensic_photo'):
        try:
            story.append(Image(case_data['Forensic_photo'], width=200, height=150))
        except Exception as e:
            story.append(Paragraph(f"Forensic Photo unavailable: {str(e)}", styles['BodyText']))
    story.append(Spacer(1, 12))

    for section, df_data in zip(
        ["Evidence", "Suspects", "Victims", "Court Hearings", "Arrests", "Criminal Data", "Investigations", "Security Footage"],
        results[1:]):
        story.append(Paragraph(section, styles['Heading2']))
        df = pd.DataFrame(df_data)
        if not df.empty:
            story.append(Table([df.columns.tolist()] + df.values.tolist()))
        else:
            story.append(Paragraph(f"No {section.lower()} available.", styles['BodyText']))
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer

def dashboard():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📊 CrimeSync Dashboard")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Case Status")
        query = "SELECT Status, COUNT(*) as count FROM CrimeCases GROUP BY Status"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.pie(df, values='count', names='Status', title='Case Status Distribution', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Crime Types")
        query = "SELECT Crime_Type, COUNT(*) as count FROM CrimeCases GROUP BY Crime_Type"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.bar(df, x='Crime_Type', y='count', title='Cases by Crime Type', color='Crime_Type')
            st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        st.subheader("Recent Activity")
        query = "SELECT Case_no, Crime_Type, Status FROM CrimeCases ORDER BY Case_id DESC LIMIT 5"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def user_management():
    if not check_permission(['Admin']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("👤 User Management")
    tabs = st.tabs(["View Users", "Add User", "Update User", "Delete User"])
    
    with tabs[0]:
        st.subheader("View Users")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Users (e.g., username, email)", key="user_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["user_id", "username", "email", "role", "status"], key="user_sort")
        query = f"SELECT user_id, username, email, role, status, department, phone_number FROM Users"
        if search_term:
            query += " WHERE username LIKE %s OR email LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    with tabs[1]:
        st.subheader("Add New User")
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                email = st.text_input("Email")
            with col2:
                role = st.selectbox("Role", ["User", "Officer", "Admin"])
                department = st.text_input("Department (optional)")
                phone_number = st.text_input("Phone Number (optional)")
            submit = st.form_submit_button("Add User")
            if submit:
                if execute_query("SELECT * FROM Users WHERE username = %s", (username,)):
                    st.error("Username already exists")
                elif execute_query("SELECT * FROM Users WHERE email = %s", (email,)):
                    st.error("Email already exists")
                else:
                    hashed_password = hash_password(password)
                    query = """
                    INSERT INTO Users (username, password, email, role, status, department, phone_number)
                    VALUES (%s, %s, %s, %s, 'Active', %s, %s)
                    """
                    if execute_query(query, (username, hashed_password, email, role, department or None, phone_number or None), fetch=False):
                        st.markdown('<div class="notification">User added successfully!</div>', unsafe_allow_html=True)
    
    with tabs[2]:
        st.subheader("Update User")
        users = execute_query("SELECT user_id, username FROM Users")
        if users:
            user_id = st.selectbox("Select User", options=[u['user_id'] for u in users], format_func=lambda x: next(u['username'] for u in users if u['user_id'] == x))
            new_role = st.selectbox("New Role", ["User", "Officer", "Admin"])
            new_status = st.selectbox("New Status", ["Active", "Inactive", "Suspended"])
            if st.button("Update User"):
                query = "UPDATE Users SET role = %s, status = %s WHERE user_id = %s"
                if execute_query(query, (new_role, new_status, user_id), fetch=False):
                    st.markdown('<div class="notification">User updated successfully!</div>', unsafe_allow_html=True)
        else:
            st.warning("No users found.")
    
    with tabs[3]:
        st.subheader("Delete User")
        users = execute_query("SELECT user_id, username FROM Users")
        if users:
            user_id = st.selectbox("Select User to Delete", options=[u['user_id'] for u in users], format_func=lambda x: next(u['username'] for u in users if u['user_id'] == x), key="del_user")
            if st.button("Delete User", key="delete_user_btn"):
                query = "DELETE FROM Users WHERE user_id = %s"
                if execute_query(query, (user_id,), fetch=False):
                    st.markdown('<div class="notification">User deleted successfully!</div>', unsafe_allow_html=True)
        else:
            st.warning("No users found.")
    st.markdown('</div>', unsafe_allow_html=True)

def crime_location_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📍 Crime Location Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Locations"] + (["Add Location"] if role in ['Admin', 'Officer'] else []) + (["Delete Location"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Locations")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Locations (e.g., City, Zip_code)", key="loc_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Location_id", "City", "Zip_code", "State", "Crime_Scene_Type"], key="loc_sort")
        query = "SELECT Location_id, City, Zip_code, State, Crime_Scene_Type FROM CrimeLocations"
        if search_term:
            query += " WHERE City LIKE %s OR Zip_code LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
            selected_row = st.selectbox("Select Location for Map", df.index, format_func=lambda x: df.loc[x, 'City'])
            if st.button("Show Map", key="loc_map"):
                show_map(df.loc[selected_row, 'City'], df.loc[selected_row, 'Zip_code'])
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Location")
            with st.form("add_loc_form"):
                col1, col2 = st.columns(2)
                with col1:
                    city = st.text_input("City")
                    zip_code = st.text_input("Zip Code")
                with col2:
                    state = st.text_input("State")
                    crime_scene_type = st.selectbox("Crime Scene Type", ["Robbery", "Homicide", "Burglary", "Theft", "Assault"])
                submit = st.form_submit_button("Add Location")
                if submit:
                    query = "INSERT INTO CrimeLocations (City, Zip_code, State, Crime_Scene_Type) VALUES (%s, %s, %s, %s)"
                    if execute_query(query, (city, zip_code, state, crime_scene_type), fetch=False):
                        st.markdown('<div class="notification">Location added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Location")
            locations = execute_query("SELECT Location_id, City FROM CrimeLocations")
            if locations:
                location_id = st.selectbox("Select Location", options=[l['Location_id'] for l in locations], format_func=lambda x: next(l['City'] for l in locations if l['Location_id'] == x))
                if st.button("Delete Location", key="del_loc"):
                    query = "DELETE FROM CrimeLocations WHERE Location_id = %s"
                    if execute_query(query, (location_id,), fetch=False):
                        st.markdown('<div class="notification">Location deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No locations found.")
    st.markdown('</div>', unsafe_allow_html=True)

def officer_management():
    if not check_permission(['Admin', 'Officer']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("👮 Officer Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Officers"] + (["Add Officer", "Update Officer", "Delete Officer"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Officers")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Officers (e.g., First_name, Last_name)", key="off_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Officer_id", "Badge_no", "First_name", "Last_name", "Department"], key="off_sort")
        query = "SELECT Officer_id, Badge_no, First_name, Last_name, Contact_no, Assigned_cases, Department FROM Officers"
        if search_term:
            query += " WHERE First_name LIKE %s OR Last_name LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role == 'Admin':
        with tabs[1]:
            st.subheader("Add New Officer")
            with st.form("add_off_form"):
                col1, col2 = st.columns(2)
                with col1:
                    badge_no = st.text_input("Badge Number")
                    first_name = st.text_input("First Name")
                    last_name = st.text_input("Last Name")
                with col2:
                    contact_no = st.text_input("Contact Number")
                    assigned_cases = st.text_input("Assigned Cases (comma-separated)")
                    department = st.text_input("Department")
                submit = st.form_submit_button("Add Officer")
                if submit:
                    query = "INSERT INTO Officers (Badge_no, First_name, Last_name, Contact_no, Assigned_cases, Department) VALUES (%s, %s, %s, %s, %s, %s)"
                    if execute_query(query, (badge_no, first_name, last_name, contact_no, assigned_cases, department), fetch=False):
                        st.markdown('<div class="notification">Officer added successfully!</div>', unsafe_allow_html=True)
        
        with tabs[2]:
            st.subheader("Update Officer")
            officers = execute_query("SELECT Officer_id, CONCAT(First_name, ' ', Last_name) as name FROM Officers")
            if officers:
                officer_id = st.selectbox("Select Officer", options=[o['Officer_id'] for o in officers], format_func=lambda x: next(o['name'] for o in officers if o['Officer_id'] == x))
                new_department = st.text_input("New Department")
                if st.button("Update Officer"):
                    query = "UPDATE Officers SET Department = %s WHERE Officer_id = %s"
                    if execute_query(query, (new_department, officer_id), fetch=False):
                        st.markdown('<div class="notification">Officer updated successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No officers found.")
        
        with tabs[3]:
            st.subheader("Delete Officer")
            officers = execute_query("SELECT Officer_id, CONCAT(First_name, ' ', Last_name) as name FROM Officers")
            if officers:
                officer_id = st.selectbox("Select Officer to Delete", options=[o['Officer_id'] for o in officers], format_func=lambda x: next(o['name'] for o in officers if o['Officer_id'] == x), key="del_off")
                if st.button("Delete Officer", key="delete_off_btn"):
                    query = "DELETE FROM Officers WHERE Officer_id = %s"
                    if execute_query(query, (officer_id,), fetch=False):
                        st.markdown('<div class="notification">Officer deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No officers found.")
    st.markdown('</div>', unsafe_allow_html=True)

def case_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🕵️ Case Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Cases"] + (["Add Case"] if role in ['Admin', 'Officer'] else []) + (["Update Case", "Update Details", "Delete Case"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Cases")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Cases (e.g., Case_no, Crime_Type, City)", key="case_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Case_id", "Case_no", "Crime_Type", "Status", "City"], key="case_sort")
        query = """
        SELECT c.Case_id, c.Case_no, c.Crime_Type, c.Status, c.Case_duration, c.Description, c.Story, c.Forensic_photo,
               l.City, l.Zip_code, l.State
        FROM CrimeCases c
        LEFT JOIN CrimeLocations l ON c.Location_id = l.Location_id
        """
        if search_term:
            query += " WHERE c.Case_no LIKE %s OR c.Crime_Type LIKE %s OR l.City LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
            selected_row = st.selectbox("Select Case for Details", df.index, format_func=lambda x: df.loc[x, 'Case_no'])
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Description:** {df.loc[selected_row, 'Description']}")
                st.markdown(f"**Story:** {df.loc[selected_row, 'Story']}")
            with col2:
                if df.loc[selected_row, 'Forensic_photo']:
                    st.image(df.loc[selected_row, 'Forensic_photo'], caption="Forensic Photo", width=300)
                if st.button("Show Map", key=f"map_{selected_row}"):
                    show_map(df.loc[selected_row, 'City'], df.loc[selected_row, 'Zip_code'])
            st.subheader("Case Timeline")
            timeline_data = execute_query("SELECT Arrest_date as Date, 'Arrest' as Event FROM Arrests WHERE Suspect_id IN (SELECT Suspect_id FROM CriminalData WHERE Associated_cases LIKE %s)", (f"%{df.loc[selected_row, 'Case_id']}%",))
            if timeline_data:
                fig = go.Figure(data=[go.Scatter(x=[d['Date'] for d in timeline_data], y=[d['Event'] for d in timeline_data], mode='lines+markers', name='Timeline')])
                st.plotly_chart(fig, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Case")
            with st.form("add_case_form"):
                col1, col2 = st.columns(2)
                with col1:
                    case_no = st.text_input("Case Number")
                    crime_type = st.selectbox("Crime Type", ["Theft", "Assault", "Burglary", "Homicide", "Cybercrime", "Fraud", "Drug-related", "Other"])
                    status = st.selectbox("Status", ["Open", "Under Investigation", "Pending Review", "Closed"])
                    case_duration = st.number_input("Case Duration (days)", min_value=0)
                with col2:
                    description = st.text_area("Description")
                    story = st.text_area("Story (Wikipedia-style)")
                    forensic_photo = st.text_input("Forensic Photo URL (optional)")
                st.subheader("Location Details")
                col3, col4 = st.columns(2)
                with col3:
                    city = st.text_input("City")
                    zip_code = st.text_input("Zip Code")
                with col4:
                    state = st.text_input("State")
                    crime_scene_type = st.selectbox("Crime Scene Type", ["Robbery", "Homicide", "Burglary", "Theft", "Assault"])
                submit = st.form_submit_button("Add Case")
                if submit:
                    execute_procedure('AddNewCase', (case_no, crime_type, status, case_duration, description, city, zip_code, state, crime_scene_type))
                    new_case_id = execute_query("SELECT Case_id FROM CrimeCases WHERE Case_no = %s", (case_no,))
                    if new_case_id:
                        query = "UPDATE CrimeCases SET Story = %s, Forensic_photo = %s WHERE Case_id = %s"
                        execute_query(query, (story, forensic_photo or None, new_case_id[0]['Case_id']), fetch=False)
                        st.markdown('<div class="notification">Case added successfully!</div>', unsafe_allow_html=True)
                    else:
                        st.error("Failed to retrieve new case ID.")
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Update Case")
            cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
            if cases:
                case_id = st.selectbox("Select Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x), key="update_case")
                new_status = st.selectbox("New Status", ["Open", "Under Investigation", "Pending Review", "Closed"])
                new_duration = st.number_input("New Case Duration (days)", min_value=0)
                if st.button("Update Case"):
                    query = "UPDATE CrimeCases SET Status = %s, Case_duration = %s WHERE Case_id = %s"
                    if execute_query(query, (new_status, new_duration, case_id), fetch=False):
                        st.markdown('<div class="notification">Case updated successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No cases found.")
        
        with tabs[3]:
            st.subheader("Update Case Details")
            cases = execute_query("SELECT Case_id, Case_no, Description, Story, Forensic_photo FROM CrimeCases")
            if cases:
                case_id = st.selectbox("Select Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x), key="update_details")
                current_desc = next(c['Description'] for c in cases if c['Case_id'] == case_id)
                current_story = next(c['Story'] for c in cases if c['Case_id'] == case_id)
                current_photo = next(c['Forensic_photo'] for c in cases if c['Case_id'] == case_id)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Current Description:** {current_desc}")
                    new_description = st.text_area("New Description", value=current_desc)
                    st.markdown(f"**Current Story:** {current_story}")
                    new_story = st.text_area("New Story", value=current_story)
                with col2:
                    st.markdown(f"**Current Forensic Photo:** {current_photo}")
                    new_photo = st.text_input("New Forensic Photo URL", value=current_photo)
                    if current_photo:
                        st.image(current_photo, width=300)
                if st.button("Update Details"):
                    query = "UPDATE CrimeCases SET Description = %s, Story = %s, Forensic_photo = %s WHERE Case_id = %s"
                    if execute_query(query, (new_description, new_story, new_photo or None, case_id), fetch=False):
                        st.markdown('<div class="notification">Case details updated successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No cases found.")
        
        with tabs[4]:
            st.subheader("Delete Case")
            cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
            if cases:
                case_id = st.selectbox("Select Case to Delete", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x), key="del_case")
                if st.button("Delete Case", key="delete_case_btn"):
                    query = "DELETE FROM CrimeCases WHERE Case_id = %s"
                    if execute_query(query, (case_id,), fetch=False):
                        st.markdown('<div class="notification">Case deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No cases found.")
    st.markdown('</div>', unsafe_allow_html=True)

def evidence_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🔍 Evidence Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Evidence"] + (["Add Evidence"] if role in ['Admin', 'Officer'] else []) + (["Delete Evidence"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Evidence")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Evidence (e.g., Type, Description)", key="evid_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Evidence_id", "Type", "Collected_date", "Case_no"], key="evid_sort")
        query = "SELECT e.Evidence_id, e.Type, e.Description, e.Collected_date, c.Case_no FROM Evidence e JOIN CrimeCases c ON e.Case_id = c.Case_id"
        if search_term:
            query += " WHERE e.Type LIKE %s OR e.Description LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Evidence")
            with st.form("add_evid_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
                    if cases:
                        case_id = st.selectbox("Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x))
                    else:
                        st.warning("No cases found.")
                        case_id = None
                    evidence_type = st.text_input("Evidence Type")
                with col2:
                    description = st.text_area("Description")
                    collected_by = st.text_input("Collected By")
                    collected_date = st.date_input("Collected Date")
                submit = st.form_submit_button("Add Evidence")
                if submit and case_id:
                    query = "INSERT INTO Evidence (Type, Description, Collected_by, Collected_date, Case_id) VALUES (%s, %s, %s, %s, %s)"
                    if execute_query(query, (evidence_type, description, collected_by, collected_date, case_id), fetch=False):
                        st.markdown('<div class="notification">Evidence added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Evidence")
            evidence = execute_query("SELECT Evidence_id, Type FROM Evidence")
            if evidence:
                evidence_id = st.selectbox("Select Evidence", options=[e['Evidence_id'] for e in evidence], format_func=lambda x: next(e['Type'] for e in evidence if e['Evidence_id'] == x))
                if st.button("Delete Evidence", key="del_evid"):
                    query = "DELETE FROM Evidence WHERE Evidence_id = %s"
                    if execute_query(query, (evidence_id,), fetch=False):
                        st.markdown('<div class="notification">Evidence deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No evidence found.")
    st.markdown('</div>', unsafe_allow_html=True)

def suspect_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🚨 Suspect Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Suspects"] + (["Add Suspect"] if role in ['Admin', 'Officer'] else []) + (["Delete Suspect"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Suspects")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Suspects (e.g., First_name, Last_name)", key="susp_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Suspect_id", "First_name", "Last_name", "Age", "Gender"], key="susp_sort")
        query = "SELECT Suspect_id, First_name, Last_name, Age, Gender, Address, Criminal_history FROM Suspects"
        if search_term:
            query += " WHERE First_name LIKE %s OR Last_name LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
            selected_row = st.selectbox("Select Suspect for Profile", df.index, format_func=lambda x: f"{df.loc[x, 'First_name']} {df.loc[x, 'Last_name']}")
            st.subheader("Suspect Profile")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Name:** {df.loc[selected_row, 'First_name']} {df.loc[selected_row, 'Last_name']}")
                st.markdown(f"**Age:** {df.loc[selected_row, 'Age']}")
                st.markdown(f"**Gender:** {df.loc[selected_row, 'Gender']}")
            with col2:
                st.markdown(f"**Address:** {df.loc[selected_row, 'Address']}")
                st.markdown(f"**Criminal History:** {df.loc[selected_row, 'Criminal_history']}")
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Suspect")
            with st.form("add_susp_form"):
                col1, col2 = st.columns(2)
                with col1:
                    first_name = st.text_input("First Name")
                    last_name = st.text_input("Last Name")
                    age = st.number_input("Age", min_value=0)
                with col2:
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                    address = st.text_area("Address")
                    criminal_history = st.text_area("Criminal History")
                submit = st.form_submit_button("Add Suspect")
                if submit:
                    query = "INSERT INTO Suspects (First_name, Last_name, Age, Gender, Address, Criminal_history) VALUES (%s, %s, %s, %s, %s, %s)"
                    if execute_query(query, (first_name, last_name, age, gender, address, criminal_history), fetch=False):
                        st.markdown('<div class="notification">Suspect added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Suspect")
            suspects = execute_query("SELECT Suspect_id, CONCAT(First_name, ' ', Last_name) as name FROM Suspects")
            if suspects:
                suspect_id = st.selectbox("Select Suspect", options=[s['Suspect_id'] for s in suspects], format_func=lambda x: next(s['name'] for s in suspects if s['Suspect_id'] == x))
                if st.button("Delete Suspect", key="del_susp"):
                    query = "DELETE FROM Suspects WHERE Suspect_id = %s"
                    if execute_query(query, (suspect_id,), fetch=False):
                        st.markdown('<div class="notification">Suspect deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No suspects found.")
    st.markdown('</div>', unsafe_allow_html=True)

def victim_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🩺 Victim Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Victims"] + (["Add Victim"] if role in ['Admin', 'Officer'] else []) + (["Delete Victim"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Victims")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Victims (e.g., Age, Gender)", key="vict_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Victim_id", "Age", "Gender", "Injury_status"], key="vict_sort")
        query = "SELECT v.Victim_id, v.Age, v.Gender, v.Contact_no, v.Injury_status, e.Type as Evidence_type FROM Victims v LEFT JOIN Evidence e ON v.Evidence_id = e.Evidence_id"
        if search_term:
            query += " WHERE v.Age LIKE %s OR v.Gender LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Victim")
            with st.form("add_vict_form"):
                col1, col2 = st.columns(2)
                with col1:
                    age = st.number_input("Age", min_value=0)
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                with col2:
                    contact_no = st.text_input("Contact Number")
                    injury_status = st.text_input("Injury Status")
                evidence = execute_query("SELECT Evidence_id, Type FROM Evidence")
                if evidence:
                    evidence_id = st.selectbox("Related Evidence", options=[e['Evidence_id'] for e in evidence], format_func=lambda x: next(e['Type'] for e in evidence if e['Evidence_id'] == x))
                else:
                    st.warning("No evidence found.")
                    evidence_id = None
                submit = st.form_submit_button("Add Victim")
                if submit and evidence_id:
                    query = "INSERT INTO Victims (Age, Gender, Contact_no, Injury_status, Evidence_id) VALUES (%s, %s, %s, %s, %s)"
                    if execute_query(query, (age, gender, contact_no, injury_status, evidence_id), fetch=False):
                        st.markdown('<div class="notification">Victim added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Victim")
            victims = execute_query("SELECT Victim_id, Age, Gender FROM Victims")
            if victims:
                victim_id = st.selectbox("Select Victim", options=[v['Victim_id'] for v in victims], format_func=lambda x: f"Age {next(v['Age'] for v in victims if v['Victim_id'] == x)}, {next(v['Gender'] for v in victims if v['Victim_id'] == x)}")
                if st.button("Delete Victim", key="del_vict"):
                    query = "DELETE FROM Victims WHERE Victim_id = %s"
                    if execute_query(query, (victim_id,), fetch=False):
                        st.markdown('<div class="notification">Victim deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No victims found.")
    st.markdown('</div>', unsafe_allow_html=True)

def court_hearing_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("⚖️ Court Hearing Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Hearings"] + (["Add Hearing"] if role in ['Admin', 'Officer'] else []) + (["Delete Hearing"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Hearings")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Hearings (e.g., Case_no, Verdict)", key="court_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Hearing_id", "Verdict", "Court_date", "Case_no"], key="court_sort")
        query = "SELECT h.Hearing_id, h.Verdict, h.Court_date, c.Case_no FROM CourtHearings h JOIN CrimeCases c ON h.Case_id = c.Case_id"
        if search_term:
            query += " WHERE c.Case_no LIKE %s OR h.Verdict LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Hearing")
            with st.form("add_court_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
                    if cases:
                        case_id = st.selectbox("Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x))
                    else:
                        st.warning("No cases found.")
                        case_id = None
                with col2:
                    verdict = st.text_input("Verdict")
                    court_date = st.date_input("Court Date")
                submit = st.form_submit_button("Add Hearing")
                if submit and case_id:
                    query = "INSERT INTO CourtHearings (Case_id, Verdict, Court_date) VALUES (%s, %s, %s)"
                    if execute_query(query, (case_id, verdict, court_date), fetch=False):
                        st.markdown('<div class="notification">Hearing added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Hearing")
            hearings = execute_query("SELECT Hearing_id, Verdict FROM CourtHearings")
            if hearings:
                hearing_id = st.selectbox("Select Hearing", options=[h['Hearing_id'] for h in hearings], format_func=lambda x: next(h['Verdict'] for h in hearings if h['Hearing_id'] == x))
                if st.button("Delete Hearing", key="del_court"):
                    query = "DELETE FROM CourtHearings WHERE Hearing_id = %s"
                    if execute_query(query, (hearing_id,), fetch=False):
                        st.markdown('<div class="notification">Hearing deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No hearings found.")
    st.markdown('</div>', unsafe_allow_html=True)

def arrest_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🚓 Arrest Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Arrests"] + (["Add Arrest"] if role in ['Admin', 'Officer'] else []) + (["Delete Arrest"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Arrests")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Arrests (e.g., Suspect_name, Charges)", key="arrest_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Arrest_id", "Arrest_date", "Location", "Charges"], key="arrest_sort")
        query = """
        SELECT a.Arrest_id, a.Arrest_date, a.Location, a.Charges, a.Bail_status, 
               s.First_name, s.Last_name, o.First_name as Officer_first, o.Last_name as Officer_last
        FROM Arrests a
        JOIN Suspects s ON a.Suspect_id = s.Suspect_id
        JOIN Officers o ON a.Officer_id = o.Officer_id
        """
        if search_term:
            query += " WHERE s.First_name LIKE %s OR s.Last_name LIKE %s OR a.Charges LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Arrest")
            with st.form("add_arrest_form"):
                col1, col2 = st.columns(2)
                with col1:
                    suspects = execute_query("SELECT Suspect_id, CONCAT(First_name, ' ', Last_name) as name FROM Suspects")
                    if suspects:
                        suspect_id = st.selectbox("Suspect", options=[s['Suspect_id'] for s in suspects], format_func=lambda x: next(s['name'] for s in suspects if s['Suspect_id'] == x))
                    else:
                        st.warning("No suspects found.")
                        suspect_id = None
                    officers = execute_query("SELECT Officer_id, CONCAT(First_name, ' ', Last_name) as name FROM Officers")
                    if officers:
                        officer_id = st.selectbox("Officer", options=[o['Officer_id'] for o in officers], format_func=lambda x: next(o['name'] for o in officers if o['Officer_id'] == x))
                    else:
                        st.warning("No officers found.")
                        officer_id = None
                with col2:
                    arrest_date = st.date_input("Arrest Date")
                    location = st.text_input("Location")
                charges = st.text_area("Charges")
                bail_status = st.selectbox("Bail Status", ["Granted", "Not Granted"])
                submit = st.form_submit_button("Add Arrest")
                if submit and suspect_id and officer_id:
                    query = "INSERT INTO Arrests (Arrest_date, Location, Charges, Bail_status, Suspect_id, Officer_id) VALUES (%s, %s, %s, %s, %s, %s)"
                    if execute_query(query, (arrest_date, location, charges, bail_status, suspect_id, officer_id), fetch=False):
                        st.markdown('<div class="notification">Arrest added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Arrest")
            arrests = execute_query("SELECT Arrest_id, Charges FROM Arrests")
            if arrests:
                arrest_id = st.selectbox("Select Arrest", options=[a['Arrest_id'] for a in arrests], format_func=lambda x: next(a['Charges'] for a in arrests if a['Arrest_id'] == x))
                if st.button("Delete Arrest", key="del_arrest"):
                    query = "DELETE FROM Arrests WHERE Arrest_id = %s"
                    if execute_query(query, (arrest_id,), fetch=False):
                        st.markdown('<div class="notification">Arrest deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No arrests found.")
    st.markdown('</div>', unsafe_allow_html=True)

def criminal_data_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📜 Criminal Data Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Criminal Data"] + (["Add Criminal Data"] if role in ['Admin', 'Officer'] else []) + (["Delete Criminal Data"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Criminal Data")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Criminal Data (e.g., Parole_status, Suspect_name)", key="crim_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Criminal_id", "Parole_status", "Sentence_duration", "First_name"], key="crim_sort")
        query = """
        SELECT cd.Criminal_id, cd.Parole_status, cd.Criminal_record, cd.Associated_cases, cd.Sentence_duration, 
               s.First_name, s.Last_name
        FROM CriminalData cd
        JOIN Suspects s ON cd.Suspect_id = s.Suspect_id
        """
        if search_term:
            query += " WHERE cd.Parole_status LIKE %s OR s.First_name LIKE %s OR s.Last_name LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Criminal Data")
            with st.form("add_crim_form"):
                col1, col2 = st.columns(2)
                with col1:
                    suspects = execute_query("SELECT Suspect_id, CONCAT(First_name, ' ', Last_name) as name FROM Suspects")
                    if suspects:
                        suspect_id = st.selectbox("Suspect", options=[s['Suspect_id'] for s in suspects], format_func=lambda x: next(s['name'] for s in suspects if s['Suspect_id'] == x))
                    else:
                        st.warning("No suspects found.")
                        suspect_id = None
                    parole_status = st.selectbox("Parole Status", ["On Parole", "None", "Pending"])
                with col2:
                    criminal_record = st.text_area("Criminal Record")
                    associated_cases = st.text_input("Associated Cases (comma-separated)")
                sentence_duration = st.number_input("Sentence Duration (years)", min_value=0)
                submit = st.form_submit_button("Add Criminal Data")
                if submit and suspect_id:
                    query = "INSERT INTO CriminalData (Parole_status, Criminal_record, Suspect_id, Associated_cases, Sentence_duration) VALUES (%s, %s, %s, %s, %s)"
                    if execute_query(query, (parole_status, criminal_record, suspect_id, associated_cases, sentence_duration), fetch=False):
                        st.markdown('<div class="notification">Criminal data added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Criminal Data")
            criminal_data = execute_query("SELECT Criminal_id, Parole_status FROM CriminalData")
            if criminal_data:
                criminal_id = st.selectbox("Select Criminal Data", options=[cd['Criminal_id'] for cd in criminal_data], format_func=lambda x: next(cd['Parole_status'] for cd in criminal_data if cd['Criminal_id'] == x))
                if st.button("Delete Criminal Data", key="del_crim"):
                    query = "DELETE FROM CriminalData WHERE Criminal_id = %s"
                    if execute_query(query, (criminal_id,), fetch=False):
                        st.markdown('<div class="notification">Criminal data deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No criminal data found.")
    st.markdown('</div>', unsafe_allow_html=True)

def investigation_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🧪 Investigation Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Investigations"] + (["Add Investigation"] if role in ['Admin', 'Officer'] else []) + (["Delete Investigation"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Investigations")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Investigations (e.g., Case_no, Status)", key="inv_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Investigation_id", "Status", "Start_date", "End_date", "Case_no"], key="inv_sort")
        query = """
        SELECT i.Investigation_id, i.Status, i.Start_date, i.End_date, c.Case_no, o.First_name, o.Last_name
        FROM Investigations i
        JOIN CrimeCases c ON i.Case_id = c.Case_id
        LEFT JOIN Officers o ON i.Lead_officer_id = o.Officer_id
        """
        if search_term:
            query += " WHERE c.Case_no LIKE %s OR i.Status LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Investigation")
            with st.form("add_inv_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
                    if cases:
                        case_id = st.selectbox("Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x))
                    else:
                        st.warning("No cases found.")
                        case_id = None
                    officers = execute_query("SELECT Officer_id, CONCAT(First_name, ' ', Last_name) as name FROM Officers")
                    if officers:
                        lead_officer_id = st.selectbox("Lead Officer", options=[o['Officer_id'] for o in officers], format_func=lambda x: next(o['name'] for o in officers if o['Officer_id'] == x))
                    else:
                        st.warning("No officers found.")
                        lead_officer_id = None
                with col2:
                    start_date = st.date_input("Start Date")
                    end_date = st.date_input("End Date", value=None)
                status = st.selectbox("Status", ["Ongoing", "Completed", "Pending"])
                findings = st.text_area("Findings")
                submit = st.form_submit_button("Add Investigation")
                if submit and case_id and lead_officer_id:
                    query = "INSERT INTO Investigations (Case_id, Lead_officer_id, Start_date, End_date, Status, Findings) VALUES (%s, %s, %s, %s, %s, %s)"
                    if execute_query(query, (case_id, lead_officer_id, start_date, end_date, status, findings), fetch=False):
                        st.markdown('<div class="notification">Investigation added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Investigation")
            investigations = execute_query("SELECT Investigation_id, Status FROM Investigations")
            if investigations:
                investigation_id = st.selectbox("Select Investigation", options=[i['Investigation_id'] for i in investigations], format_func=lambda x: next(i['Status'] for i in investigations if i['Investigation_id'] == x))
                if st.button("Delete Investigation", key="del_inv"):
                    query = "DELETE FROM Investigations WHERE Investigation_id = %s"
                    if execute_query(query, (investigation_id,), fetch=False):
                        st.markdown('<div class="notification">Investigation deleted successfully!</div>', unsafe_allow_html=True)
            else:
                st.warning("No investigations found.")
    st.markdown('</div>', unsafe_allow_html=True)

def security_footage_management():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🎥 Security Footage Management")
    role = st.session_state.user['role']
    tabs = st.tabs(["View Footage"] + (["Add Footage"] if role in ['Admin', 'Officer'] else []) + (["Delete Footage"] if role == 'Admin' else []))
    
    with tabs[0]:
        st.subheader("View Footage")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search Footage (e.g., Footage_type, City)", key="foot_search")
        with col2:
            sort_by = st.selectbox("Sort By", ["Footage_id", "Footage_type", "Duration", "Timestamp", "City"], key="foot_sort")
        query = "SELECT sf.Footage_id, sf.Footage_type, sf.Duration, sf.Timestamp, sf.Footage_link, cl.City FROM SecurityFootage sf JOIN CrimeLocations cl ON sf.Location_id = cl.Location_id"
        if search_term:
            query += " WHERE sf.Footage_type LIKE %s OR cl.City LIKE %s"
            data = execute_query(query, (f"%{search_term}%", f"%{search_term}%"))
        else:
            data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=sort_by)
            st.dataframe(df, use_container_width=True)
            selected_location = st.selectbox("Select Location", df['City'].unique(), key="view_footage_location")
            footage_options = df[df['City'] == selected_location][['Footage_id', 'Footage_type']].values
            if footage_options.size > 0:
                selected_footage = st.selectbox("Select Footage", options=[f"{f[0]} - {f[1]}" for f in footage_options], key="view_footage_id")
                footage_id = selected_footage.split(" - ")[0]
                footage_link = df[df['Footage_id'] == footage_id]['Footage_link'].iloc[0]
                if st.button("View Footage", key=f"view_foot_{footage_id}"):
                    st.video(footage_link)
            else:
                st.warning("No footage available for this location.")
    
    if role in ['Admin', 'Officer']:
        with tabs[1]:
            st.subheader("Add New Footage")
            with st.form("add_foot_form"):
                col1, col2 = st.columns(2)
                with col1:
                    locations = execute_query("SELECT Location_id, City FROM CrimeLocations")
                    if locations:
                        location_id = st.selectbox("Location", options=[l['Location_id'] for l in locations], format_func=lambda x: next(l['City'] for l in locations if l['Location_id'] == x), key="add_footage_location")
                    else:
                        st.warning("No locations found.")
                        location_id = None
                    footage_type = st.selectbox("Footage Type", ["CCTV", "Dashcam", "Bodycam"], key="add_footage_type")
                with col2:
                    duration = st.number_input("Duration (seconds)", min_value=0)
                    date = st.date_input("Date")
                time = st.time_input("Time")
                timestamp = datetime.combine(date, time)
                footage_link = st.text_input("Footage Link (URL)")
                submit = st.form_submit_button("Add Footage")
                if submit and location_id:
                    city_name = next(l["City"] for l in locations if l["Location_id"] == location_id)
                    st.markdown(f'<div class="prompt">Confirm adding footage for {city_name}?</div>', unsafe_allow_html=True)
                    if st.form_submit_button("Confirm Add", key="confirm_add_footage"):
                        query = "INSERT INTO SecurityFootage (Location_id, Footage_type, Duration, Timestamp, Footage_link) VALUES (%s, %s, %s, %s, %s)"
                        if execute_query(query, (location_id, footage_type, duration, timestamp, footage_link), fetch=False):
                            st.markdown('<div class="notification">Footage added successfully!</div>', unsafe_allow_html=True)
    
    if role == 'Admin':
        with tabs[2]:
            st.subheader("Delete Footage")
            locations = execute_query("SELECT Location_id, City FROM CrimeLocations")
            if locations:
                location_id = st.selectbox("Select Location", options=[l['Location_id'] for l in locations], format_func=lambda x: next(l['City'] for l in locations if l['Location_id'] == x), key="delete_footage_location")
                footage = execute_query("SELECT Footage_id, Footage_type FROM SecurityFootage WHERE Location_id = %s", (location_id,))
                if footage:
                    footage_id = st.selectbox("Select Footage", options=[f['Footage_id'] for f in footage], format_func=lambda x: next(f['Footage_type'] for f in footage if f['Footage_id'] == x), key="delete_footage_id")
                    if st.button("Delete Footage", key="del_foot"):
                        city_name = next(l["City"] for l in locations if l["Location_id"] == location_id)
                        st.markdown(f'<div class="prompt">Confirm deleting footage {footage_id} from {city_name}?</div>', unsafe_allow_html=True)
                        if st.button("Confirm Delete", key="confirm_del_footage"):
                            query = "DELETE FROM SecurityFootage WHERE Footage_id = %s"
                            if execute_query(query, (footage_id,), fetch=False):
                                st.markdown('<div class="notification">Footage deleted successfully!</div>', unsafe_allow_html=True)
                else:
                    st.warning("No footage found for this location.")
            else:
                st.warning("No locations found.")
    st.markdown('</div>', unsafe_allow_html=True)
def reports():
    if not check_permission(['Admin', 'Officer', 'User']):
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📈 Reports")
    report_type = st.selectbox("Select Report Type", ["Case Summary", "Evidence Summary", "Suspect Analysis", "Investigation Status", "Detailed Case Report"])
    
    if report_type == "Case Summary":
        query = "SELECT Crime_Type, Status, COUNT(*) as count FROM CrimeCases GROUP BY Crime_Type, Status"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.sunburst(df, path=['Crime_Type', 'Status'], values='count', title='Case Summary by Crime Type and Status', color='Crime_Type')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Evidence Summary":
        query = "SELECT Type, COUNT(*) as count FROM Evidence GROUP BY Type"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.treemap(df, path=['Type'], values='count', title='Evidence Summary by Type', color='Type')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Suspect Analysis":
        query = "SELECT Gender, COUNT(*) as count FROM Suspects GROUP BY Gender"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.bar(df, x='Gender', y='count', title='Suspect Analysis by Gender', color='Gender')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Investigation Status":
        query = "SELECT Status, COUNT(*) as count FROM Investigations GROUP BY Status"
        data = execute_query(query)
        if data:
            df = pd.DataFrame(data)
            fig = px.scatter(df, x='Status', y='count', size='count', title='Investigation Status', color='Status')
            st.plotly_chart(fig, use_container_width=True)
    
    elif report_type == "Detailed Case Report":
        st.subheader("Detailed Case Report")
        cases = execute_query("SELECT Case_id, Case_no FROM CrimeCases")
        if cases:
            case_id = st.selectbox("Select Case", options=[c['Case_id'] for c in cases], format_func=lambda x: next(c['Case_no'] for c in cases if c['Case_id'] == x))
            if st.button("Generate Report"):
                results = execute_procedure('GetCaseReport', (case_id,))
                if results:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("### Case Details")
                        case_df = pd.DataFrame(results[0])
                        st.dataframe(case_df, use_container_width=True)
                        st.markdown(f"**Description:** {case_df.iloc[0]['Description']}")
                        st.markdown(f"**Story:** {case_df.iloc[0]['Story']}")
                    with col2:
                        if case_df.iloc[0]['Forensic_photo']:
                            st.image(case_df.iloc[0]['Forensic_photo'], caption="Forensic Photo", width=300)
                    
                    for section, df_data in zip(
                        ["Evidence", "Suspects", "Victims", "Court Hearings", "Arrests", "Criminal Data", "Investigations", "Security Footage"],
                        results[1:]):
                        st.write(f"### {section}")
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)

                    pdf_buffer = generate_pdf_report(case_id, results)
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"Case_Report_{case_id}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("No data found for this case.")
        else:
            st.warning("No cases found.")
    st.markdown('</div>', unsafe_allow_html=True)

def get_menu_for_role(role):
    """Return the menu options based on user role."""
    if role == 'Admin':
        return ["Dashboard", "User Management", "Crime Location Management", "Officer Management",
                "Case Management", "Evidence Management", "Suspect Management", "Victim Management",
                "Court Hearing Management", "Arrest Management", "Criminal Data Management",
                "Investigation Management", "Security Footage Management", "Reports", "Logout"]
    elif role == 'Officer':
        return ["Dashboard", "Crime Location Management", "Officer Management", "Case Management",
                "Evidence Management", "Suspect Management", "Victim Management", "Court Hearing Management",
                "Arrest Management", "Criminal Data Management", "Investigation Management",
                "Security Footage Management", "Reports", "Logout"]
    else:  # User
        return ["Dashboard", "Crime Location Management", "Case Management", "Evidence Management",
                "Suspect Management", "Victim Management", "Court Hearing Management", "Arrest Management",
                "Criminal Data Management", "Investigation Management", "Security Footage Management",
                "Reports", "Logout"]

def main():
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3062/3062634.png", width=100)
    if 'user' not in st.session_state:
        page = st.sidebar.selectbox("Select Page", ["Login", "Register", "Forgot Password"])
        if page == "Login":
            login()
        elif page == "Register":
            register()
        elif page == "Forgot Password":
            forgot_password()
        
        if "reset_token" in st.query_params:
            reset_password()
    else:
        role = st.session_state.user['role']
        st.sidebar.title(f"Welcome, {st.session_state.user['username']} ({role})")
        menu = get_menu_for_role(role)
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Dashboard":
            dashboard()
        elif choice == "User Management":
            user_management()
        elif choice == "Crime Location Management":
            crime_location_management()
        elif choice == "Officer Management":
            officer_management()
        elif choice == "Case Management":
            case_management()
        elif choice == "Evidence Management":
            evidence_management()
        elif choice == "Suspect Management":
            suspect_management()
        elif choice == "Victim Management":
            victim_management()
        elif choice == "Court Hearing Management":
            court_hearing_management()
        elif choice == "Arrest Management":
            arrest_management()
        elif choice == "Criminal Data Management":
            criminal_data_management()
        elif choice == "Investigation Management":
            investigation_management()
        elif choice == "Security Footage Management":
            security_footage_management()
        elif choice == "Reports":
            reports()
        elif choice == "Logout":
            st.session_state.clear()
            st.markdown('<div class="notification">Logged out successfully!</div>', unsafe_allow_html=True)
            st.rerun()

if __name__ == "__main__":
    main()

print("CrimeSync - Enhanced Streamlit Application")
print("To run this application:")
print("1. Ensure you have Python and pip installed")
print("2. Install required dependencies: pip install streamlit pandas mysql-connector-python plotly streamlit-folium folium geopy reportlab")
print("3. Set up the MySQL database as per the provided schema (init_database.py)")
print("4. Update the MySQL credentials and email settings in the script")
print("5. Run the Streamlit app: streamlit run app.py")
print("6. Open the URL provided in your browser (usually http://localhost:8501)")