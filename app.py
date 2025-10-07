import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# ------------------ GOOGLE SHEETS SETUP ------------------
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
    for i, row in enumerate(data, start=2):  # row 1 = header
        sheet_roll = str(row["ROLL NUMBER"]).strip().lower()
        if sheet_roll == roll_number:
            sheet.update_cell(i, 3, "Present")
            return True, row["NAME"]
    return False, None

# ------------------ REAL-TIME QR DETECTOR ------------------
class QRProcessor(VideoProcessorBase):
    def __init__(self):
        self.detected = set()
        self.detector = cv2.QRCodeDetector()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = self.detector.detectAndDecode(gray)
        if data:
            roll = data.strip()
            if roll not in self.detected:
                found, name = mark_attendance(roll)
                if found:
                    st.success(f"✅ {name} ({roll}) marked Present")
                    st.balloons()
                else:
                    st.error(f"❌ Roll Number {roll} not found in list")
                self.detected.add(roll)
        return frame

# ------------------ STREAMLIT UI ------------------
st.set_page_config(page_title="Workshop Attendance", page_icon="📋")
st.title("📋 Club Workshop Attendance System (Live QR Scanner)")

st.markdown("""
### 📱 Instructions:
- Allow camera access.
- Show participant QR ID to camera.
- Attendance will be automatically marked as **Present** once QR is detected.
""")

RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})
webrtc_streamer(
    key="live-qr-scanner",
    video_processor_factory=QRProcessor,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": False},
)

# Manual entry fallback
st.subheader("⌨️ Manual Entry (Optional)")
manual_roll = st.text_input("Enter Roll Number")
if st.button("Mark Attendance"):
    if manual_roll:
        found, name = mark_attendance(manual_roll)
        if found:
            st.success(f"✅ {name} ({manual_roll}) marked Present")
            st.balloons()
        else:
            st.error(f"❌ Roll Number {manual_roll} not found")

# Show current list
st.subheader("📊 Current Attendance List")
try:
    data = sheet.get_all_records()
    st.dataframe(data)
except Exception:
    st.warning("⚠️ Could not fetch attendance list.")
