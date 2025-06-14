import os
import easyocr
import pandas as pd
import re
import streamlit as st
from PIL import Image

# Set up upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load vehicle registration data
@st.cache_data
def load_data():
    df = pd.read_excel("vehicle_registration_data_complete.xlsx", dtype=str)
    df["Plate Number Cleaned"] = df["Plate Number"].astype(str).str.replace(r"[^A-Za-z0-9]", "", regex=True).str.upper().str.strip()
    return df

df = load_data()

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

# Utility to clean plate number
def clean_text(text):
    return "".join(re.findall(r"[A-Za-z0-9]+", text)).upper()

# Streamlit UI
st.set_page_config(page_title="Number Plate Scanner", layout="centered")
st.title("🚗 Number Plate Scanner")
st.write("Upload a vehicle image to detect the number plate and fetch its registration details.")

# File uploader
uploaded_file = st.file_uploader("Upload Vehicle Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    image.save(file_path)

    st.image(image, caption="Uploaded Vehicle Image", use_column_width=True)

    with st.spinner("🔍 Detecting number plate..."):
        results = reader.readtext(file_path)
        extracted_text = clean_text("".join([res[1] for res in results]))

        st.subheader("📋 Detected Number Plate:")
        st.code(extracted_text)

        matched_info = df[df["Plate Number Cleaned"] == extracted_text]

        if not matched_info.empty:
            st.success("✅ Vehicle Found:")
            st.dataframe(matched_info)
        else:
            st.warning("❌ Vehicle not found in the database.")
