import os
import easyocr
import pandas as pd
import re
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import time

# Set up upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load vehicle registration data
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("vehicle_registration_data_complete.xlsx", dtype=str)
        df["Plate Number Cleaned"] = df["Plate Number"].astype(str).str.replace(r"[^A-Za-z0-9]", "", regex=True).str.upper().str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

df = load_data()

# Initialize EasyOCR reader
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['en'])

reader = load_ocr_model()

# Utility to clean plate number
def clean_text(text):
    return "".join(re.findall(r"[A-Za-z0-9]+", text)).upper()

# Streamlit UI Configuration
st.set_page_config(
    page_title="Live Number Plate Scanner",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Main styles */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header styles */
    .css-1v3fvcr {
        color: #2c3e50;
        text-align: center;
        padding-bottom: 1rem;
        border-bottom: 2px solid #3498db;
    }
    
    /* Camera container */
    .stCamera {
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        overflow: hidden;
        border: 3px solid #3498db;
    }
    
    /* Detection results */
    .stCodeBlock {
        border-radius: 10px;
        background: #2c3e50 !important;
        color: white !important;
        font-size: 1.2rem !important;
        padding: 1rem !important;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Spinner animation */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .spinner {
        border: 4px solid rgba(0, 0, 0, 0.1);
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border-left-color: #3498db;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# App Title
st.title("🚗 Live Number Plate Scanner")
st.markdown("Use your device camera to detect number plates in real-time")

# Initialize session state
if 'last_detection' not in st.session_state:
    st.session_state.last_detection = None
if 'detection_history' not in st.session_state:
    st.session_state.detection_history = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Detection cooldown (seconds)
DETECTION_COOLDOWN = 5

# Main App Layout
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Live Camera Feed")
    st.markdown("Position the vehicle's number plate in the camera view")
    
    # Streamlit camera input
    img_file_buffer = st.camera_input("Take a picture of a vehicle", key="camera")
    
    if img_file_buffer is not None and not st.session_state.processing:
        st.session_state.processing = True
        
        # Convert image to OpenCV format
        bytes_data = img_file_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        
        # Save temporary image
        temp_path = os.path.join(UPLOAD_FOLDER, "temp_capture.jpg")
        cv2.imwrite(temp_path, cv2_img)
        
        with st.spinner("🔍 Detecting number plate..."):
            try:
                # Perform OCR
                results = reader.readtext(cv2_img)
                extracted_text = clean_text("".join([res[1] for res in results]))
                
                if extracted_text and (st.session_state.last_detection != extracted_text or 
                                     (time.time() - st.session_state.get('last_detection_time', 0)) > DETECTION_COOLDOWN):
                    st.session_state.last_detection = extracted_text
                    st.session_state.last_detection_time = time.time()
                    st.session_state.detection_history.append(extracted_text)
                    
                    # Check database
                    matched_info = df[df["Plate Number Cleaned"] == extracted_text]
                    
                    if not matched_info.empty:
                        result = {
                            "status": "success",
                            "plate": extracted_text,
                            "data": matched_info
                        }
                    else:
                        result = {
                            "status": "not_found",
                            "plate": extracted_text
                        }
                    
                    # Store result in session state
                    st.session_state.last_result = result
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
            finally:
                st.session_state.processing = False

with col2:
    st.subheader("Detection Results")
    
    # Show last detection result
    if 'last_result' in st.session_state:
        result = st.session_state.last_result
        
        if result["status"] == "success":
            st.success(f"✅ Detected Plate: `{result['plate']}`")
            st.dataframe(result["data"])
            
            # Show vehicle image if available
            if "Vehicle Image" in result["data"].columns:
                img_path = result["data"]["Vehicle Image"].iloc[0]
                if isinstance(img_path, str) and os.path.exists(img_path):
                    st.image(img_path, caption="Registered Vehicle", use_column_width=True)
        else:
            st.warning(f"❌ Detected Plate: `{result['plate']}` (Not found in database)")
    else:
        st.info("No plate detected yet. Point your camera at a vehicle's license plate.")
    
    # Show detection history
    if st.session_state.detection_history:
        st.subheader("Detection History")
        history_cols = st.columns(3)
        
        for i, plate in enumerate(st.session_state.detection_history[-6:]):  # Show last 6 plates
            with history_cols[i % 3]:
                st.code(plate)

# Manual upload fallback
st.markdown("---")
st.subheader("Alternative: Upload an Image")
uploaded_file = st.file_uploader("Choose a vehicle image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    
    with st.spinner("🔍 Processing uploaded image..."):
        try:
            # Save temporary image
            temp_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
            image.save(temp_path)
            
            # Perform OCR
            results = reader.readtext(np.array(image))
            extracted_text = clean_text("".join([res[1] for res in results]))
            
            st.subheader("Detection Results")
            st.code(extracted_text)
            
            # Check database
            matched_info = df[df["Plate Number Cleaned"] == extracted_text]
            
            if not matched_info.empty:
                st.success("✅ Vehicle Found:")
                st.dataframe(matched_info)
                
                if "Vehicle Image" in matched_info.columns:
                    img_path = matched_info["Vehicle Image"].iloc[0]
                    if isinstance(img_path, str) and os.path.exists(img_path):
                        st.image(img_path, caption="Registered Vehicle", use_column_width=True)
            else:
                st.warning("❌ Vehicle not found in the database.")
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
