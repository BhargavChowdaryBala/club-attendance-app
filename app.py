import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
import numpy as np
from PIL import Image

# ------------------ GOOGLE SHEETS SETUP ------------------

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "service_account.json"  # Ensure this file is in your repo
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)

SHEET_NAME = "Workshop_Attendance"
sheet = client.open(SHEET_NAME).sheet1


# ------------------ FUNCTIONS ------------------

# ✅ Mark attendance (case-insensitive + trims spaces)
def mark_attendance(roll_number):
    roll_number = str(roll_number).strip().lower()

    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):  # Row 1 = header
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            sheet.update_cell(i, 3, "Present")  # 3rd column is isPresent
            return True, row["NAME"]
    return False, None


# ✅ Decode QR using OpenCV (no pyzbar needed)
def scan_qr_from_image(img):
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(img)
    if data:
        return data
    return None


# ------------------ STREAMLIT UI ------------------

st.set_page_config(page_title="Workshop Attendance", page_icon="📋", layout="centered")

st.title("📋 Club Workshop Attendance System")

st.markdown(
    """
    **Instructions for Coordinators:**
    - 📱 On **Android**, the **back camera** opens automatically.
    - 🍏 On **iPhone**, tap the **flip icon** to switch to the back camera.
    - 🎯 Make sure the **QR code on the participant ID** is clearly visible.
    - 🧾 If the QR doesn't scan, you can **enter the Roll Number manually** below.
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
        else:
            st.error(f"❌ Roll Number {roll} not found in the list.")
    else:
        st.warning("⚠️ No QR code detected in the image. Please try again.")

st.divider()

# ------------------ OPTION 2: MANUAL ENTRY ------------------
st.subheader("⌨️ Mark Attendance Manually")

manual_roll = st.text_input("Enter Roll Number")

if st.button("Submit Roll Number"):
    if manual_roll.strip():
        found, name = mark_attendance(manual_roll)
        if found:
            st.success(f"✅ {name} ({manual_roll}) marked Present")
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
