import cv2
import numpy as np
import requests
import time
import os
from deepface import DeepFace

# Configuration
NODE_API_URL = "http://localhost:5000/api/v1/alerts" # Node.js ka Alert URL
CAMERA_SOURCE = 0 # 0 for Webcam, ya "rtsp://..." IP Camera ke liye
EMPLOYEE_FOLDER = "employees"

# OpenCV Face Detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Aag (Fire) detect karne ka function (Using HSV Color Space)
def detect_fire(frame):
    blur = cv2.GaussianBlur(frame, (21, 21), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    
    # Fire ke colors (Red, Orange, Yellow) ka range
    lower = np.array([18, 50, 50], dtype="uint8")
    upper = np.array([35, 255, 255], dtype="uint8")
    
    mask = cv2.inRange(hsv, lower, upper)
    fire_pixels = cv2.countNonZero(mask)
    
    # Agar screen par bahut saare fire pixels hain, matlab aag lagi hai
    return fire_pixels > 15000

print("🎥 Starting 24/7 Live CCTV Monitoring (Fire & Face Detection)...")
cap = cv2.VideoCapture(CAMERA_SOURCE)

last_alert_time = 0
COOLDOWN_SECONDS = 15 # Ek alert bhejne ke baad 15 second rukega taaki spam na ho

while True:
    ret, frame = cap.read()
    if not ret: break

    # 1. Check for Fire
    is_fire = detect_fire(frame)

    if is_fire:
        current_time = time.time()
        
        # Cooldown check (Spam rokne ke liye)
        if current_time - last_alert_time > COOLDOWN_SECONDS:
            print("🔥 FIRE DETECTED! Scanning for people in danger...")
            
            # 2. Detect Faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            
            identified_people = []
            
            # 3. Identify People (Pichle 1 ghante ya current present log)
            for (x, y, w, h) in faces:
                pad_x, pad_y = int(w * 0.2), int(h * 0.3)
                y1, y2 = max(0, y - pad_y), min(frame.shape[0], y + h + pad_y)
                x1, x2 = max(0, x - pad_x), min(frame.shape[1], x + w + pad_x)
                
                face_roi = frame[y1:y2, x1:x2]
                if face_roi.size == 0: continue
                
                try:
                    # Database se match karo
                    dfs = DeepFace.find(img_path=face_roi, db_path=EMPLOYEE_FOLDER, enforce_detection=False, silent=True)
                    if len(dfs) > 0 and not dfs[0].empty:
                        name = os.path.splitext(os.path.basename(dfs[0].iloc[0]['identity']))[0].capitalize()
                        if name not in identified_people:
                            identified_people.append(name)
                except:
                    pass

            # Unknown log jo match nahi hue
            unknown_count = len(faces) - len(identified_people)
            if unknown_count > 0:
                for i in range(unknown_count):
                    identified_people.append(f"Unknown Person {i+1}")

            # 4. Send Real-Time Alert to Node.js Dashboard
            alert_payload = {
                "type": "FIRE_DETECTED",
                "source": "Main Assembly Line CCTV",
                "description": f"Critical fire hazard detected! {len(faces)} people are trapped in the area.",
                "facesDetected": len(faces),
                "identifiedPersons": identified_people
            }
            
            try:
                requests.post(NODE_API_URL, json=alert_payload)
                print(f"🚨 Alert Sent to Dashboard: {alert_payload}")
            except Exception as e:
                print(f"❌ Failed to send alert: {e}")
                
            last_alert_time = current_time

    # Demo ke liye video window dikhana (Optional)
    cv2.imshow("IEG Smart CCTV (Press 'q' to quit)", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()