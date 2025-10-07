import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
from pyzbar.pyzbar import decode
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# ------------------ GOOGLE SHEETS ------------------
service_account_info = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
SHEET_NAME = "Workshop_Attendance"
sheet = client.open(SHEET_NAME).sheet1

def mark_attendance(roll_number):
    roll_number = str(roll_number).strip().lower()
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            sheet.update_cell(i, 3, "Present")
            return True, row["NAME"]
    return False, None

# ------------------ REAL-TIME QR PROCESSOR ------------------
class QRProcessor(VideoProcessorBase):
    def __init__(self):
        self.detected = set()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded_objects = decode(img)
        for obj in decoded_objects:
            roll = obj.data.decode("utf-8").strip()
            if roll not in self.detected:
                found, name = mark_attendance(roll)
                if found:
                    st.success(f"✅ {name} ({roll}) marked Present")
                else:
                    st.error(f"❌ Roll Number {roll} not found")
                self.detected.add(roll)
        return frame

# ------------------ STREAMLIT UI ------------------
st.title("📋 Club Workshop Attendance (Real-Time QR Scan)")

st.markdown("""
**Instructions:**  
- Allow camera access  
- Show QR code of participant ID to camera  
- Attendance will be marked automatically
""")

RTC_CONFIGURATION = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
webrtc_streamer(key="qr-scanner", video_processor_factory=QRProcessor, rtc_configuration=RTC_CONFIGURATION)
