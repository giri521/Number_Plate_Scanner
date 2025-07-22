Certainly! Here's the full **`README.md`** text for your **Vehicle Number Plate Scanner Web App** project:

---

```markdown
# 🚘 Vehicle Number Plate Scanner Web App

An AI-powered Flask web application that scans vehicle number plates from images or camera input using **EasyOCR**, validates the format, fetches vehicle details from a local JSON file, and generates downloadable PDF reports. It also stores scan history using **Backendless**.

---

## 📌 Project Description

This project is a smart vehicle verification system that:

- Extracts license plate text using **OCR** (EasyOCR)
- Corrects common OCR character errors (`O ↔ 0`, `I ↔ 1`, etc.)
- Validates Indian license plate format (`e.g., AP31AB1234`)
- Looks up vehicle data from a local `data.json` file
- Generates **PDF reports** with all vehicle details
- Saves all scanned data with timestamp and image to **Backendless**
- Displays recent scan history with PDF download options

It supports input via image upload, camera capture, and manual entry.

---

## 🔧 Features

- 📷 Live OCR from uploaded images or camera
- ✍️ Manual number plate entry support
- ✅ Format validation and auto-correction
- 📄 PDF report generation
- ☁️ Scan history stored in Backendless cloud
- 🧾 View and download past scan reports
- 📊 JSON-based vehicle detail lookup

---

## 🗂️ Folder Structure

```

number\_plate/
├── app.py                  # Main Flask app
├── data.json               # Vehicle data source
├── static/
│   ├── uploads/            # Uploaded vehicle images
│   └── \*.pdf               # Generated vehicle reports
├── templates/
│   ├── index.html          # Main page
│   └── history.html        # Scan history page
├── requirements.txt
└── README.md

````

---

## 💻 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/number_plate.git
cd number_plate
````

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Flask App

```bash
python app.py
```

Then open your browser and go to:
➡️ `http://127.0.0.1:5000`

---

## 🌐 Backendless Setup

The app uses **Backendless** for cloud history storage.
Make sure to replace these in `app.py` if you're using your own account:

```python
APP_ID = "YOUR_APP_ID"
API_KEY = "YOUR_API_KEY"
```

Default values:

* App ID: `2F27DC29-E3EF-4551-A9CD-9CF80F2A9BC7`
* API Key: `87C0CEAC-C4CA-41E8-BF89-F58EBD917334`

---

## 📥 API Endpoints

| Endpoint            | Method | Description                       |
| ------------------- | ------ | --------------------------------- |
| `/`                 | GET    | Home page                         |
| `/upload`           | POST   | Upload image for OCR              |
| `/manual`           | POST   | Enter number plate manually       |
| `/camera`           | POST   | Camera capture (same as upload)   |
| `/download/<plate>` | GET    | Download PDF report for the plate |
| `/history_page`     | GET    | View full scan history            |

---

## 📄 Sample `data.json` Entry

```json
{
  "AP31AB1234": {
    "owner": "Rahul Sharma",
    "model": "Hyundai i20",
    "color": "White",
    "address": "Hyderabad",
    "registration_year": 2018,
    "expiry": "2028-03-01",
    "rc_number": "RC654321",
    "license_number": "DL123456789",
    "chassis_number": "CHS987654321",
    "engine_number": "ENG987654321",
    "seating_capacity": 5,
    "fuel_type": "Petrol",
    "rto": "Hyderabad South",
    "state": "Telangana"
  }
}
```

---

## 📦 Requirements

All dependencies are listed in `requirements.txt`:

```txt
Flask
easyocr
fpdf
requests
opencv-python
Pillow
torch
torchvision
numpy
Werkzeug
```

Install with:

```bash
pip install -r requirements.txt
```

---

## 📜 License

This project is open-source and free to use for educational and non-commercial purposes.

---

## 🤝 Acknowledgements

* [EasyOCR](https://github.com/JaidedAI/EasyOCR)
* [Backendless](https://backendless.com/)
* [FPDF](https://pyfpdf.readthedocs.io/)

---

> Made with 💡 by Giri Vennapusa

```

Let me know if you'd like me to auto-generate the `index.html`, `history.html`, or the `data.json` starter file too!
```
