import streamlit as st
import easyocr
import pandas as pd
import numpy as np
import os
import re
from PIL import Image

# Initialize EasyOCR
reader = easyocr.Reader(['en'])

# Load dataset
df = pd.read_excel("vehicle_registration_data_complete.xlsx", dtype=str)
df["Plate Number Cleaned"] = df["Plate Number"].astype(str).str.replace(r"[^A-Za-z0-9]", "", regex=True).str.upper().str.strip()

# Function to clean OCR text
def clean_text(text):
    return "".join(re.findall(r"[A-Za-z0-9]+", text)).upper()

# Streamlit UI
st.set_page_config(page_title="Number Plate Scanner", layout="centered")
st.title("🚗 Number Plate Scanner")

uploaded_file = st.file_uploader("Upload a vehicle number plate image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Display uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # Save file temporarily
    temp_filepath = "temp_image.jpg"
    image.save(temp_filepath)

    # Perform OCR
    with st.spinner("Extracting text from image..."):
        result = reader.readtext(temp_filepath)
        extracted_text = clean_text("".join([text[1] for text in result]))

    # Display extracted text
    st.subheader("📌 Extracted Text:")
    st.write(f"**{extracted_text}**")

    # Search in dataset
    vehicle_info = df[df["Plate Number Cleaned"] == extracted_text]

    if not vehicle_info.empty:
        details = vehicle_info.iloc[0].to_dict()
        st.success("✅ Vehicle Found!")
        st.subheader("🚘 Vehicle Details:")
        for key, value in details.items():
            st.write(f"**{key}:** {value}")
    else:
        st.error("❌ Vehicle not found in the database.")

    # Delete temporary file
    os.remove(temp_filepath)
