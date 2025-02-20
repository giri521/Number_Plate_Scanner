from flask import Flask, render_template, request, jsonify
import os
import easyocr
import pandas as pd
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize EasyOCR
reader = easyocr.Reader(['en'])

# Load dataset
df = pd.read_excel("vehicle_registration_data_complete.xlsx", dtype=str)
df["Plate Number Cleaned"] = df["Plate Number"].astype(str).str.replace(r"[^A-Za-z0-9]", "", regex=True).str.upper().str.strip()

def clean_text(text):
    return "".join(re.findall(r"[A-Za-z0-9]+", text)).upper()  # Remove special characters

@app.route("/")
def index():
    return render_template("index.html", vehicle_info=None)

@app.route("/capture", methods=["POST"])
def capture():
    if "image" not in request.files:
        return jsonify({"error": "No image received"})

    file = request.files["image"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Perform OCR
    result = reader.readtext(filepath)
    extracted_text = clean_text("".join([text[1] for text in result]))

    # Search in dataset
    vehicle_info = df[df["Plate Number Cleaned"] == extracted_text]

    if not vehicle_info.empty:
        details = vehicle_info.iloc[0].to_dict()
        return jsonify({"text": extracted_text, "details": details, "image_path": filepath})
    else:
        return jsonify({"text": extracted_text, "details": {"error": "Vehicle not found"}, "image_path": filepath})

if __name__ == "__main__":
    app.run(debug=True)
