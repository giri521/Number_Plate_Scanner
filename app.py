import streamlit as st
import easyocr
import cv2
import numpy as np
from PIL import Image
import pandas as pd

# Load dataset
df = pd.read_excel("vehicle_data.xlsx")  # Ensure the dataset is in the same directory

# Initialize OCR
reader = easyocr.Reader(['en'])

def extract_number_plate(image):
    """Extract text from the image using EasyOCR"""
    image = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    results = reader.readtext(gray)

    detected_texts = [text[1] for text in results if len(text[1]) >= 6]
    return " ".join(detected_texts)

# Streamlit UI
st.title("📸 Number Plate Scanner")

uploaded_image = st.file_uploader("Upload a Number Plate Image", type=["jpg", "png", "jpeg"])

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    if st.button("🔍 Scan Number Plate"):
        plate_text = extract_number_plate(image)
        if plate_text:
            st.success(f"Detected Number Plate: **{plate_text}**")

            # Search for details in the dataset
            vehicle_details = df[df['Number Plate'] == plate_text]
            if not vehicle_details.empty:
                st.subheader("Vehicle Details:")
                st.write(vehicle_details.to_dict(orient="records"))
            else:
                st.warning("No details found for this number plate.")
        else:
            st.error("Number plate not detected. Try another image.")

