import os
import easyocr
import pandas as pd
import re
import streamlit as st
from PIL import Image
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import threading
import queue
import time

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
st.set_page_config(page_title="Live Number Plate Scanner", layout="centered", page_icon="🚗")
st.title("🚗 Live Number Plate Scanner")
st.write("Use your device camera to detect number plates in real-time and fetch registration details.")

# CSS for better UI
st.markdown("""
<style>
    /* Main container */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header */
    .css-1v3fvcr {
        color: #2c3e50;
        text-align: center;
        padding-bottom: 1rem;
        border-bottom: 2px solid #3498db;
    }
    
    /* Camera container */
    .css-1l02zno {
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
    
    /* Success message */
    .stAlert .st-b7 {
        background-color: #2ecc71 !important;
        color: white !important;
        border-radius: 10px;
    }
    
    /* Warning message */
    .stAlert .st-c0 {
        background-color: #e74c3c !important;
        color: white !important;
        border-radius: 10px;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(to right, #3498db, #2c3e50);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
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

# Create a queue for passing frames between threads
frame_queue = queue.Queue(maxsize=10)
result_queue = queue.Queue()

# Global variables for tracking state
if 'last_detection' not in st.session_state:
    st.session_state.last_detection = None
if 'last_detection_time' not in st.session_state:
    st.session_state.last_detection_time = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'detected_plates' not in st.session_state:
    st.session_state.detected_plates = []

# Detection cooldown period (seconds)
DETECTION_COOLDOWN = 5

def process_frames():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            
            # Skip processing if we're still in cooldown
            current_time = time.time()
            if current_time - st.session_state.last_detection_time < DETECTION_COOLDOWN:
                continue
                
            st.session_state.processing = True
            
            # Convert frame to PIL Image
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Save temporary image
            temp_path = os.path.join(UPLOAD_FOLDER, "temp_capture.jpg")
            img.save(temp_path)
            
            # Perform OCR
            results = reader.readtext(temp_path)
            extracted_text = clean_text("".join([res[1] for res in results]))
            
            if extracted_text and (st.session_state.last_detection != extracted_text or 
                                 current_time - st.session_state.last_detection_time > DETECTION_COOLDOWN):
                st.session_state.last_detection = extracted_text
                st.session_state.last_detection_time = current_time
                
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
                
                result_queue.put(result)
                st.session_state.detected_plates.append(extracted_text)
            
            st.session_state.processing = False

# Start processing thread
processing_thread = threading.Thread(target=process_frames, daemon=True)
processing_thread.start()

# WebRTC video callback
def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    
    # Put frame in queue if not processing and queue not full
    if not st.session_state.processing and not frame_queue.full():
        frame_queue.put(img.copy())
    
    # Draw rectangle around detection area
    height, width = img.shape[:2]
    detection_area = (width // 4, height // 4, width * 3 // 4, height * 3 // 4)
    cv2.rectangle(img, (detection_area[0], detection_area[1]), 
                 (detection_area[2], detection_area[3]), (0, 255, 0), 2)
    
    # Add scanning animation effect
    scan_pos = int((time.time() % 2) * (detection_area[3] - detection_area[1]) / 2 + detection_area[1])
    cv2.line(img, (detection_area[0], scan_pos), (detection_area[2], scan_pos), (0, 255, 255), 2)
    
    return av.VideoFrame.from_ndarray(img, format="bgr24")

# WebRTC configuration
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Main app layout
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Live Camera Feed")
    st.markdown("Position the vehicle's number plate within the green rectangle for detection.")
    
    # WebRTC streamer
    ctx = webrtc_streamer(
        key="example",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

with col2:
    st.subheader("Detection Results")
    
    if not result_queue.empty():
        result = result_queue.get()
        
        if result["status"] == "success":
            st.success(f"✅ Detected Plate: `{result['plate']}`")
            st.dataframe(result["data"])
            
            # Show vehicle image if available
            if "Vehicle Image" in result["data"].columns:
                img_path = result["data"]["Vehicle Image"].iloc[0]
                if os.path.exists(img_path):
                    st.image(img_path, caption="Registered Vehicle", use_column_width=True)
        else:
            st.warning(f"❌ Detected Plate: `{result['plate']}` (Not found in database)")
    
    # Show last detected plate if no new detections
    elif st.session_state.last_detection:
        matched_info = df[df["Plate Number Cleaned"] == st.session_state.last_detection]
        
        if not matched_info.empty:
            st.success(f"✅ Last Detected Plate: `{st.session_state.last_detection}`")
            st.dataframe(matched_info)
            
            if "Vehicle Image" in matched_info.columns:
                img_path = matched_info["Vehicle Image"].iloc[0]
                if os.path.exists(img_path):
                    st.image(img_path, caption="Registered Vehicle", use_column_width=True)
        else:
            st.warning(f"❌ Last Detected Plate: `{st.session_state.last_detection}` (Not found in database)")
    
    # Show detection history
    if st.session_state.detected_plates:
        st.subheader("Detection History")
        history_cols = st.columns(3)
        
        for i, plate in enumerate(st.session_state.detected_plates[-6:]):  # Show last 6 plates
            with history_cols[i % 3]:
                st.code(plate)

# Manual upload fallback
st.markdown("---")
st.subheader("Or upload an image manually")
uploaded_file = st.file_uploader("Upload Vehicle Image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

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
            
            if "Vehicle Image" in matched_info.columns:
                img_path = matched_info["Vehicle Image"].iloc[0]
                if os.path.exists(img_path):
                    st.image(img_path, caption="Registered Vehicle", use_column_width=True)
        else:
            st.warning("❌ Vehicle not found in the database.")
