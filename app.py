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

# Initialize EasyOCR reader with optimized settings
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(
        ['en'],
        gpu=True,  # Enable GPU acceleration if available
        model_storage_directory='model_files',
        download_enabled=True
    )

reader = load_ocr_model()

# Utility to clean plate number with improved pattern matching
def clean_text(text):
    # Improved pattern for common plate formats (adjust based on your country's format)
    plate_pattern = re.compile(r"""
        (?:[A-Z]{2,3}[- ]?\d{1,4})|        # AB-1234 or ABC-123
        (?:[A-Z]{1,2}\d{1,4}[A-Z]{1,3})|   # A1234BC or AB123CD
        (?:\d{1,4}[A-Z]{2,3})|            # 1234AB or 123ABC
        (?:[A-Z]{1,2}\d{1,4})|            # A1234 or AB1234
        (?:[A-Z]+\d+[A-Z]*)                # Any combination of letters and numbers
    """, re.VERBOSE)
    
    matches = plate_pattern.findall(text.upper())
    if matches:
        # Take the longest match (most likely to be the plate)
        best_match = max(matches, key=len)
        # Remove all non-alphanumeric characters
        return re.sub(r'[^A-Z0-9]', '', best_match)
    return ""

# Image preprocessing function to improve OCR accuracy
def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Apply sharpening
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(thresh, -1, kernel)
    
    # Apply dilation to make text thicker
    kernel = np.ones((2,2), np.uint8)
    dilated = cv2.dilate(sharpened, kernel, iterations=1)
    
    return dilated

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
    
    /* Detection box */
    .detection-box {
        position: absolute;
        border: 2px solid #FF0000;
        background-color: rgba(255, 0, 0, 0.2);
        z-index: 1000;
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
if 'show_preprocessed' not in st.session_state:
    st.session_state.show_preprocessed = False

# Detection cooldown (seconds)
DETECTION_COOLDOWN = 5

# Main App Layout
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Live Camera Feed")
    st.markdown("Position the vehicle's number plate in the camera view")
    
    # Add toggle for showing preprocessed image
    st.session_state.show_preprocessed = st.checkbox("Show preprocessed image (for debugging)")
    
    # Streamlit camera input
    img_file_buffer = st.camera_input("Take a picture of a vehicle", key="camera")
    
    if img_file_buffer is not None and not st.session_state.processing:
        st.session_state.processing = True
        
        try:
            # Convert image to OpenCV format
            bytes_data = img_file_buffer.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            
            # Preprocess the image
            preprocessed_img = preprocess_image(cv2_img)
            
            if st.session_state.show_preprocessed:
                st.image(preprocessed_img, caption="Preprocessed Image", use_column_width=True, channels="GRAY")
            
            # Save temporary image
            temp_path = os.path.join(UPLOAD_FOLDER, "temp_capture.jpg")
            cv2.imwrite(temp_path, preprocessed_img)
            
            with st.spinner("🔍 Detecting number plate..."):
                start_time = time.time()
                
                # Perform OCR with optimized parameters
                results = reader.readtext(
                    preprocessed_img,
                    decoder='beamsearch',  # More accurate but slightly slower
                    beamWidth=5,           # Balance between speed and accuracy
                    contrast_ths=0.1,      # Better for low-contrast images
                    adjust_contrast=0.7,   # Helps with varying lighting
                    text_threshold=0.7,    # Higher threshold for more confident detections
                    link_threshold=0.4,    # Helps with connected characters
                    mag_ratio=1.5          # Helps with small text
                )
                
                # Extract and clean all potential plate numbers
                potential_plates = [clean_text(res[1]) for res in results]
                potential_plates = [plate for plate in potential_plates if len(plate) >= 4]  # Filter too short texts
                
                if potential_plates:
                    # Get the most likely plate (longest match)
                    extracted_text = max(potential_plates, key=len)
                    
                    processing_time = time.time() - start_time
                    st.info(f"Processing time: {processing_time:.2f} seconds")
                    
                    if extracted_text and (st.session_state.last_detection != extracted_text or 
                                         (time.time() - st.session_state.get('last_detection_time', 0)) > DETECTION_COOLDOWN):
                        st.session_state.last_detection = extracted_text
                        st.session_state.last_detection_time = time.time()
                        st.session_state.detection_history.append(extracted_text)
                        
                        # Check database
                        matched_info = df[df["Plate Number Cleaned"].str.contains(extracted_text, case=False, na=False)]
                        
                        if not matched_info.empty:
                            result = {
                                "status": "success",
                                "plate": extracted_text,
                                "data": matched_info
                            }
                        else:
                            # Try partial matches if exact match not found
                            partial_matches = df[df["Plate Number Cleaned"].str.contains(extracted_text[:4], case=False, na=False)]
                            if not partial_matches.empty:
                                result = {
                                    "status": "partial_match",
                                    "plate": extracted_text,
                                    "data": partial_matches
                                }
                            else:
                                result = {
                                    "status": "not_found",
                                    "plate": extracted_text
                                }
                        
                        # Store result in session state
                        st.session_state.last_result = result
                else:
                    st.warning("No potential plate numbers detected. Try adjusting the camera angle.")
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
            st.dataframe(result["data"].head())  # Show only first few matches
            
            # Show vehicle image if available
            if "Vehicle Image" in result["data"].columns:
                img_path = result["data"]["Vehicle Image"].iloc[0]
                if isinstance(img_path, str) and os.path.exists(img_path):
                    st.image(img_path, caption="Registered Vehicle", use_column_width=True)
        elif result["status"] == "partial_match":
            st.warning(f"⚠️ Partial Match: `{result['plate']}`")
            st.dataframe(result["data"].head())
            st.info("This is a partial match. Please verify the plate number.")
        else:
            st.warning(f"❌ Detected Plate: `{result['plate']}` (Not found in database)")
    else:
        st.info("No plate detected yet. Point your camera at a vehicle's license plate.")
    
    # Show detection history
    if st.session_state.detection_history:
        st.subheader("Detection History")
        history_cols = st.columns(3)
        
        for i, plate in enumerate(reversed(st.session_state.detection_history[-6:])):  # Show last 6 plates (newest first)
            with history_cols[i % 3]:
                st.code(plate)

# Manual upload fallback with improved processing
st.markdown("---")
st.subheader("Alternative: Upload an Image")
uploaded_file = st.file_uploader("Choose a vehicle image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        with st.spinner("🔍 Processing uploaded image..."):
            # Convert to OpenCV format
            cv2_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocess the image
            preprocessed_img = preprocess_image(cv2_img)
            
            if st.session_state.show_preprocessed:
                st.image(preprocessed_img, caption="Preprocessed Image", use_column_width=True, channels="GRAY")
            
            # Perform OCR
            results = reader.readtext(
                preprocessed_img,
                decoder='beamsearch',
                beamWidth=5,
                contrast_ths=0.1,
                adjust_contrast=0.7,
                text_threshold=0.7,
                link_threshold=0.4,
                mag_ratio=1.5
            )
            
            # Extract and clean all potential plate numbers
            potential_plates = [clean_text(res[1]) for res in results]
            potential_plates = [plate for plate in potential_plates if len(plate) >= 4]  # Filter too short texts
            
            if potential_plates:
                # Get the most likely plate (longest match)
                extracted_text = max(potential_plates, key=len)
                
                st.subheader("Detection Results")
                st.code(extracted_text)
                
                # Check database
                matched_info = df[df["Plate Number Cleaned"].str.contains(extracted_text, case=False, na=False)]
                
                if not matched_info.empty:
                    st.success("✅ Vehicle Found:")
                    st.dataframe(matched_info.head())
                    
                    if "Vehicle Image" in matched_info.columns:
                        img_path = matched_info["Vehicle Image"].iloc[0]
                        if isinstance(img_path, str) and os.path.exists(img_path):
                            st.image(img_path, caption="Registered Vehicle", use_column_width=True)
                else:
                    # Try partial matches if exact match not found
                    partial_matches = df[df["Plate Number Cleaned"].str.contains(extracted_text[:4], case=False, na=False)]
                    if not partial_matches.empty:
                        st.warning("⚠️ Partial Match Found:")
                        st.dataframe(partial_matches.head())
                        st.info("This is a partial match. Please verify the plate number.")
                    else:
                        st.warning("❌ Vehicle not found in the database.")
            else:
                st.warning("No potential plate numbers detected in the uploaded image.")
    except Exception as e:
        st.error(f"Error processing uploaded image: {str(e)}")

# Add tips for better detection
st.markdown("---")
st.subheader("Tips for Better Detection")
st.markdown("""
1. **Positioning**: Ensure the number plate is clearly visible and centered in the frame.
2. **Lighting**: Good lighting helps - avoid shadows and glare on the plate.
3. **Distance**: Get close enough so the plate fills a significant portion of the image.
4. **Angle**: Try to capture the plate straight-on rather than at an angle.
5. **Focus**: Make sure the plate is in focus - blurry images are harder to read.
""")
