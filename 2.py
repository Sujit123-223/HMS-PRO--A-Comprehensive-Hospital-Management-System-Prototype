from flask import Flask, request, redirect, url_for, flash, session, g
from markupsafe import Markup
import json
import uuid
import datetime
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "hms_pro_v4_super_secret_key_is_awesome"

DATA_FILE = "hms_data.json"

# --- Data Handling ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "patients": [], "doctors": [], "appointments": [],
            "medical_notes": [], "prescriptions": [], "invoices": [], "users": {}
        }
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            default_keys = {
                "patients": [], "doctors": [], "appointments": [],
                "medical_notes": [], "prescriptions": [], "invoices": [], "users": {}
            }
            for key, default_value in default_keys.items():
                if key not in data:
                    data[key] = default_value
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "patients": [], "doctors": [], "appointments": [],
            "medical_notes": [], "prescriptions": [], "invoices": [], "users": {}
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)

hms_data = load_data()

# --- Helper Functions ---
def generate_uuid():
    return str(uuid.uuid4())

def get_entity_by_id(entity_type, entity_id):
    for entity in hms_data.get(entity_type, []):
        if entity.get('id') == entity_id:
            return entity
    return None

def get_patient_name(patient_id, full=True):
    patient = get_entity_by_id("patients", patient_id)
    if patient:
        return f"{patient.get('first_name','')} {patient.get('last_name','')}" if full else patient.get('first_name','')
    return "N/A"

def get_doctor_name(doctor_id):
    doctor = get_entity_by_id("doctors", doctor_id)
    return doctor.get('name', "N/A") if doctor else "N/A"

def get_prescription_for_appointment(appointment_id):
    for pres in hms_data.get("prescriptions", []):
        if pres.get("appointment_id") == appointment_id:
            return pres
    return None

def get_invoice_for_appointment(appointment_id):
    for inv in hms_data.get("invoices", []):
        if inv.get("appointment_id") == appointment_id:
            return inv
    return None

# --- Simulated User/Auth ---
@app.before_request
def load_logged_in_user_and_doctor_profile():
    user_id = session.get('user_id')
    g.user = session.get('username', None)
    g.doctor_profile = None
    if g.user:
        for doc in hms_data['doctors']:
            if doc.get('name', '').lower() == g.user.lower():
                g.doctor_profile = doc
                break

# --- HTML Generation Functions ---
def base_html(title, content, show_nav=True, current_page_endpoint=None):
    nav_html = ""
    user_greeting_html = ""
    my_profile_link_html = "" # Initialize to empty string

    if g.user:
        user_greeting_html = f"<span class='user-greeting'>Logged in as: <strong>{Markup.escape(g.user)}</strong> | <a href='{url_for('logout')}' class='logout-link'>Logout</a></span>"
        if g.doctor_profile: # Check if g.doctor_profile exists and is not None
            doctor_id_for_url = g.doctor_profile.get('id') # Use .get() for safety
            if doctor_id_for_url: # Ensure ID was found
                profile_url = url_for('view_doctor', doctor_id=doctor_id_for_url)
                my_profile_link_html = f'<a href="{profile_url}" class="my-profile-link"><span class="nav-icon">🧑‍⚕️</span> My Schedule</a>'
    else:
        user_greeting_html = f"<span class='user-greeting'><a href='{url_for('login')}' class='login-link'>Login</a></span>"


    search_form_html = f"""
    <form method="GET" action="{url_for('search_results')}" class="search-form">
        <input type="search" name="query" placeholder="Search Patients/Doctors..." value="{Markup.escape(request.args.get('query', ''))}">
        <button type="submit"><span class="nav-icon">🔍</span></button>
    </form>
    """

    if show_nav:
        nav_items = {
            'dashboard': ('🏠', 'Dashboard'),
            'list_patients': ('👤', 'Patients'),
            'list_doctors': ('⚕️', 'Doctors'),
            'list_appointments': ('📅', 'Appointments')
        }
        nav_links_html = ""
        for endpoint, (icon, text) in nav_items.items():
            active_class = 'active' if endpoint == current_page_endpoint else ''
            nav_links_html += f'<a href="{url_for(endpoint)}" class="{active_class}"><span class="nav-icon">{icon}</span> {text}</a>'

        nav_html = f"""
        <header class="main-header">
            <div class="logo-container">
                <a href="{url_for('dashboard')}" class="logo-link">HMS Pro</a>
            </div>
            <nav>
                {nav_links_html}
                {my_profile_link_html}
            </nav>
            <div class="header-right">
                {search_form_html}
                {user_greeting_html}
            </div>
        </header>
        """

    # Embedded CSS
    css_styles = """
    <style>
        /* Reset and Base */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f0f2f5; /* Slightly different background */
            color: #3f3f3f; /* Softer black */
            line-height: 1.65;
            font-size: 16px;
        }

        /* Main Header & Navigation */
        .main-header {
            background-color: #ffffff; /* White header */
            color: #333;
            padding: 0 25px; /* More padding */
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
            height: 65px; /* Fixed height */
        }
        .logo-container { display: flex; align-items: center; }
        .main-header .logo-link {
            font-size: 1.6em;
            font-weight: 700; /* Bolder */
            color: #007bff; /* Primary blue */
            text-decoration: none;
        }
        .main-header nav { display: flex; align-items: center; }
        .main-header nav a, .main-header .my-profile-link {
            color: #555;
            text-decoration: none;
            margin: 0 12px;
            padding: 8px 10px;
            border-radius: 5px;
            transition: background-color 0.2s ease, color 0.2s ease;
            font-weight: 500;
            font-size: 0.95em;
            display: flex; /* For icon alignment */
            align-items: center;
        }
        .main-header nav a .nav-icon, .main-header .my-profile-link .nav-icon { margin-right: 7px; font-size: 1.1em; }
        .main-header nav a:hover, .main-header .my-profile-link:hover {
            background-color: #e9ecef; /* Light grey hover */
            color: #0056b3; /* Darker blue on hover */
        }
        .main-header nav a.active {
            background-color: #007bff;
            color: #fff;
            font-weight: 600;
        }
        .main-header nav a.active:hover { background-color: #0056b3; }

        .header-right { display: flex; align-items: center; }
        .search-form { display: flex; margin-right: 20px; }
        .search-form input[type="search"] {
            padding: 7px 10px;
            border: 1px solid #ced4da;
            border-radius: 4px 0 0 4px;
            font-size: 0.9em;
            width: 200px;
        }
        .search-form button {
            padding: 7px 10px;
            border: 1px solid #007bff;
            background-color: #007bff;
            color: white;
            border-radius: 0 4px 4px 0;
            cursor: pointer;
            border-left: none;
        }
        .search-form button .nav-icon { font-size: 1em; }


        .user-greeting { font-size: 0.9em; color: #555; }
        .user-greeting strong { color: #007bff; }
        .user-greeting a { color: #dc3545; text-decoration: none; margin-left:5px; } /* Red for logout */
        .user-greeting a:hover { text-decoration: underline; }


        /* Main Content Container */
        .container {
            width: 95%;
            max-width: 1450px;
            margin: 25px auto;
            padding: 30px;
            background-color: #ffffff;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05); /* Softer shadow */
            border-radius: 12px; /* More rounded */
        }

        /* Headings */
        h1, h2, h3, h4 { color: #2c3e50; }
        h1 {
            font-size: 2em; /* Slightly smaller */
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
            text-align: left;
            font-weight: 600;
            display: flex; /* For icon alignment */
            align-items: center;
        }
        h1 .nav-icon { font-size: 1em; margin-right: 10px; color: #007bff;}

        h2 {
            font-size: 1.5em;
            margin-top: 25px;
            margin-bottom: 15px;
            color: #34495e;
            font-weight: 600;
        }
        h2:first-of-type { margin-top: 0; }
        h3 { font-size: 1.25em; margin-bottom: 12px; color: #454545; font-weight: 500; }
        h4 { font-size: 1.1em; margin-bottom: 8px; color: #555; font-weight: 500; }


        /* Tables */
        table {
            width: 100%;
            border-collapse: separate; /* Allows for border-spacing */
            border-spacing: 0; /* Reset default spacing */
            margin-bottom: 25px;
            border: 1px solid #dee2e6; /* Outer border for the table */
            border-radius: 6px; /* Rounded corners for the table */
            overflow: hidden; /* Clip content to rounded corners */
        }
        th, td {
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6; /* Horizontal lines */
            text-align: left;
            vertical-align: middle;
        }
        th {
            background-color: #f8f9fa; /* Very light grey header */
            font-weight: 600;
            color: #495057;
            border-top: none; /* Remove top border from th if table has outer border */
        }
        td { background-color: #fff; }
        tr:last-child td { border-bottom: none; } /* No bottom border for last row cells */
        tr:hover td { background-color: #f1f3f5; }
        td .action-links a, td .action-links button, td .action-links form { margin-right: 6px; margin-bottom: 4px; }
        td.action-links { white-space: nowrap; } /* Prevent action buttons from wrapping too early */


        /* Forms */
        .form-container { padding: 25px; background-color: #fdfdfd; border: 1px solid #e9ecef; border-radius: 8px; margin-bottom:25px;}
        fieldset {
            border: 1px solid #d1d8e0;
            padding: 20px 25px;
            margin-bottom: 25px;
            border-radius: 6px;
            background-color: #fff;
        }
        legend {
            font-weight: 600;
            color: #007bff; /* Blue legend */
            padding: 0 10px;
            font-size: 1.15em;
            display: flex; /* For icon alignment */
            align-items: center;
        }
        legend .icon { margin-right: 8px; font-size: 1.1em;}
        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 7px; font-weight: 500; color: #495057; font-size: 0.95em; }
        input[type="text"], input[type="date"], input[type="time"],
        input[type="email"], input[type="tel"], input[type="number"], select, textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 0.95em;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
            background-color: #fff; /* Ensure inputs are white */
        }
        input:focus, select:focus, textarea:focus {
            border-color: #80bdff;
            outline: 0;
            box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
        }
        textarea { min-height: 90px; resize: vertical; }
        select[multiple] { min-height: 120px; }

        /* Buttons */
        .button-bar { margin-top: 25px; display: flex; gap: 10px; flex-wrap: wrap; }
        button, input[type="submit"], .button-link {
            padding: 9px 16px; /* Slightly adjusted padding */
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em; /* Slightly smaller button text */
            font-weight: 500;
            text-decoration: none;
            display: inline-flex; /* For icon alignment */
            align-items: center;
            justify-content: center;
            margin-right: 0; /* Handled by gap in button-bar */
            margin-bottom: 0; /* Handled by gap in button-bar */
            transition: background-color 0.2s, transform 0.1s, box-shadow 0.2s;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        button:hover, input[type="submit"]:hover, .button-link:hover {
             transform: translateY(-1px);
             box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        button .icon, input[type="submit"] .icon, .button-link .icon { margin-right: 7px; font-size: 1.1em; }

        .button-primary { background-color: #007bff; color: white; }
        .button-primary:hover { background-color: #0069d9; }

        .button-secondary { background-color: #6c757d; color: white; }
        .button-secondary:hover { background-color: #5a6268; }

        .button-success { background-color: #28a745; color: white; }
        .button-success:hover { background-color: #218838; }

        .button-danger { background-color: #dc3545; color: white; }
        .button-danger:hover { background-color: #c82333; }

        .button-warning { background-color: #ffc107; color: #212529; }
        .button-warning:hover { background-color: #e0a800; }

        .button-info { background-color: #17a2b8; color: white; }
        .button-info:hover { background-color: #138496; }

        /* Alerts */
        .alert {
            padding: 12px 18px;
            margin-bottom: 20px;
            border: 1px solid transparent;
            border-radius: 5px;
            display: flex;
            align-items: center;
            font-size: 0.95em;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .alert .icon { font-size: 1.3em; margin-right: 12px; }
        .alert-success { background-color: #d1e7dd; color: #0f5132; border-color: #badbcc; }
        .alert-danger  { background-color: #f8d7da; color: #842029; border-color: #f5c2c7; }
        .alert-warning { background-color: #fff3cd; color: #664d03; border-color: #ffecb5; }
        .alert-info    { background-color: #cff4fc; color: #055160; border-color: #b6effb; }

        /* Dashboard Cards */
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-bottom: 30px; }
        .card {
            background: #fff;
            padding: 25px;
            border-radius: 10px; /* More rounded */
            box-shadow: 0 4px 12px rgba(0,0,0,0.06); /* Softer, more spread shadow */
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: flex;
            flex-direction: column;
        }
        .card:hover { transform: translateY(-4px); box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
        .card-header { display: flex; align-items: center; margin-bottom: 15px; }
        .card-icon { font-size: 2.2em; color: #007bff; margin-right: 15px; }
        .card h3 { margin-top: 0; margin-bottom: 5px; color: #343a40; font-size: 1.15em; font-weight: 600; }
        .card p { font-size: 0.9em; color: #6c757d; margin: 0; }
        .card .stat { font-size: 2em; font-weight: 700; color: #007bff; display: block; margin: 10px 0; }
        .card .button-link { margin-top: auto; /* Pushes button to bottom if card content varies */ }
        .card ul { list-style: none; padding-left: 0; font-size: 0.9em; }
        .card ul li { padding: 3px 0; border-bottom: 1px dashed #eee; }
        .card ul li:last-child { border-bottom: none; }
        .card ul li .meta { font-size:0.85em; color: #6c757d; }


        /* Detail View Styles */
        .detail-view-container { margin-bottom: 25px; }
        .detail-section { background-color: #f9fafb; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e9ecef; }
        .detail-section h3 { border-bottom: 1px solid #d1d8e0; padding-bottom: 8px; margin-bottom: 15px; font-size: 1.2em; color: #007bff; display: flex; align-items: center;}
        .detail-section h3 .icon { margin-right: 8px; }
        .detail-grid { display: grid; grid-template-columns: minmax(150px, auto) 1fr; gap: 8px 15px; font-size: 0.95em;}
        .detail-grid strong { font-weight: 600; color: #495057; }
        .detail-list ul { list-style: none; padding-left: 0; }
        .detail-list li { background-color: #fff; padding: 10px 12px; margin-bottom: 6px; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 0.9em;}
        .detail-list li .meta { font-size: 0.8em; color: #6c757d; display: block; }
        .detail-list li a { color: #007bff; text-decoration:none; }
        .detail-list li a:hover { text-decoration:underline; }


        /* Notes & Prescription/Billing Section */
        .related-info-section { background-color: #f8f9fa; border: 1px solid #e0e7ef; padding: 20px; margin-top: 20px; border-radius: 8px; }
        .related-info-section h4 { margin-top:0; color: #34495e; font-size: 1.15em; border-bottom: 1px solid #d1d8e0; padding-bottom: 6px; margin-bottom: 12px; display:flex; align-items:center;}
        .related-info-section h4 .icon { margin-right: 8px; }
        .related-info-section ul { list-style-type: none; padding-left: 0; }
        .related-info-section li { background-color: #fff; border: 1px solid #e9ecef; padding: 10px; margin-bottom: 8px; border-radius: 4px; font-size: 0.9em; }
        .related-info-section li strong { display: block; font-size: 0.85em; color: #5a6268; margin-bottom: 4px; }
        .related-info-section form label { font-size: 0.9em; font-weight: 500; }
        .related-info-section form textarea, .related-info-section form input[type="text"], .related-info-section form input[type="number"] { min-height: auto; font-size: 0.9em; margin-bottom:10px; }
        .related-info-section form input[type="submit"] { padding: 8px 15px; font-size: 0.9em; }

        /* No Data Message */
        .no-data {
            text-align: center;
            padding: 35px 20px;
            background-color: #f8f9fa;
            border: 1px dashed #ced4da;
            border-radius: 6px;
            color: #6c757d;
            font-size: 1.05em;
            margin: 20px 0;
        }
        .no-data .icon { font-size: 2.2em; display: block; margin-bottom: 12px; color: #adb5bd; }

        /* Login Form Specifics */
        .login-container { max-width: 420px; margin: 60px auto; padding: 35px; background: #fff; border-radius: 10px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        .login-container h2 { text-align:center; margin-bottom: 25px; font-size:1.8em; color: #007bff; }

        /* Responsive */
        @media (max-width: 1200px) {
            .main-header nav a, .main-header .my-profile-link { margin: 0 8px; }
            .search-form input[type="search"] { width: 150px; }
        }
        @media (max-width: 992px) {
            .main-header { flex-direction: column; align-items: stretch; height: auto; padding: 15px; }
            .logo-container { margin-bottom: 10px; text-align:center; width:100%; }
            .main-header nav { justify-content: center; margin-bottom:10px; flex-wrap:wrap; width:100%; }
            .main-header nav a, .main-header .my-profile-link { margin: 5px; }
            .header-right { flex-direction: column; align-items:center; width:100%; }
            .search-form { margin-right: 0; margin-bottom: 10px; width:100%; max-width:300px; }
            .search-form input[type="search"] { width: calc(100% - 40px); } /* Adjust for button */
            .user-greeting { text-align:center; width:100%; }
            .dashboard-grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
        }
        @media (max-width: 768px) {
            .detail-grid { grid-template-columns: 1fr; }
            .detail-grid strong { text-align: left; }
            h1 { font-size: 1.7em; }
            h2 { font-size: 1.3em; }
            .button-bar { flex-direction: column; }
            .button-bar button, .button-bar input[type="submit"], .button-bar .button-link { width: 100%; margin-bottom: 10px; }
            table { font-size: 0.9em; } /* Smaller text in tables */
            th, td { padding: 8px 10px; }
        }
    </style>
    """

    flashed_messages_html = ""
    messages = session.pop('_flashes', [])
    for category, message in messages:
        category_map = {'message': 'info', None: 'info'}
        alert_category = category_map.get(category, category)
        icon_map = {'success': '✔️', 'danger': '❗', 'warning': '⚠️', 'info': 'ℹ️'}
        alert_icon = icon_map.get(alert_category, 'ℹ️')
        flashed_messages_html += f'<div class="alert alert-{alert_category}"><span class="icon">{alert_icon}</span> {Markup.escape(message)}</div>'


    return Markup(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HMS Pro - {Markup.escape(title)}</title>
        {css_styles}
    </head>
    <body>
        {nav_html}
        <div class="container">
            {flashed_messages_html}
            <h1><span class="nav-icon" style="font-size:1em; margin-right:10px;">{current_page_icon(current_page_endpoint)}</span>{Markup.escape(title)}</h1>
            {content}
        </div>
        <footer style="text-align:center; padding: 25px 0; font-size:0.85em; color: #888; margin-top:30px; border-top: 1px solid #e0e0e0;">
            HMS Pro © {datetime.datetime.now().year}
        </footer>
    </body>
    </html>
    """)

def current_page_icon(endpoint):
    icons = {'dashboard': '🏠', 'list_patients': '👤', 'list_doctors': '⚕️', 'list_appointments': '📅',
             'add_patient_form': '➕👤', 'edit_patient_form': '✏️👤', 'view_patient': '👁️👤',
             'add_doctor_form': '➕⚕️', 'edit_doctor_form': '✏️⚕️', 'view_doctor': '👁️⚕️',
             'add_appointment_form': '➕📅', 'login': '🔑', 'search_results': '🔍'}
    return icons.get(endpoint, '')


# --- Simulated Login/Logout ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session['user_id'] = "user_" + generate_uuid()[:8]
            session['username'] = username
            g.user = username
            g.doctor_profile = None
            for doc in hms_data['doctors']:
                if doc.get('name', '').lower() == username.lower():
                    g.doctor_profile = doc
                    break
            flash(f"Welcome back, {Markup.escape(username)}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Please enter a username to simulate login.", "warning")

    form_html = f"""
    <div class="login-container">
        <h2>HMS Portal Login</h2>
        <form method="post">
            <div class="form-group">
                <label for="username">Enter Your Name (e.g., Dr. Smith, Admin):</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="button-bar" style="justify-content:center;">
                <button type="submit" class="button-primary"><span class="icon">🔑</span> Login</button>
            </div>
        </form>
    </div>
    """
    return base_html("Login", form_html, show_nav=False, current_page_endpoint='login')

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    g.user = None
    g.doctor_profile = None
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("login"))

# --- Search ---
@app.route("/search")
def search_results():
    if 'username' not in session: return redirect(url_for('login'))
    query = request.args.get('query', '').lower()
    escaped_query = Markup.escape(query)
    results_html = ""

    found_patients = [p for p in hms_data['patients'] if query in p.get('first_name','').lower() or query in p.get('last_name','').lower()]
    found_doctors = [d for d in hms_data['doctors'] if query in d.get('name','').lower() or query in d.get('specialty','').lower()]

    if not found_patients and not found_doctors:
        results_html += f"<div class='no-data'><span class='icon'>🤷</span>No matching patients or doctors found for \"{escaped_query}\".</div>"
    else:
        if found_patients:
            results_html += "<h3>Matching Patients</h3><table><thead><tr><th>Name</th><th>DOB</th><th>Phone</th><th>Actions</th></tr></thead><tbody>"
            for p in found_patients:
                results_html += f"""<tr>
                                    <td><a href='{url_for('view_patient', patient_id=p['id'])}'>{Markup.escape(p['first_name'])} {Markup.escape(p['last_name'])}</a></td>
                                    <td>{Markup.escape(p['dob'])}</td><td>{Markup.escape(p['phone'])}</td>
                                    <td class="action-links"><a href="{url_for('view_patient', patient_id=p['id'])}" class="button-link button-info"><span class="icon">👁️</span> View</a></td>
                                 </tr>"""
            results_html += "</tbody></table>"
        if found_doctors:
            results_html += "<h3>Matching Doctors</h3><table><thead><tr><th>Name</th><th>Specialty</th><th>Phone</th><th>Actions</th></tr></thead><tbody>"
            for d in found_doctors:
                results_html += f"""<tr>
                                    <td><a href='{url_for('view_doctor', doctor_id=d['id'])}'>{Markup.escape(d['name'])}</a></td>
                                    <td>{Markup.escape(d['specialty'])}</td><td>{Markup.escape(d['phone'])}</td>
                                    <td class="action-links"><a href="{url_for('view_doctor', doctor_id=d['id'])}" class="button-link button-info"><span class="icon">👁️</span> View</a></td>
                                 </tr>"""
            results_html += "</tbody></table>"

    return base_html(f"Search Results: \"{escaped_query}\"", results_html, current_page_endpoint='search_results')


# --- Dashboard ---
@app.route("/")
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))

    today_str = datetime.date.today().isoformat()
    appointments_today_count = 0
    appointments_today_list_html = "<ul>"
    found_today = False
    for appt in sorted(hms_data['appointments'], key=lambda x: x.get('time','')):
        if appt.get('date') == today_str and appt.get('status') == 'Scheduled':
            appointments_today_count += 1
            patient_name = get_patient_name(appt.get('patient_id'))
            doctor_name = get_doctor_name(appt.get('doctor_id'))
            appointments_today_list_html += f"<li><span class='meta'>{appt.get('time')}</span> {Markup.escape(patient_name)} with {Markup.escape(doctor_name)}</li>"
            found_today = True
    if not found_today: appointments_today_list_html += "<li>No appointments scheduled for today.</li>"
    appointments_today_list_html += "</ul>"

    unpaid_invoices_count = len([inv for inv in hms_data['invoices'] if inv.get('status') == 'Unpaid'])
    recent_patients_html = "<ul>"
    found_recent_patients = False
    for p in sorted(hms_data['patients'], key=lambda x: x.get('created_at',''), reverse=True)[:3]:
        recent_patients_html += f"<li><a href='{url_for('view_patient', patient_id=p['id'])}'>{Markup.escape(p['first_name'])} {Markup.escape(p['last_name'])}</a> <span class='meta'>(Registered: {p.get('created_at','')[:10]})</span></li>"
        found_recent_patients = True
    if not found_recent_patients: recent_patients_html += "<li>No patients registered yet.</li>"
    recent_patients_html += "</ul>"

    content = f"""
    <div class="dashboard-grid">
        <div class="card">
            <div class="card-header"><span class="card-icon">👤</span><div><h3>Patients</h3><p>Manage patient records</p></div></div>
            <span class="stat">{len(hms_data['patients'])}</span>
            <p>Total Registered</p>
            <a href="{url_for('add_patient_form')}" class="button-link button-primary"><span class="icon">➕</span> Register New</a>
        </div>
        <div class="card">
            <div class="card-header"><span class="card-icon">⚕️</span><div><h3>Doctors</h3><p>Manage doctor profiles</p></div></div>
            <span class="stat">{len(hms_data['doctors'])}</span>
            <p>Total Available</p>
            <a href="{url_for('add_doctor_form')}" class="button-link button-primary"><span class="icon">➕</span> Add New</a>
        </div>
        <div class="card">
            <div class="card-header"><span class="card-icon">📅</span><div><h3>Appointments</h3><p>Schedule and track</p></div></div>
            <span class="stat">{len(hms_data['appointments'])}</span>
            <p>Total Booked ({len([a for a in hms_data['appointments'] if a.get('status') == 'Scheduled'])} Scheduled)</p>
            <a href="{url_for('add_appointment_form')}" class="button-link button-primary"><span class="icon">➕</span> Book New</a>
        </div>
        <div class="card">
            <div class="card-header"><span class="card-icon">💵</span><div><h3>Billing</h3><p>Track invoices</p></div></div>
            <span class="stat">{unpaid_invoices_count}</span>
            <p>Unpaid Invoices</p>
            {'' if unpaid_invoices_count == 0 else '<p style="font-size:0.8em; color:red;">Action may be required.</p>'}
             <a href="{url_for('list_appointments')}" class="button-link button-info" style="font-size:0.8em; padding: 6px 10px;"><span class="icon">👁️</span> View All Appointments</a>
        </div>
    </div>

    <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr;">
        <div class="card">
            <h3><span class="icon" style="color:#28a745;">🗓️</span> Appointments Today ({today_str})</h3>
            {appointments_today_list_html}
        </div>
        <div class="card">
            <h3><span class="icon" style="color:#ffc107;">✨</span> Recently Registered Patients</h3>
            {recent_patients_html}
        </div>
    </div>
    """
    return base_html("Dashboard", content, current_page_endpoint='dashboard')

# --- Patient Management (Forms and Views) ---
def patient_form_html(patient=None, action_url=None):
    is_edit = patient is not None
    patient_id = patient.get('id', '') if is_edit else ''
    first_name = patient.get('first_name', '') if is_edit else ''
    last_name = patient.get('last_name', '') if is_edit else ''
    dob = patient.get('dob', '') if is_edit else ''
    gender = patient.get('gender', 'Other') if is_edit else 'Other'
    phone = patient.get('phone', '') if is_edit else ''
    email = patient.get('email', '') if is_edit else ''
    address = patient.get('address', '') if is_edit else ''
    allergies = patient.get('allergies', '') if is_edit else ''
    history = patient.get('history', '') if is_edit else ''

    gender_options_html = ""
    for g_opt in ["Male", "Female", "Other", "Prefer not to say"]:
        selected = 'selected' if g_opt == gender else ''
        gender_options_html += f'<option value="{Markup.escape(g_opt)}" {selected}>{Markup.escape(g_opt)}</option>'

    form_content = f"""
    <div class="form-container">
    <form method="POST" action="{action_url}">
        <input type="hidden" name="patient_id" value="{Markup.escape(patient_id)}">
        <fieldset>
            <legend><span class="icon">👤</span> Personal Information</legend>
            <div class="form-group"><label for="first_name">First Name:</label><input type="text" id="first_name" name="first_name" value="{Markup.escape(first_name)}" required></div>
            <div class="form-group"><label for="last_name">Last Name:</label><input type="text" id="last_name" name="last_name" value="{Markup.escape(last_name)}" required></div>
            <div class="form-group"><label for="dob">Date of Birth:</label><input type="date" id="dob" name="dob" value="{Markup.escape(dob)}" required></div>
            <div class="form-group"><label for="gender">Gender:</label><select id="gender" name="gender">{gender_options_html}</select></div>
        </fieldset>
        <fieldset>
            <legend><span class="icon">📞</span> Contact Information</legend>
            <div class="form-group"><label for="phone">Phone:</label><input type="tel" id="phone" name="phone" value="{Markup.escape(phone)}" pattern="[0-9\\-\\s\\(\\)]+" title="Enter a valid phone number" required></div>
            <div class="form-group"><label for="email">Email:</label><input type="email" id="email" name="email" value="{Markup.escape(email)}"></div>
            <div class="form-group"><label for="address">Address:</label><textarea id="address" name="address">{Markup.escape(address)}</textarea></div>
        </fieldset>
        <fieldset>
            <legend><span class="icon">❤️</span> Medical Information</legend>
            <div class="form-group"><label for="allergies">Allergies:</label><textarea id="allergies" name="allergies">{Markup.escape(allergies)}</textarea></div>
            <div class="form-group"><label for="history">Medical History Summary:</label><textarea id="history" name="history">{Markup.escape(history)}</textarea></div>
        </fieldset>
        <div class="button-bar">
            <button type="submit" class="button-primary"><span class="icon">💾</span> {'Update Patient' if is_edit else 'Register Patient'}</button>
            <a href="{url_for('list_patients')}" class="button-link button-secondary"><span class="icon">❌</span> Cancel</a>
        </div>
    </form>
    </div>
    """
    return form_content

@app.route("/patients")
def list_patients():
    if 'username' not in session: return redirect(url_for('login'))
    patients_html = ""
    if not hms_data['patients']:
        patients_html += "<div class='no-data'><span class='icon'>🤷</span>No patients registered yet. Start by adding one!</div>"
    else:
        patients_html += "<table><thead><tr><th>Name</th><th>DOB</th><th>Gender</th><th>Phone</th><th>Actions</th></tr></thead><tbody>"
        for p in sorted(hms_data['patients'], key=lambda x: (x.get('last_name','').lower(), x.get('first_name','').lower())):
            patients_html += f"""
            <tr>
                <td><a href="{url_for('view_patient', patient_id=p['id'])}">{Markup.escape(p.get('first_name', ''))} {Markup.escape(p.get('last_name', ''))}</a></td>
                <td>{Markup.escape(p.get('dob', 'N/A'))}</td>
                <td>{Markup.escape(p.get('gender', 'N/A'))}</td>
                <td>{Markup.escape(p.get('phone', 'N/A'))}</td>
                <td class="action-links">
                    <a href="{url_for('view_patient', patient_id=p['id'])}" class="button-link button-info"><span class="icon">👁️</span> View</a>
                    <a href="{url_for('edit_patient_form', patient_id=p['id'])}" class="button-link button-warning"><span class="icon">✏️</span> Edit</a>
                    <form method="POST" action="{url_for('delete_patient', patient_id=p['id'])}" style="display:inline;" onsubmit="return confirm('Delete Patient: {Markup.escape(p.get('first_name', ''))} {Markup.escape(p.get('last_name', ''))}?\\nThis will also delete related appointments, notes, prescriptions, and invoices.');">
                        <button type="submit" class="button-danger"><span class="icon">🗑️</span> Delete</button>
                    </form>
                </td>
            </tr>"""
        patients_html += "</tbody></table>"
    content = f"<a href='{url_for('add_patient_form')}' class='button-link button-success'><span class='icon'>➕</span> Register New Patient</a><br><br>{patients_html}"
    return base_html("Patient Records", content, current_page_endpoint='list_patients')

@app.route("/patient/new", methods=["GET", "POST"])
def add_patient_form():
    if 'username' not in session: return redirect(url_for('login'))
    if request.method == "POST":
        new_patient = {
            "id": generate_uuid(), "first_name": request.form["first_name"], "last_name": request.form["last_name"],
            "dob": request.form["dob"], "gender": request.form["gender"], "phone": request.form["phone"],
            "email": request.form.get("email", ""), "address": request.form.get("address", ""),
            "allergies": request.form.get("allergies", ""), "history": request.form.get("history", ""),
            "created_at": datetime.datetime.now().isoformat()
        }
        hms_data["patients"].append(new_patient)
        save_data(hms_data)
        flash(f"Patient {Markup.escape(new_patient['first_name'])} {Markup.escape(new_patient['last_name'])} registered successfully!", "success")
        return redirect(url_for("list_patients"))
    form_html_content = patient_form_html(action_url=url_for('add_patient_form'))
    return base_html("Register New Patient", form_html_content, current_page_endpoint='list_patients')

@app.route("/patient/edit/<patient_id>", methods=["GET", "POST"])
def edit_patient_form(patient_id):
    if 'username' not in session: return redirect(url_for('login'))
    patient = get_entity_by_id("patients", patient_id)
    if not patient:
        flash("Patient not found.", "danger"); return redirect(url_for("list_patients"))

    if request.method == "POST":
        patient_index = next((i for i, p in enumerate(hms_data["patients"]) if p["id"] == patient_id), -1)
        if patient_index != -1:
            hms_data["patients"][patient_index].update({
                "first_name": request.form["first_name"], "last_name": request.form["last_name"],
                "dob": request.form["dob"], "gender": request.form["gender"], "phone": request.form["phone"],
                "email": request.form.get("email", patient.get("email")), "address": request.form.get("address", patient.get("address")),
                "allergies": request.form.get("allergies", patient.get("allergies")), "history": request.form.get("history", patient.get("history")),
                "updated_at": datetime.datetime.now().isoformat()
            })
            save_data(hms_data)
            flash("Patient details updated successfully!", "success")
            return redirect(url_for("view_patient", patient_id=patient_id))
    form_html_content = patient_form_html(patient=patient, action_url=url_for('edit_patient_form', patient_id=patient_id))
    return base_html(f"Edit Patient: {Markup.escape(patient['first_name'])} {Markup.escape(patient['last_name'])}", form_html_content, current_page_endpoint='list_patients')

@app.route("/patient/delete/<patient_id>", methods=["POST"])
def delete_patient(patient_id):
    if 'username' not in session: return redirect(url_for('login'))
    original_len = len(hms_data["patients"])
    patient_name_deleted = get_patient_name(patient_id)
    hms_data["patients"] = [p for p in hms_data["patients"] if p["id"] != patient_id]
    appointments_to_delete = [a['id'] for a in hms_data["appointments"] if a.get("patient_id") == patient_id]
    hms_data["appointments"] = [a for a in hms_data["appointments"] if a.get("patient_id") != patient_id]
    hms_data["medical_notes"] = [n for n in hms_data["medical_notes"] if not ((n.get("entity_type") == "patient" and n.get("entity_id") == patient_id) or (n.get("entity_type") == "appointment" and n.get("entity_id") in appointments_to_delete))]
    hms_data["prescriptions"] = [p for p in hms_data["prescriptions"] if p.get("appointment_id") not in appointments_to_delete]
    hms_data["invoices"] = [i for i in hms_data["invoices"] if i.get("appointment_id") not in appointments_to_delete]

    if len(hms_data["patients"]) < original_len:
        save_data(hms_data)
        flash(f"Patient {Markup.escape(patient_name_deleted)} and all related data deleted successfully.", "success")
    else:
        flash("Patient not found for deletion.", "warning")
    return redirect(url_for("list_patients"))

@app.route("/patient/view/<patient_id>")
def view_patient(patient_id):
    if 'username' not in session: return redirect(url_for('login'))
    patient = get_entity_by_id("patients", patient_id)
    if not patient:
        flash("Patient not found.", "danger"); return redirect(url_for("list_patients"))

    details_html = "<div class='detail-section'><h3><span class='icon'>👤</span> Patient Information</h3><div class='detail-grid'>"
    key_info = {
        "Full Name": f"{Markup.escape(patient.get('first_name',''))} {Markup.escape(patient.get('last_name',''))}", "Date of Birth": Markup.escape(patient.get('dob','N/A')),
        "Gender": Markup.escape(patient.get('gender','N/A')), "Phone": Markup.escape(patient.get('phone','N/A')), "Email": Markup.escape(patient.get('email','N/A')),
        "Address": Markup.escape(patient.get('address','N/A')), "Allergies": Markup.escape(patient.get('allergies','N/A'))
    }
    for key, value in key_info.items(): details_html += f"<strong>{key}:</strong><span>{value if value else '<em>Not specified</em>'}</span>"
    details_html += "</div>"
    details_html += f"<p style='margin-top:10px;'><strong>Medical History:</strong> {Markup.escape(patient.get('history','Not specified'))}</p></div>"

    appointments_html = "<div class='detail-section'><h3><span class='icon'>📅</span> Appointments</h3><div class='detail-list'>"
    patient_appts = [a for a in hms_data["appointments"] if a.get("patient_id") == patient_id]
    if patient_appts:
        appointments_html += "<ul>"
        for appt in sorted(patient_appts, key=lambda x: x.get('date',''), reverse=True):
            doctor_name = get_doctor_name(appt.get('doctor_id'))
            prescription = get_prescription_for_appointment(appt['id'])
            invoice = get_invoice_for_appointment(appt['id'])
            
            # --- Corrected f-string usage for anchor ---
            appointment_anchor = f"appt-{appt['id']}"
            appointment_url = url_for('list_appointments', _anchor=appointment_anchor)
            # --- End Correction ---

            appt_summary = f"<a href='{appointment_url}'>📅 {Markup.escape(appt.get('date',''))} at {Markup.escape(appt.get('time',''))}</a> with {Markup.escape(doctor_name)} ({Markup.escape(appt.get('status',''))})"
            appt_summary += f"<br><span class='meta'>Reason: {Markup.escape(appt.get('reason',''))}</span>"
            if prescription: appt_summary += f"<br><span class='meta' style='color:green;'>℞ Medications: {Markup.escape(prescription.get('medications', 'N/A')[:50])}...</span>"
            if invoice: appt_summary += f"<br><span class='meta' style='color:blue;'>🧾 Invoice: ${invoice.get('amount', 0.00):.2f} ({Markup.escape(invoice.get('status', 'Unknown'))})</span>"
            appointments_html += f"<li>{appt_summary}</li>"
        appointments_html += "</ul>"
    else: appointments_html += "<div class='no-data'><span class='icon'>🤷</span>No appointments found.</div>"
    appointments_html += "</div></div>"

    notes_html = medical_notes_html(patient_id, 'patient')

    content = f"""
    <div class="button-bar" style="margin-bottom:20px;">
        <a href="{url_for('list_patients')}" class="button-link button-secondary"><span class="icon">⬅️</span> Back to Patient List</a>
        <a href="{url_for('edit_patient_form', patient_id=patient_id)}" class="button-link button-warning"><span class="icon">✏️</span> Edit Patient</a>
        <a href="{url_for('add_appointment_form', patient_id_prefill=patient_id)}" class="button-link button-success"><span class="icon">➕📅</span> New Appointment for Patient</a>
    </div>
    {details_html}
    {appointments_html}
    {notes_html}
    """
    return base_html(f"Patient Details: {Markup.escape(patient.get('first_name',''))} {Markup.escape(patient.get('last_name',''))}", content, current_page_endpoint='list_patients')


# --- Doctor Management (Forms and Views) ---
def doctor_form_html(doctor=None, action_url=None):
    is_edit = doctor is not None
    doctor_id = doctor.get('id', '') if is_edit else ''
    name = doctor.get('name', '') if is_edit else ''
    specialty = doctor.get('specialty', '') if is_edit else ''
    phone = doctor.get('phone', '') if is_edit else ''
    email = doctor.get('email', '') if is_edit else ''

    form_content = f"""
    <div class="form-container">
    <form method="POST" action="{action_url}">
        <input type="hidden" name="doctor_id" value="{Markup.escape(doctor_id)}">
        <fieldset>
            <legend><span class="icon">⚕️</span> Doctor Details</legend>
            <div class="form-group"><label for="name">Full Name:</label><input type="text" id="name" name="name" value="{Markup.escape(name)}" required></div>
            <div class="form-group"><label for="specialty">Specialty:</label><input type="text" id="specialty" name="specialty" value="{Markup.escape(specialty)}" required></div>
            <div class="form-group"><label for="phone">Phone:</label><input type="tel" id="phone" name="phone" value="{Markup.escape(phone)}" pattern="[0-9\\-\\s\\(\\)]+" title="Enter a valid phone number" required></div>
            <div class="form-group"><label for="email">Email:</label><input type="email" id="email" name="email" value="{Markup.escape(email)}"></div>
        </fieldset>
        <div class="button-bar">
            <button type="submit" class="button-primary"><span class="icon">💾</span> {'Update Doctor' if is_edit else 'Add Doctor'}</button>
            <a href="{url_for('list_doctors')}" class="button-link button-secondary"><span class="icon">❌</span> Cancel</a>
        </div>
    </form>
    </div>
    """
    return form_content

@app.route("/doctors")
def list_doctors():
    if 'username' not in session: return redirect(url_for('login'))
    doctors_html = ""
    if not hms_data['doctors']:
        doctors_html += "<div class='no-data'><span class='icon'>🤷</span>No doctors available yet.</div>"
    else:
        doctors_html += "<table><thead><tr><th>Name</th><th>Specialty</th><th>Phone</th><th>Email</th><th>Actions</th></tr></thead><tbody>"
        for d in sorted(hms_data['doctors'], key=lambda x: x.get('name','').lower()):
            doctors_html += f"""
            <tr>
                <td><a href="{url_for('view_doctor', doctor_id=d['id'])}">{Markup.escape(d.get('name', 'N/A'))}</a></td>
                <td>{Markup.escape(d.get('specialty', 'N/A'))}</td>
                <td>{Markup.escape(d.get('phone', 'N/A'))}</td>
                <td>{Markup.escape(d.get('email', 'N/A'))}</td>
                <td class="action-links">
                    <a href="{url_for('view_doctor', doctor_id=d['id'])}" class="button-link button-info"><span class="icon">👁️</span> View</a>
                    <a href="{url_for('edit_doctor_form', doctor_id=d['id'])}" class="button-link button-warning"><span class="icon">✏️</span> Edit</a>
                    <form method="POST" action="{url_for('delete_doctor', doctor_id=d['id'])}" style="display:inline;" onsubmit="return confirm('Delete Doctor: {Markup.escape(d.get('name', ''))}?\\nThis may affect existing appointments.');">
                        <button type="submit" class="button-danger"><span class="icon">🗑️</span> Delete</button>
                    </form>
                </td>
            </tr>"""
        doctors_html += "</tbody></table>"
    content = f"<a href='{url_for('add_doctor_form')}' class='button-link button-success'><span class='icon'>➕</span> Add New Doctor</a><br><br>{doctors_html}"
    return base_html("Doctor Records", content, current_page_endpoint='list_doctors')

@app.route("/doctor/new", methods=["GET", "POST"])
def add_doctor_form():
    if 'username' not in session: return redirect(url_for('login'))
    if request.method == "POST":
        new_doctor = {
            "id": generate_uuid(), "name": request.form["name"], "specialty": request.form["specialty"],
            "phone": request.form["phone"], "email": request.form.get("email", ""),
            "created_at": datetime.datetime.now().isoformat()
        }
        hms_data["doctors"].append(new_doctor)
        save_data(hms_data)
        flash(f"Doctor {Markup.escape(new_doctor['name'])} added successfully!", "success")
        return redirect(url_for("list_doctors"))
    form_html_content = doctor_form_html(action_url=url_for('add_doctor_form'))
    return base_html("Add New Doctor", form_html_content, current_page_endpoint='list_doctors')

@app.route("/doctor/edit/<doctor_id>", methods=["GET", "POST"])
def edit_doctor_form(doctor_id):
    if 'username' not in session: return redirect(url_for('login'))
    doctor = get_entity_by_id("doctors", doctor_id)
    if not doctor:
        flash("Doctor not found.", "danger"); return redirect(url_for("list_doctors"))
    if request.method == "POST":
        doctor_index = next((i for i, d in enumerate(hms_data["doctors"]) if d["id"] == doctor_id), -1)
        if doctor_index != -1:
            hms_data["doctors"][doctor_index].update({
                "name": request.form["name"], "specialty": request.form["specialty"],
                "phone": request.form["phone"], "email": request.form.get("email", doctor.get("email")),
                "updated_at": datetime.datetime.now().isoformat()
            })
            save_data(hms_data)
            flash("Doctor details updated successfully!", "success")
            return redirect(url_for("view_doctor", doctor_id=doctor_id))
    form_html_content = doctor_form_html(doctor=doctor, action_url=url_for('edit_doctor_form', doctor_id=doctor_id))
    return base_html(f"Edit Doctor: {Markup.escape(doctor['name'])}", form_html_content, current_page_endpoint='list_doctors')

@app.route("/doctor/delete/<doctor_id>", methods=["POST"])
def delete_doctor(doctor_id):
    if 'username' not in session: return redirect(url_for('login'))
    original_len = len(hms_data["doctors"])
    doctor_name_deleted = get_doctor_name(doctor_id)
    hms_data["doctors"] = [d for d in hms_data["doctors"] if d["id"] != doctor_id]
    for appt in hms_data["appointments"]:
        if appt.get("doctor_id") == doctor_id:
            appt["doctor_id"] = None
            appt["doctor_name_at_booking"] = doctor_name_deleted
    if len(hms_data["doctors"]) < original_len:
        save_data(hms_data)
        flash(f"Doctor {Markup.escape(doctor_name_deleted)} deleted. Related appointments may need review.", "success")
    else:
        flash("Doctor not found for deletion.", "warning")
    return redirect(url_for("list_doctors"))

@app.route("/doctor/view/<doctor_id>")
def view_doctor(doctor_id):
    if 'username' not in session: return redirect(url_for('login'))
    doctor = get_entity_by_id("doctors", doctor_id)
    if not doctor:
        flash("Doctor not found.", "danger"); return redirect(url_for("list_doctors"))

    details_html = "<div class='detail-section'><h3><span class='icon'>⚕️</span> Doctor Information</h3><div class='detail-grid'>"
    key_info = {
        "Full Name": Markup.escape(doctor.get('name','N/A')), "Specialty": Markup.escape(doctor.get('specialty','N/A')),
        "Phone": Markup.escape(doctor.get('phone','N/A')), "Email": Markup.escape(doctor.get('email','N/A'))
    }
    for key, value in key_info.items(): details_html += f"<strong>{key}:</strong><span>{value if value else '<em>N/A</em>'}</span>"
    details_html += "</div></div>"

    appointments_html = "<div class='detail-section'><h3><span class='icon'>📅</span> Scheduled Appointments</h3><div class='detail-list'>"
    doctor_appts = [a for a in hms_data["appointments"] if a.get("doctor_id") == doctor_id and a.get("status") == "Scheduled"]
    if doctor_appts:
        appointments_html += "<ul>"
        for appt in sorted(doctor_appts, key=lambda x: (x.get('date',''), x.get('time',''))):
            patient_name = get_patient_name(appt.get('patient_id'))
            appointments_html += f"<li>📅 {Markup.escape(appt.get('date',''))} at {Markup.escape(appt.get('time',''))} with <a href='{url_for('view_patient', patient_id=appt.get('patient_id'))}'>{Markup.escape(patient_name)}</a> - Reason: {Markup.escape(appt.get('reason',''))}</li>"
        appointments_html += "</ul>"
    else: appointments_html += "<div class='no-data'><span class='icon'>🤷</span>No scheduled appointments.</div>"
    appointments_html += "</div></div>"

    content = f"""
    <div class="button-bar" style="margin-bottom:20px;">
        <a href="{url_for('list_doctors')}" class="button-link button-secondary"><span class="icon">⬅️</span> Back to Doctor List</a>
        <a href="{url_for('edit_doctor_form', doctor_id=doctor_id)}" class="button-link button-warning"><span class="icon">✏️</span> Edit Doctor</a>
    </div>
    {details_html}
    {appointments_html}
    """
    return base_html(f"Doctor Profile: {Markup.escape(doctor.get('name',''))}", content, current_page_endpoint='list_doctors')


# --- Appointment Management (Forms, Views, Prescription, Billing) ---
def appointment_form_html(action_url=None, patient_id_prefill=None):
    patient_options_html = ""
    if not hms_data["patients"]: patient_options_html = "<option value='' disabled selected>No patients available - Please register a patient first.</option>"
    else:
        patient_options_html += "<option value='' disabled " + ("" if patient_id_prefill else "selected") + ">-- Select Patient --</option>"
        for p in sorted(hms_data["patients"], key=lambda x: (x.get('last_name','').lower(), x.get('first_name','').lower())):
            selected = 'selected' if p["id"] == patient_id_prefill else ''
            patient_options_html += f'<option value="{Markup.escape(p["id"])}" {selected}>{Markup.escape(p["first_name"])} {Markup.escape(p["last_name"])}</option>'

    doctor_options_html = ""
    if not hms_data["doctors"]: doctor_options_html = "<option value='' disabled selected>No doctors available - Please add a doctor first.</option>"
    else:
        doctor_options_html += "<option value='' disabled selected>-- Select Doctor --</option>"
        for d in sorted(hms_data["doctors"], key=lambda x: x.get('name','').lower()):
            doctor_options_html += f'<option value="{Markup.escape(d["id"])}">{Markup.escape(d["name"])} ({Markup.escape(d["specialty"])})</option>'

    form_content = f"""
    <div class="form-container">
    <form method="POST" action="{action_url}">
        <fieldset>
            <legend><span class="icon">📅</span> Appointment Details</legend>
            <div class="form-group"><label for="patient_id">Patient:</label><select id="patient_id" name="patient_id" required>{patient_options_html}</select></div>
            <div class="form-group"><label for="doctor_id">Doctor:</label><select id="doctor_id" name="doctor_id" required>{doctor_options_html}</select></div>
            <div class="form-group"><label for="date">Date:</label><input type="date" id="date" name="date" value="{datetime.date.today().isoformat()}" min="{datetime.date.today().isoformat()}" required></div>
            <div class="form-group"><label for="time">Time:</label><input type="time" id="time" name="time" value="09:00" required></div>
            <div class="form-group"><label for="reason">Reason for Visit:</label><textarea id="reason" name="reason" required></textarea></div>
        </fieldset>
        <div class="button-bar">
            <button type="submit" class="button-primary"><span class="icon">➕</span> Book Appointment</button>
            <a href="{url_for('list_appointments')}" class="button-link button-secondary"><span class="icon">❌</span> Cancel</a>
        </div>
    </form>
    </div>
    """
    return form_content

def prescription_form_html(appointment_id, existing_prescription=None):
    medications = existing_prescription.get('medications', '') if existing_prescription else ''
    instructions = existing_prescription.get('instructions', '') if existing_prescription else ''
    action = "Update" if existing_prescription else "Add"
    return f"""
    <div class="related-info-section">
        <h4><span class="icon">℞</span> {action} Prescription</h4>
        <form method="POST" action="{url_for('save_prescription', appointment_id=appointment_id)}">
            <div class="form-group">
                <label for="medications_{appointment_id}">Medications:</label>
                <textarea id="medications_{appointment_id}" name="medications" rows="3" required>{Markup.escape(medications)}</textarea>
            </div>
            <div class="form-group">
                <label for="instructions_{appointment_id}">Instructions:</label>
                <textarea id="instructions_{appointment_id}" name="instructions" rows="2">{Markup.escape(instructions)}</textarea>
            </div>
            <button type="submit" class="button-success"><span class="icon">💾</span> {action} Prescription</button>
        </form>
    </div>
    """

def invoice_form_html(appointment_id, existing_invoice=None):
    item_description = existing_invoice.get('item_description', 'Consultation & Services') if existing_invoice else 'Consultation & Services'
    amount = existing_invoice.get('amount', '') if existing_invoice else ''
    status = existing_invoice.get('status', 'Unpaid') if existing_invoice else 'Unpaid'
    action = "Update" if existing_invoice else "Create"
    form_html = f"""
    <div class="related-info-section">
        <h4><span class="icon">🧾</span> {action} Invoice</h4>
        <form method="POST" action="{url_for('save_invoice', appointment_id=appointment_id)}">
            <div class="form-group">
                <label for="item_desc_{appointment_id}">Service/Item Description:</label>
                <input type="text" id="item_desc_{appointment_id}" name="item_description" value="{Markup.escape(item_description)}" required>
            </div>
            <div class="form-group">
                <label for="amount_{appointment_id}">Amount (USD):</label>
                <input type="number" id="amount_{appointment_id}" name="amount" value="{amount}" step="0.01" min="0" required>
            </div>
            <div class="form-group">
                <label for="inv_status_{appointment_id}">Status:</label>
                <select id="inv_status_{appointment_id}" name="status">
                    <option value="Unpaid" {'selected' if status == 'Unpaid' else ''}>Unpaid</option>
                    <option value="Paid" {'selected' if status == 'Paid' else ''}>Paid</option>
                </select>
            </div>
            <button type="submit" class="button-success"><span class="icon">💾</span> {action} Invoice</button>
        </form>
    </div>
    """
    return form_html

@app.route("/appointments", methods=["GET"])
def list_appointments():
    if 'username' not in session: return redirect(url_for('login'))
    
    filter_date_from = request.args.get('date_from', '')
    filter_date_to = request.args.get('date_to', '')
    filter_status = request.args.get('status', 'All')
    query_patient_id = request.args.get('query_patient_id', None)

    filtered_appointments = list(hms_data['appointments'])
    if query_patient_id:
        filtered_appointments = [a for a in filtered_appointments if a.get('patient_id') == query_patient_id]
    if filter_date_from:
        filtered_appointments = [a for a in filtered_appointments if a.get('date','') >= filter_date_from]
    if filter_date_to:
        filtered_appointments = [a for a in filtered_appointments if a.get('date','') <= filter_date_to]
    if filter_status != 'All' and filter_status:
        filtered_appointments = [a for a in filtered_appointments if a.get('status','') == filter_status]

    filter_form_html = f"""
    <form method="GET" action="{url_for('list_appointments')}" class="form-container" style="margin-bottom:20px; background-color:#f9fafb; padding:20px;">
        <fieldset style="border-color:#d1d8e0;">
            <legend><span class="icon">🔍</span> Filter Appointments</legend>
            <div style="display:flex; gap: 15px; flex-wrap:wrap; align-items:flex-end;">
                <div class="form-group" style="flex:1; min-width:180px;">
                    <label for="date_from">Date From:</label>
                    <input type="date" id="date_from" name="date_from" value="{filter_date_from}">
                </div>
                <div class="form-group" style="flex:1; min-width:180px;">
                    <label for="date_to">Date To:</label>
                    <input type="date" id="date_to" name="date_to" value="{filter_date_to}">
                </div>
                <div class="form-group" style="flex:1; min-width:150px;">
                    <label for="status">Status:</label>
                    <select id="status" name="status">
                        <option value="All" {'selected' if filter_status == 'All' else ''}>All</option>
                        <option value="Scheduled" {'selected' if filter_status == 'Scheduled' else ''}>Scheduled</option>
                        <option value="Completed" {'selected' if filter_status == 'Completed' else ''}>Completed</option>
                        <option value="Cancelled" {'selected' if filter_status == 'Cancelled' else ''}>Cancelled</option>
                    </select>
                </div>
                <div class="form-group" style="padding-top:25px;">
                    <button type="submit" class="button-primary"><span class="icon">🔍</span> Filter</button>
                    <a href="{url_for('list_appointments')}" class="button-link button-secondary"><span class="icon">🔄</span> Reset</a>
                </div>
            </div>
        </fieldset>
    </form>
    """

    appointments_table_html = ""
    if not filtered_appointments and any([filter_date_from, filter_date_to, filter_status != 'All', query_patient_id]):
        appointments_table_html += "<div class='no-data'><span class='icon'>🤷</span>No appointments match your filter criteria.</div>"
    elif not hms_data['appointments']:
        appointments_table_html += "<div class='no-data'><span class='icon'>🤷</span>No appointments booked yet.</div>"
    else:
        appointments_table_html += "<table><thead><tr><th>Patient</th><th>Doctor</th><th>Date & Time</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead><tbody>"
        for a in sorted(filtered_appointments, key=lambda x: (x.get('date', ''), x.get('time', ''))):
            patient_name = get_patient_name(a.get('patient_id'))
            doctor_name = get_doctor_name(a.get('doctor_id'))
            status_buttons = ""
            if a.get('status') == 'Scheduled':
                status_buttons = f"""
                <form method="POST" action="{url_for('update_appointment_status', appointment_id=a['id'])}" style="display:inline;">
                    <input type="hidden" name="new_status" value="Completed">
                    <button type="submit" class="button-success"><span class="icon">✔️</span> Complete</button>
                </form>
                <form method="POST" action="{url_for('update_appointment_status', appointment_id=a['id'])}" style="display:inline;">
                    <input type="hidden" name="new_status" value="Cancelled">
                    <button type="submit" class="button-warning"><span class="icon">❌</span> Cancel</button>
                </form>
                """
            
            prescription = get_prescription_for_appointment(a['id'])
            invoice = get_invoice_for_appointment(a['id'])

            appointments_table_html += f"""
            <tr id="appt-{a['id']}">
                <td><a href="{url_for('view_patient', patient_id=a.get('patient_id'))}">{Markup.escape(patient_name)}</a></td>
                <td><a href="{url_for('view_doctor', doctor_id=a.get('doctor_id'))}">{Markup.escape(doctor_name)}</a></td>
                <td>{Markup.escape(a.get('date', 'N/A'))} at {Markup.escape(a.get('time', 'N/A'))}</td>
                <td>{Markup.escape(a.get('reason', 'N/A')[:30])}{'...' if len(a.get('reason', '')) > 30 else ''}</td>
                <td>
                    {Markup.escape(a.get('status', 'N/A'))}
                    { '<br><span style="font-size:0.8em; color:green;">℞</span>' if prescription else '' }
                    { f'<br><span style="font-size:0.8em; color:blue;">🧾 ({Markup.escape(invoice.get("status"))})</span>' if invoice else '' }
                </td>
                <td class="action-links">
                    {status_buttons}
                    <form method="POST" action="{url_for('delete_appointment', appointment_id=a['id'])}" style="display:inline;" onsubmit="return confirm('Delete appointment for {Markup.escape(patient_name)} on {Markup.escape(a.get('date'))}?');">
                        <button type="submit" class="button-danger"><span class="icon">🗑️</span> Delete</button>
                    </form>
                    <button class="button-info" onclick="toggleDetails('details-row-{a['id']}')"><span class="icon">➕</span> Details</button>
                </td>
            </tr>
            <tr id="details-row-{a['id']}" style="display:none;"><td colspan="6" style="background-color: #f9f9f9; padding:15px;">
                <h4><span class="icon">📋</span> Appointment Details:</h4>
                <p><strong>Full Reason:</strong> {Markup.escape(a.get('reason', 'N/A'))}</p>
                {medical_notes_html(a['id'], 'appointment')}
                {prescription_form_html(a['id'], prescription) if a.get('status') == 'Completed' else '<p style="font-style:italic; color:#777; padding:10px; background-color:#fff; border-radius:4px; border:1px solid #eee;">Prescriptions can be added after appointment is completed.</p>'}
                {invoice_form_html(a['id'], invoice) if a.get('status') == 'Completed' else '<p style="font-style:italic; color:#777; padding:10px; background-color:#fff; border-radius:4px; border:1px solid #eee;">Invoices can be managed after appointment is completed.</p>'}
            </td></tr>
            """
        appointments_table_html += "</tbody></table>"
    
    appointments_table_html += """
    <script>
    function toggleDetails(rowId) {
        var detailsRow = document.getElementById(rowId);
        var button = document.querySelector('button[onclick="toggleDetails(\'' + rowId + '\')"]');
        if (detailsRow) {
            if (detailsRow.style.display === 'none' || detailsRow.style.display === '') {
                detailsRow.style.display = 'table-row';
                if(button) button.innerHTML = '<span class="icon">➖</span> Details';
            } else {
                detailsRow.style.display = 'none';
                if(button) button.innerHTML = '<span class="icon">➕</span> Details';
            }
        }
    }
    // If linked with #appt-ID, open its details
    if (window.location.hash && window.location.hash.startsWith('#appt-')) {
        const apptId = window.location.hash.substring(6); // Remove #appt-
        const detailsRowId = 'details-row-' + apptId;
        const detailsRow = document.getElementById(detailsRowId);
        if (detailsRow) {
            detailsRow.style.display = 'table-row';
            var button = document.querySelector('button[onclick="toggleDetails(\'' + detailsRowId + '\')"]');
            if(button) button.innerHTML = '<span class="icon">➖</span> Details';
            const apptRow = document.getElementById('appt-' + apptId);
            if (apptRow) { apptRow.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        }
    }
    </script>
    """
    content = f"<a href='{url_for('add_appointment_form')}' class='button-link button-success'><span class='icon'>➕</span> Book New Appointment</a><br><br>{filter_form_html}{appointments_table_html}"
    return base_html("Appointment Schedule", content, current_page_endpoint='list_appointments')


@app.route("/appointment/new", methods=["GET", "POST"])
def add_appointment_form():
    if 'username' not in session: return redirect(url_for('login'))
    patient_id_prefill = request.args.get('patient_id_prefill', None)

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        if not patient_id or not doctor_id:
            flash("Patient and Doctor must be selected.", "danger")
            form_html_content = appointment_form_html(action_url=url_for('add_appointment_form'), patient_id_prefill=patient_id_prefill)
            return base_html("Book New Appointment", form_html_content, current_page_endpoint='list_appointments')

        new_appointment = {
            "id": generate_uuid(), "patient_id": patient_id, "doctor_id": doctor_id,
            "date": request.form["date"], "time": request.form["time"], "reason": request.form.get("reason", ""),
            "status": "Scheduled", "created_at": datetime.datetime.now().isoformat()
        }
        hms_data["appointments"].append(new_appointment)
        save_data(hms_data)
        flash("Appointment booked successfully!", "success")
        return redirect(url_for("list_appointments"))
    form_html_content = appointment_form_html(action_url=url_for('add_appointment_form'), patient_id_prefill=patient_id_prefill)
    return base_html("Book New Appointment", form_html_content, current_page_endpoint='list_appointments')

@app.route("/appointment/update_status/<appointment_id>", methods=["POST"])
def update_appointment_status(appointment_id):
    if 'username' not in session: return redirect(url_for('login'))
    appointment = get_entity_by_id("appointments", appointment_id)
    if appointment:
        new_status = request.form.get("new_status")
        if new_status in ["Completed", "Cancelled"]:
            appointment_index = next((i for i, a in enumerate(hms_data["appointments"]) if a["id"] == appointment_id), -1)
            if appointment_index != -1:
                hms_data["appointments"][appointment_index]["status"] = new_status
                hms_data["appointments"][appointment_index]["updated_at"] = datetime.datetime.now().isoformat()
                save_data(hms_data)
                flash(f"Appointment status updated to {new_status}.", "success")
        else: flash("Invalid status update.", "danger")
    else: flash("Appointment not found.", "danger")
    return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))

@app.route("/appointment/delete/<appointment_id>", methods=["POST"])
def delete_appointment(appointment_id):
    if 'username' not in session: return redirect(url_for('login'))
    original_len = len(hms_data["appointments"])
    hms_data["appointments"] = [a for a in hms_data["appointments"] if a["id"] != appointment_id]
    hms_data["medical_notes"] = [n for n in hms_data["medical_notes"] if not (n.get("entity_type") == "appointment" and n.get("entity_id") == appointment_id)]
    hms_data["prescriptions"] = [p for p in hms_data["prescriptions"] if p.get("appointment_id") != appointment_id]
    hms_data["invoices"] = [i for i in hms_data["invoices"] if i.get("appointment_id") != appointment_id]

    if len(hms_data["appointments"]) < original_len:
        save_data(hms_data)
        flash("Appointment and related data deleted successfully.", "success")
    else: flash("Appointment not found for deletion.", "warning")
    return redirect(url_for("list_appointments"))

# --- Prescription Management ---
@app.route("/prescription/save/<appointment_id>", methods=["POST"])
def save_prescription(appointment_id):
    if 'username' not in session: return redirect(url_for('login'))
    appointment = get_entity_by_id("appointments", appointment_id)
    if not appointment or appointment.get("status") != "Completed":
        flash("Prescriptions can only be added/updated for completed appointments.", "warning")
        return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))

    medications = request.form.get("medications")
    instructions = request.form.get("instructions")

    existing_prescription = get_prescription_for_appointment(appointment_id)
    if existing_prescription:
        idx = hms_data["prescriptions"].index(existing_prescription)
        hms_data["prescriptions"][idx].update({
            "medications": medications, "instructions": instructions,
            "updated_at": datetime.datetime.now().isoformat(), "updated_by": session.get('username', 'System')
        })
        flash("Prescription updated successfully.", "success")
    else:
        new_prescription = {
            "id": generate_uuid(), "appointment_id": appointment_id,
            "patient_id": appointment.get("patient_id"), "doctor_id": appointment.get("doctor_id"),
            "medications": medications, "instructions": instructions,
            "created_at": datetime.datetime.now().isoformat(), "created_by": session.get('username', 'System')
        }
        hms_data["prescriptions"].append(new_prescription)
        flash("Prescription added successfully.", "success")
    save_data(hms_data)
    return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))

# --- Invoice/Billing Management ---
@app.route("/invoice/save/<appointment_id>", methods=["POST"])
def save_invoice(appointment_id):
    if 'username' not in session: return redirect(url_for('login'))
    appointment = get_entity_by_id("appointments", appointment_id)
    if not appointment or appointment.get("status") != "Completed":
        flash("Invoices can only be managed for completed appointments.", "warning")
        return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))

    item_description = request.form.get("item_description")
    try:
        amount = float(request.form.get("amount"))
        if amount < 0: raise ValueError("Amount cannot be negative.")
    except (ValueError, TypeError):
        flash("Invalid or negative amount for invoice.", "danger")
        return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))
    status = request.form.get("status")

    existing_invoice = get_invoice_for_appointment(appointment_id)
    if existing_invoice:
        idx = hms_data["invoices"].index(existing_invoice)
        hms_data["invoices"][idx].update({
            "item_description": item_description, "amount": amount, "status": status,
            "updated_at": datetime.datetime.now().isoformat(), "updated_by": session.get('username', 'System')
        })
        flash("Invoice updated successfully.", "success")
    else:
        new_invoice = {
            "id": generate_uuid(), "appointment_id": appointment_id,
            "patient_id": appointment.get("patient_id"), "doctor_id": appointment.get("doctor_id"),
            "item_description": item_description, "amount": amount, "status": status,
            "invoice_date": datetime.date.today().isoformat(),
            "created_at": datetime.datetime.now().isoformat(), "created_by": session.get('username', 'System')
        }
        hms_data["invoices"].append(new_invoice)
        flash("Invoice created successfully.", "success")
    save_data(hms_data)
    return redirect(url_for("list_appointments", _anchor=f"appt-{appointment_id}"))


# --- Medical Notes (shared by patient and appointment) ---
def medical_notes_html(entity_id, entity_type):
    notes_html = f"<div class='related-info-section'><h4><span class='icon'>📝</span> Medical Notes</h4>"
    notes = [n for n in hms_data["medical_notes"] if n.get("entity_id") == entity_id and n.get("entity_type") == entity_type]
    if notes:
        notes_html += "<ul>"
        for note in sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True):
            created_dt = datetime.datetime.fromisoformat(note.get("created_at", datetime.datetime.min.isoformat()))
            notes_html += f"<li><strong>Noted on {created_dt.strftime('%Y-%m-%d %H:%M')} by {Markup.escape(note.get('user', 'System'))}:</strong> {Markup.escape(note.get('text', ''))}</li>"
        notes_html += "</ul>"
    else:
        notes_html += "<p>No notes found for this item.</p>"

    notes_html += f"""
    <form method="POST" action="{url_for('add_note')}">
        <input type="hidden" name="entity_id" value="{entity_id}">
        <input type="hidden" name="entity_type" value="{entity_type}">
        <input type="hidden" name="return_url" value="{request.url}">
        <div class="form-group">
            <label for="note_text_{entity_id}_{entity_type}">Add New Note:</label>
            <textarea name="note_text" id="note_text_{entity_id}_{entity_type}" rows="3" required></textarea>
        </div>
        <button type="submit" class="button-success"><span class="icon">➕</span> Add Note</button>
    </form></div>
    """
    return notes_html

@app.route("/note/add", methods=["POST"])
def add_note():
    if 'username' not in session: return redirect(url_for('login'))
    entity_id = request.form.get("entity_id")
    entity_type = request.form.get("entity_type")
    note_text = request.form.get("note_text")
    return_url = request.form.get("return_url", url_for('dashboard'))

    if not all([entity_id, entity_type, note_text]):
        flash("Missing data for adding note.", "danger")
        return redirect(return_url)

    new_note = {
        "id": generate_uuid(), "entity_id": entity_id, "entity_type": entity_type,
        "text": note_text, "created_at": datetime.datetime.now().isoformat(),
        "user": session.get('username', 'System')
    }
    hms_data["medical_notes"].append(new_note)
    save_data(hms_data)
    flash("Medical note added successfully.", "success")
    
    anchor = ""
    if entity_type == 'appointment':
        anchor = f"appt-{entity_id}"
    
    # Check if return_url already has a fragment
    base_return_url = return_url.split('#')[0]
    if anchor:
        return redirect(f"{base_return_url}#{anchor}")
    return redirect(base_return_url)


if __name__ == "__main__":
    app.run(debug=True, port=5003)