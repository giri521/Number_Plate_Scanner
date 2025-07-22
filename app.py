from flask import Flask, render_template, request, jsonify, send_file
import os
import easyocr
import json
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from fpdf import FPDF
import requests

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

# Initialize EasyOCR reader
try:
    reader = easyocr.Reader(['en'], gpu=False)
except Exception as e:
    print(f"Failed to initialize EasyOCR: {e}")
    reader = None

# Load data from data.json
try:
    with open("data.json", "r") as f:
        vehicle_data = json.load(f)
except Exception as e:
    print(f"Failed to load vehicle data: {e}")
    vehicle_data = {}

# Backendless setup
APP_ID = "2F27DC29-E3EF-4551-A9CD-9CF80F2A9BC7"
API_KEY = "87C0CEAC-C4CA-41E8-BF89-F58EBD917334"
BACKENDLESS_URL = f"https://api.backendless.com/{APP_ID}/{API_KEY}/data/VehicleHistory"
BACKENDLESS_TABLE_URL = f"https://api.backendless.com/{APP_ID}/{API_KEY}/data/"

def create_table_if_not_exists():
    try:
        # Check if table exists by trying to count records
        response = requests.get(f"{BACKENDLESS_URL}/count", timeout=5)
        if response.status_code == 404:
            # Table doesn't exist, create it
            table_definition = {
                "name": "VehicleHistory",
                "columns": {
                    "plate": {"type": "STRING", "required": True},
                    "timestamp": {"type": "DATETIME", "required": True},
                    "owner": {"type": "STRING"},
                    "model": {"type": "STRING"},
                    "color": {"type": "STRING"},
                    "address": {"type": "STRING"},
                    "registration_year": {"type": "INTEGER"},
                    "expiry": {"type": "STRING"},
                    "rc_number": {"type": "STRING"},
                    "license_number": {"type": "STRING"},
                    "chassis_number": {"type": "STRING"},
                    "engine_number": {"type": "STRING"},
                    "seating_capacity": {"type": "INTEGER"},
                    "fuel_type": {"type": "STRING"},
                    "rto": {"type": "STRING"},
                    "state": {"type": "STRING"},
                    "image_path": {"type": "STRING"}
                }
            }
            create_response = requests.post(
                f"{BACKENDLESS_TABLE_URL}",
                json=table_definition,
                timeout=5
            )
            create_response.raise_for_status()
            print("Created VehicleHistory table in Backendless")
    except Exception as e:
        print(f"Error checking/creating table: {e}")

# Create table on startup
create_table_if_not_exists()

def correct_ocr_errors(text):
    if not text or len(text) != 10:
        return text  # skip invalid inputs

    corrected = list(text.upper())

    # Define character replacements for different positions
    replacements = {
        'letters': {'0': 'O', '1': 'I', '5': 'S', '8': 'B'},
        'digits': {'O': '0', 'I': '1', 'S': '5', 'B': '8'}
    }

    # Apply corrections based on position
    for i, char in enumerate(corrected):
        if i in [0, 1, 4, 5]:  # Letter positions
            if char in replacements['letters']:
                corrected[i] = replacements['letters'][char]
        elif i in [2, 3, 6, 7, 8, 9]:  # Digit positions
            if char in replacements['digits']:
                corrected[i] = replacements['digits'][char]

    return ''.join(corrected)

def save_history(plate, image_path=None):
    try:
        if plate in vehicle_data:
            entry = vehicle_data[plate].copy()
            entry['plate'] = plate
            entry['timestamp'] = datetime.now().isoformat()
            if image_path:
                entry['image_path'] = image_path
            
            response = requests.post(BACKENDLESS_URL, json=entry, timeout=5)
            response.raise_for_status()
            return True
        return False
    except Exception as e:
        print(f"Failed to save history: {e}")
        return False

def get_recent_history(limit=100):
    try:
        params = {'pageSize': limit, 'sortBy': 'timestamp desc'}
        response = requests.get(BACKENDLESS_URL, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch history: {e}")
        return []

def validate_plate_format(plate):
    return bool(re.match(r"^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$", plate))

def generate_pdf(data, filepath):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Vehicle Details Report", ln=True, align='C')
        pdf.ln(10)
        
        # Add image if available
        if data.get('image_path') and os.path.exists(data['image_path']):
            pdf.image(data['image_path'], x=10, y=30, w=40)
            pdf.set_y(80)  # Move below image
        
        # Reset font for details
        pdf.set_font("Arial", size=12)
        
        # Add all details
        fields = [
            ("License Plate", data.get('plate', '')),
            ("Owner", data.get('owner', '')),
            ("Model", data.get('model', '')),
            ("Color", data.get('color', '')),
            ("Address", data.get('address', '')),
            ("Registration Year", data.get('registration_year', '')),
            ("Expiry Date", data.get('expiry', '')),
            ("RC Number", data.get('rc_number', '')),
            ("License Number", data.get('license_number', '')),
            ("Chassis Number", data.get('chassis_number', '')),
            ("Engine Number", data.get('engine_number', '')),
            ("Seating Capacity", data.get('seating_capacity', '')),
            ("Fuel Type", data.get('fuel_type', '')),
            ("RTO", data.get('rto', '')),
            ("State", data.get('state', ''))
        ]
        
        for label, value in fields:
            pdf.cell(200, 10, txt=f"{label}: {value}", ln=True)
        
        # Add timestamp
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        
        pdf.output(filepath)
        return True
    except Exception as e:
        print(f"Failed to generate PDF: {e}")
        return False

@app.template_filter('format_datetime')
def format_datetime(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return value

@app.route("/")
def index():
    history = get_recent_history(2)  # Only show 2 most recent on main page
    return render_template("index.html", history=history)

@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    try:
        file.save(filepath)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {e}"}), 500

    if not reader:
        return jsonify({"error": "OCR engine not available"}), 500

    try:
        result = reader.readtext(filepath)
        extracted_text = ''.join([text[1] for text in result]).upper()
        cleaned_text = re.sub(r"[^A-Z0-9]", "", extracted_text)
        corrected_text = correct_ocr_errors(cleaned_text)

        response = {
            "extracted_text": corrected_text,
            "image_path": filepath
        }

        if validate_plate_format(corrected_text):
            if corrected_text in vehicle_data:
                details = vehicle_data[corrected_text]
                details['plate'] = corrected_text  # Include plate in details
                details['image_path'] = filepath  # Include image path
                response["details"] = details
                
                # Save complete history with image path
                save_history(corrected_text, filepath)

                # Generate PDF report
                pdf_path = os.path.join("static", f"{corrected_text}.pdf")
                if generate_pdf(details, pdf_path):
                    response["pdf_url"] = f"/download/{corrected_text}"
            else:
                response["details"] = {"error": "Vehicle not found"}
        else:
            response["details"] = {"error": "Invalid plate format"}

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Processing failed: {e}"}), 500

@app.route("/manual", methods=["POST"])
def manual():
    plate = request.form.get("plate", "").upper()
    cleaned_text = re.sub(r"[^A-Z0-9]", "", plate)
    corrected_text = correct_ocr_errors(cleaned_text)

    response = {"extracted_text": corrected_text}

    if validate_plate_format(corrected_text):
        if corrected_text in vehicle_data:
            details = vehicle_data[corrected_text]
            details['plate'] = corrected_text  # Include plate in details
            response["details"] = details
            
            # Save complete history
            save_history(corrected_text)

            # Generate PDF report
            pdf_path = os.path.join("static", f"{corrected_text}.pdf")
            if generate_pdf(details, pdf_path):
                response["pdf_url"] = f"/download/{corrected_text}"
        else:
            response["details"] = {"error": "Vehicle not found"}
    else:
        response["details"] = {"error": "Invalid plate format"}

    return jsonify(response)

@app.route("/download/<plate>")
def download(plate):
    pdf_path = os.path.join("static", f"{plate}.pdf")
    if not os.path.exists(pdf_path):
        return "File not found", 404
    return send_file(pdf_path, as_attachment=True)

@app.route("/camera", methods=["POST"])
def camera():
    return upload()  # Reuse the upload functionality

@app.route("/history_page")
def history_page():
    try:
        # Fetch all history records from Backendless
        history = get_recent_history(100)
        
        # Ensure PDFs exist for each entry
        for entry in history:
            if 'plate' in entry:
                pdf_path = os.path.join("static", f"{entry['plate']}.pdf")
                if not os.path.exists(pdf_path):
                    # Regenerate PDF if missing
                    generate_pdf(entry, pdf_path)
        
        return render_template("history.html", history=history)
    except Exception as e:
        print(f"Failed to fetch history: {e}")
        return render_template("history.html", history=[])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)