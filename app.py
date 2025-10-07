import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
import numpy as np
from PIL import Image
import json
import base64
from io import BytesIO
from streamlit.components.v1 import html

# ---------------- Google Sheets setup ----------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    SERVICE_ACCOUNT_FILE = "service_account.json"
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)

client = gspread.authorize(creds)

SHEET_NAME = "Workshop_Attendance"
sheet = client.open(SHEET_NAME).sheet1


# ---------------- Attendance marking ----------------
def mark_attendance(roll_number):
    roll_number = str(roll_number).strip().lower()
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            if str(row["isPresent"]).strip().lower() == "present":
                return "already", row["NAME"]
            sheet.update_cell(i, 3, "Present")
            return "marked", row["NAME"]
    return "not_found", None


# ---------------- QR decoding using OpenCV ----------------
def scan_qr_from_image(img):
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img_bgr)
    if data:
        return data
    return None


# ---------------- Streamlit App ----------------
st.title("📋 Club Workshop Attendance System")

# --- Manual Entry ---
st.subheader("⌨️ Mark Attendance Manually")
manual_roll = st.text_input("Enter Roll Number")

if st.button("Submit Roll Number"):
    if manual_roll:
        status, name = mark_attendance(manual_roll)
        if status == "marked":
            st.success(f"✅ {name} ({manual_roll}) marked Present")
        elif status == "already":
            st.warning(f"⚠️ {name} ({manual_roll}) is already marked Present")
        else:
            st.error(f"❌ Roll Number {manual_roll} not found in the list")

# --- Camera Input (Back Camera for Mobile) ---
st.subheader("📷 Mark Attendance via QR Code (Back Camera)")

camera_html = """
<video id="video" autoplay playsinline width="300" height="220" style="border-radius:10px;border:2px solid #ccc;"></video>
<canvas id="canvas" style="display:none;"></canvas>
<button id="capture" style="margin-top:10px;padding:8px 16px;border-radius:8px;background-color:#0d6efd;color:white;">📸 Capture</button>

<script>
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const capture = document.getElementById('capture');

// Try rear camera first
navigator.mediaDevices.getUserMedia({ video: { facingMode: { exact: "environment" } } })
  .then(stream => { video.srcObject = stream; })
  .catch(err => {
    console.warn("Rear camera not found, switching to default:", err);
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => { video.srcObject = stream; });
  });

capture.onclick = () => {
  const context = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataURL = canvas.toDataURL('image/png');
  window.parent.postMessage({ type: 'capture', image: dataURL }, '*');
};
</script>
"""

html(camera_html, height=350)

# Listen for captured image
capture_event = st.session_state.get("captured_image", None)

# Streamlit’s message listener to receive from iframe
st.markdown("""
<script>
window.addEventListener('message', (event) => {
  if (event.data.type === 'capture') {
    const captured = event.data.image;
    window.parent.postMessage({ isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: captured }, '*');
  }
});
</script>
""", unsafe_allow_html=True)

# Use the correct new API (no experimental)
if "captured_image" not in st.session_state:
    st.session_state["captured_image"] = None

captured_image = st.query_params.get("captured_image", None)

if captured_image:
    st.session_state["captured_image"] = captured_image

if st.session_state["captured_image"]:
    img_base64 = st.session_state["captured_image"]
    if isinstance(img_base64, str) and img_base64.startswith("data:image"):
        img_bytes = base64.b64decode(img_base64.split(",")[1])
        img = Image.open(BytesIO(img_bytes))
        roll = scan_qr_from_image(img)
        if roll:
            status, name = mark_attendance(roll)
            if status == "marked":
                st.success(f"✅ {name} ({roll}) marked Present")
            elif status == "already":
                st.warning(f"⚠️ {name} ({roll}) is already marked Present")
            else:
                st.error(f"❌ Roll Number {roll} not found in the list")
        else:
            st.warning("⚠️ No QR code detected in the image.")


# --- Attendance Summary ---
st.subheader("📊 Attendance Summary")
data = sheet.get_all_records()

total = len(data)
present = sum(1 for row in data if str(row["isPresent"]).strip().lower() == "present")
left = total - present

col1, col2, col3 = st.columns(3)
col1.metric("👥 Total Participants", total)
col2.metric("✅ Present", present)
col3.metric("⏳ Left", left)

# --- Show current attendance list ---
st.subheader("📋 Current Attendance List")
st.dataframe(data)
