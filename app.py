import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pyzbar.pyzbar import decode
import cv2
import numpy as np
from PIL import Image
import json

# ---------------- Google Sheets setup ----------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# If running locally, keep your JSON file
# SERVICE_ACCOUNT_FILE = "service_account.json"
# creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)

# If deploying on Streamlit Cloud, load from secrets
if "gcp_service_account" in st.secrets:
    creds_dict = json.loads(st.secrets["gcp_service_account"])
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
    for i, row in enumerate(data, start=2):  # start=2 (row 1 is header)
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            if str(row["isPresent"]).strip().lower() == "present":
                return "already", row["NAME"]
            sheet.update_cell(i, 3, "Present")  # 3rd column = isPresent
            return "marked", row["NAME"]
    return "not_found", None

# ---------------- QR decoding ----------------
def scan_qr_from_image(img):
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    decoded_objects = decode(img)
    if decoded_objects:
        return decoded_objects[0].data.decode("utf-8")
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

# --- Camera Input (mobile-friendly) ---
st.subheader("📷 Mark Attendance via QR Code")

img_file = st.camera_input("Scan your QR Code")
if img_file is not None:
    img = Image.open(img_file)
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
