import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pyzbar.pyzbar import decode
import cv2
import numpy as np
from PIL import Image

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "service_account.json"  # your service account key file
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)

# Open your sheet
SHEET_NAME = "Workshop_Attendance"
sheet = client.open(SHEET_NAME).sheet1


# ✅ Attendance marking with case-insensitive + space handling
def mark_attendance(roll_number):
    roll_number = str(roll_number).strip().lower()  # normalize scanned/manual roll

    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):  # start=2 (row 1 is header)
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            sheet.update_cell(i, 3, "Present")  # 3rd column = isPresent
            return True, row["NAME"]
    return False, None


# ✅ QR decoding from image
def scan_qr_from_image(img):
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    decoded_objects = decode(img)
    if decoded_objects:
        return decoded_objects[0].data.decode("utf-8")
    return None


# ------------------ Streamlit App ------------------

st.title("📋 Club Workshop Attendance System")

# --- Option 1: Capture QR from camera ---
st.subheader("📷 Mark Attendance via QR Code")

if "camera_active" not in st.session_state:
    st.session_state.camera_active = False

if st.button("📸 Take Photo"):
    st.session_state.camera_active = not st.session_state.camera_active

if st.session_state.camera_active:
    img_file = st.camera_input("Scan QR Code")
    if img_file is not None:
        img = Image.open(img_file)
        roll = scan_qr_from_image(img)
        if roll:
            found, name = mark_attendance(roll)
            if found:
                st.success(f"✅ {name} ({roll}) marked Present")
            else:
                st.error(f"❌ Roll Number {roll} not found in the list")
        else:
            st.warning("⚠️ No QR code detected in the image.")


# --- Option 2: Manual Entry ---
st.subheader("⌨️ Mark Attendance Manually")
manual_roll = st.text_input("Enter Roll Number")
if st.button("Submit Roll Number"):
    if manual_roll:
        found, name = mark_attendance(manual_roll)
        if found:
            st.success(f"✅ {name} ({manual_roll}) marked Present")
        else:
            st.error(f"❌ Roll Number {manual_roll} not found in the list")


# --- Show current attendance list ---
st.subheader("📊 Current Attendance List")
data = sheet.get_all_records()
st.dataframe(data)
