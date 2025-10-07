import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
import numpy as np
from PIL import Image

# ------------------ GOOGLE SHEETS SETUP ------------------

# Load credentials from Streamlit secrets
service_account_info = st.secrets["gcp_service_account"]

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

SHEET_NAME = "Workshop_Attendance"
sheet = client.open(SHEET_NAME).sheet1

# ------------------ FUNCTIONS ------------------

def mark_attendance(roll_number):
    """Mark attendance in Google Sheet (case-insensitive)"""
    roll_number = str(roll_number).strip().lower()
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            sheet.update_cell(i, 3, "Present")  # 3rd column = isPresent
            return True, row["NAME"]
    return False, None

def scan_qr_from_image(img):
    """Improved QR detection for mobile photos"""
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)  # Improve contrast

    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(gray)
    if data:
        return data.strip()

    # Fallback for multiple QR codes
    result = detector.detectAndDecodeMulti(gray)
    if result is not None:
        data_list, bbox_list, _ = result
        if data_list:
            return data_list[0].strip()  # take first QR if multiple
    return None

def show_confetti():
    """Display confetti using Streamlit balloons"""
    st.balloons()

# ------------------ STREAMLIT UI ------------------

st.set_page_config(page_title="Workshop Attendance", page_icon="📋", layout="centered")
st.title("📋 Club Workshop Attendance System")

st.markdown(
    """
    **Instructions for Coordinators:**
    - 📱 Android: back camera opens automatically.
    - 🍏 iPhone: tap the flip icon to switch to back camera.
    - 🎯 Make sure the QR code on the participant ID is clearly visible.
    - 🧾 If QR doesn't scan, use manual roll entry below.
    """
)

st.divider()

# ------------------ OPTION 1: QR SCAN ------------------
st.subheader("📷 Mark Attendance via QR Code")
img_file = st.camera_input("Scan QR Code (Allow camera access)")

if img_file is not None:
    img = Image.open(img_file)
    roll = scan_qr_from_image(img)
    if roll:
        found, name = mark_attendance(roll)
        if found:
            st.success(f"✅ {name} ({roll}) marked Present")
            show_confetti()
        else:
            st.error(f"❌ Roll Number {roll} not found in the list.")
    else:
        st.warning("⚠️ No QR code detected. Please try again.")

st.divider()

# ------------------ OPTION 2: MANUAL ENTRY ------------------
st.subheader("⌨️ Mark Attendance Manually")
manual_roll = st.text_input("Enter Roll Number")

if st.button("Submit Roll Number"):
    if manual_roll.strip():
        found, name = mark_attendance(manual_roll)
        if found:
            st.success(f"✅ {name} ({manual_roll}) marked Present")
            show_confetti()
        else:
            st.error(f"❌ Roll Number {manual_roll} not found in the list.")
    else:
        st.warning("⚠️ Please enter a valid Roll Number.")

st.divider()

# ------------------ CURRENT ATTENDANCE LIST ------------------
st.subheader("📊 Current Attendance List")
try:
    data = sheet.get_all_records()
    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No data found in the sheet.")
except Exception as e:
    st.error("⚠️ Unable to fetch data from Google Sheet.")
    st.text(str(e))

st.caption("© 2025 Bhargav | Club Workshop Attendance System")
