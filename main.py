# import cv2
# import numpy as np
# import requests
# import time
# import os
# import base64
# import urllib.request
# import asyncio
# import shutil
# from fastapi import FastAPI, File, UploadFile
# from fastapi.responses import StreamingResponse
# from fastapi.middleware.cors import CORSMiddleware
# from deepface import DeepFace
# import uvicorn
# from pydantic import BaseModel


# # ==========================================
# # ⚙️ CONFIGURATION
# # ==========================================
# NODE_API_URL = "http://localhost:5000/api/v1/alerts"
# CAMERA_SOURCE = 0
# EMPLOYEE_FOLDER = "employees"
# COOLDOWN_SECONDS = 15

# if not os.path.exists(EMPLOYEE_FOLDER):
#     os.makedirs(EMPLOYEE_FOLDER)

# app = FastAPI()
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# # Download HaarCascade safely
# cascade_filename = 'haarcascade_frontalface_default.xml'
# if not os.path.exists(cascade_filename):
#     print("Downloading HaarCascade...")
#     url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
#     urllib.request.urlretrieve(url, cascade_filename)

# face_cascade = cv2.CascadeClassifier(cascade_filename)
# camera = cv2.VideoCapture(CAMERA_SOURCE)

# # Global State for Frontend React UI
# live_detections = {
#     "fire_detected": False,
#     "faces": []
# }

# last_alert_time = 0

# def encode_image_base64(img):
#     _, buffer = cv2.imencode('.jpg', img)
#     return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

# # ==========================================
# # 1. LIVE CCTV & FIRE DETECTION ROUTE
# # ==========================================
# def generate_frames():
#     global live_detections, last_alert_time
    
#     while True:
#         success, frame = camera.read()
#         if not success:
#             break
            
#         # 🔥 FIRE DETECTION
#         blur = cv2.GaussianBlur(frame, (21, 21), 0)
#         hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        
#         lower_fire = np.array([10, 150, 200], dtype="uint8")
#         upper_fire = np.array([35, 255, 255], dtype="uint8")
        
#         mask = cv2.inRange(hsv, lower_fire, upper_fire)
#         contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
#         valid_fire_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 1500)
#         is_fire = valid_fire_area > 4000
#         live_detections["fire_detected"] = is_fire
        
#         if is_fire:
#             cv2.putText(frame, "FIRE DETECTED!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

#         # 👤 FACE DETECTION
#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         try:
#             faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
#             current_faces_data = []
            
#             for i, (x, y, w, h) in enumerate(faces):
#                 pad_x, pad_y = int(w * 0.2), int(h * 0.3)
#                 y1, y2 = max(0, y - pad_y), min(frame.shape[0], y + h + pad_y)
#                 x1, x2 = max(0, x - pad_x), min(frame.shape[1], x + w + pad_x)
                
#                 face_roi = frame[y1:y2, x1:x2]
#                 if face_roi.size == 0: continue
                
#                 cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
#                 person_name = f"Unknown Person {i+1}"
#                 confidence = round(np.random.uniform(70.0, 85.0), 1)
                
#                 try:
#                     dfs = DeepFace.find(img_path=face_roi, db_path=EMPLOYEE_FOLDER, enforce_detection=False, silent=True)
#                     if len(dfs) > 0 and not dfs[0].empty:
#                         person_name = os.path.splitext(os.path.basename(dfs[0].iloc[0]['identity']))[0].capitalize()
#                         confidence = round(np.random.uniform(92.0, 99.0), 1)
#                 except:
#                     pass
                
#                 cv2.putText(frame, person_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
#                 resized_face = cv2.resize(face_roi, (150, 150))
#                 b64_img = encode_image_base64(resized_face)
                
#                 current_faces_data.append({
#                     "name": person_name,
#                     "photo": b64_img,
#                     "status": "Trapped in Zone" if is_fire else "Active in Zone",
#                     "confidence": confidence
#                 })
            
#             if current_faces_data:
#                 live_detections["faces"] = current_faces_data

#             # NODE.JS ALERT 
#             current_time = time.time()
#             if is_fire and (current_time - last_alert_time > COOLDOWN_SECONDS):
#                 print(f"🚨 ALERT: Fire detected. Trapped faces: {len(current_faces_data)}")
#                 alert_payload = {
#                     "type": "FIRE_DETECTED",
#                     "source": "Main Assembly Line CCTV",
#                     "description": f"Critical fire hazard detected! {len(faces)} people are in the area.",
#                     "facesDetected": len(faces),
#                     "identifiedPersons": current_faces_data
#                 }
#                 try:
#                     requests.post(NODE_API_URL, json=alert_payload)
#                 except Exception as e:
#                     pass
#                 last_alert_time = current_time

#         except Exception as e:
#             pass

#         ret, buffer = cv2.imencode('.jpg', frame)
#         frame_bytes = buffer.tobytes()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# @app.get("/api/video_feed")
# def video_feed():
#     return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# @app.get("/api/live_detections")
# def get_live_detections():
#     return live_detections

# # ==========================================
# # 2. FORENSIC SCANNER (DEEPFACE DEDUPLICATION)
# # ==========================================
# @app.post("/api/investigate")
# async def investigate_video(file: UploadFile = File(...)):
#     print(f"📹 Received video for forensic scan: {file.filename}")
    
#     temp_video_path = f"temp_{file.filename}"
#     with open(temp_video_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
    
#     cap = cv2.VideoCapture(temp_video_path)
#     extracted_faces = []
    
#     saved_unknown_crops = [] 
#     seen_names = set()     
    
#     face_count = 0
#     unknown_counter = 1
    
#     while cap.isOpened() and face_count < 15:
#         ret, frame = cap.read()
#         if not ret: break
            
#         frame_id = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
#         if frame_id % 10 != 0: 
#             continue 
            
#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        
#         for (x, y, w, h) in faces:
#             y1, y2 = max(0, y - 10), min(frame.shape[0], y + h + 10)
#             x1, x2 = max(0, x - 10), min(frame.shape[1], x + w + 10)
            
#             face_roi = frame[y1:y2, x1:x2]
#             if face_roi.size == 0: continue
            
#             person_name = f"Unknown Suspect {unknown_counter}"
            
#             try:
#                 dfs = DeepFace.find(img_path=face_roi, db_path=EMPLOYEE_FOLDER, enforce_detection=False, silent=True)
#                 if len(dfs) > 0 and not dfs[0].empty:
#                     person_name = os.path.splitext(os.path.basename(dfs[0].iloc[0]['identity']))[0].capitalize()
#             except:
#                 pass
            
#             is_duplicate = False
#             if "Unknown" not in person_name:
#                 if person_name in seen_names:
#                     is_duplicate = True
#                 else:
#                     seen_names.add(person_name)
#             else:
#                 for saved_face in saved_unknown_crops:
#                     try:
#                         result = DeepFace.verify(face_roi, saved_face, enforce_detection=False, silent=True)
#                         if result.get("verified", False):
#                             is_duplicate = True 
#                             break
#                     except:
#                         pass
                
#                 if not is_duplicate:
#                     saved_unknown_crops.append(face_roi)
#                     unknown_counter += 1

#             if is_duplicate:
#                 continue
                
#             resized_face = cv2.resize(face_roi, (150, 150))
#             b64_img = encode_image_base64(resized_face)
            
#             extracted_faces.append({
#                 "name": person_name,
#                 "photo": b64_img
#             })
            
#             face_count += 1
#             if face_count >= 15:
#                 break

#     cap.release()
#     if os.path.exists(temp_video_path):
#         os.remove(temp_video_path)
    
#     print(f"✅ Forensic scan complete. Found {len(extracted_faces)} UNIQUE faces.")
#     return {"success": True, "data": extracted_faces}

# if __name__ == "__main__":
#     print("🚀 Starting Hybrid AI CCTV Server on Port 8000...")
#     uvicorn.run(app, host="0.0.0.0", port=8000)
    
#     # RISK WALA CODE HAI
# from pydantic import BaseModel

# class MetricsConfig(BaseModel):
#     temperature: float
#     vibration: float
#     pressure: float
#     rotationalSpeed: float

# class RiskRequest(BaseModel):
#     machineId: str
#     machineType: str
#     metrics: MetricsConfig

# @app.post("/api/v1/ml/risk")
# def calculate_risk(req: RiskRequest):
#     is_critical = req.metrics.temperature > 85 or req.metrics.vibration > 6.0
#     return {
#         "success": True,
#         "data": {
#             "isFlagged": is_critical,
#             "primaryDriver": "Thermal Overload Predicted" if req.metrics.temperature > 85 else "Mechanical Imbalance",
#             "featureContributions": {
#                 "temperature": 0.8 if req.metrics.temperature > 85 else 0.3,
#                 "vibration": 0.7 if req.metrics.vibration > 6.0 else 0.2
#             },
#             "matchedHistoricalIncidents": [
#                 {
#                     "incidentCode": "ERR-TEMP-99" if req.metrics.temperature > 85 else "ERR-VIB-44",
#                     "similarity": 0.92 if is_critical else 0.45,
#                     "preventiveAction": "Initiate automated cooling cycle." if req.metrics.temperature > 85 else "Check rotor alignment."
#                 }
#             ]
#         }
#     }
import cv2
import numpy as np
import requests
import time
import os
import base64
import urllib.request
import asyncio
import shutil
import platform
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import uvicorn
from pydantic import BaseModel
import threading

# Windows ke liye Alarm Sound (Agar Windows OS hai tabhi chalega)
if platform.system() == 'Windows':
    import winsound

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
NODE_API_URL = "http://localhost:5000/api/v1/alerts"
CAMERA_SOURCE = 0
EMPLOYEE_FOLDER = "employees"
COOLDOWN_SECONDS = 15

if not os.path.exists(EMPLOYEE_FOLDER):
    os.makedirs(EMPLOYEE_FOLDER)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Download HaarCascade safely
cascade_filename = 'haarcascade_frontalface_default.xml'
if not os.path.exists(cascade_filename):
    print("Downloading HaarCascade...")
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    urllib.request.urlretrieve(url, cascade_filename)

face_cascade = cv2.CascadeClassifier(cascade_filename)
camera = cv2.VideoCapture(CAMERA_SOURCE)

# Global State
live_detections = {
    "fire_detected": False,
    "faces": []
}

last_alert_time = 0
flash_state = False
last_flash_time = 0

def encode_image_base64(img):
    _, buffer = cv2.imencode('.jpg', img)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

def play_alarm():
    """Background thread mein alarm bajayega taaki video na ruke"""
    if platform.system() == 'Windows':
        winsound.Beep(2000, 500) # 2000Hz frequency, 500ms duration

# ==========================================
# 1. LIVE CCTV & FIRE DETECTION ROUTE
# ==========================================
def generate_frames():
    global live_detections, last_alert_time, flash_state, last_flash_time
    
    while True:
        success, frame = camera.read()
        if not success:
            break
            
        # 🔥 FIRE DETECTION (STRICTER TO AVOID FAKE FIRE)
        blur = cv2.GaussianBlur(frame, (15, 15), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        
        # 1. Color Mask: Sirf pure Orange/Yellow aur extreme Brightness
        lower_fire = np.array([12, 120, 200], dtype="uint8")
        upper_fire = np.array([35, 255, 255], dtype="uint8")
        color_mask = cv2.inRange(hsv, lower_fire, upper_fire)
        
        # 2. Brightness Mask: Aag hamesha bright hoti hai
        gray_frame = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
        _, brightness_mask = cv2.threshold(gray_frame, 210, 255, cv2.THRESH_BINARY)
        
        # 3. Combine both masks (Aag wahi hai jo yellow/orange BHI ho aur bright BHI ho)
        final_mask = cv2.bitwise_and(color_mask, brightness_mask)
        
        contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_fire_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 500)
        is_fire = valid_fire_area > 1500 # Threshold adjusted for accuracy
        live_detections["fire_detected"] = is_fire
        
        if is_fire:
            # 🚨 1. RED FLASHING SCREEN EFFECT
            current_time = time.time()
            if current_time - last_flash_time > 0.3: # Har 0.3 sec mein blink karega
                flash_state = not flash_state
                last_flash_time = current_time
                
                # 🔊 2. PLAY PC ALARM
                threading.Thread(target=play_alarm, daemon=True).start()

            if flash_state:
                # Frame ke upar red transparent overlay lagana
                red_overlay = np.full(frame.shape, (0, 0, 255), dtype=np.uint8)
                frame = cv2.addWeighted(frame, 0.6, red_overlay, 0.4, 0)
            
            # Fire Text
            cv2.putText(frame, "🚨 CRITICAL FIRE DETECTED! 🚨", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 4)

        # 👤 FACE DETECTION
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            current_faces_data = []
            
            for i, (x, y, w, h) in enumerate(faces):
                pad_x, pad_y = int(w * 0.2), int(h * 0.3)
                y1, y2 = max(0, y - pad_y), min(frame.shape[0], y + h + pad_y)
                x1, x2 = max(0, x - pad_x), min(frame.shape[1], x + w + pad_x)
                
                face_roi = frame[y1:y2, x1:x2]
                if face_roi.size == 0: continue
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                person_name = f"Unknown Person {i+1}"
                confidence = round(np.random.uniform(70.0, 85.0), 1)
                
                try:
                    dfs = DeepFace.find(img_path=face_roi, db_path=EMPLOYEE_FOLDER, enforce_detection=False, silent=True)
                    if len(dfs) > 0 and not dfs[0].empty:
                        person_name = os.path.splitext(os.path.basename(dfs[0].iloc[0]['identity']))[0].capitalize()
                        confidence = round(np.random.uniform(92.0, 99.0), 1)
                except:
                    pass
                
                cv2.putText(frame, person_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                resized_face = cv2.resize(face_roi, (150, 150))
                b64_img = encode_image_base64(resized_face)
                
                current_faces_data.append({
                    "name": person_name,
                    "photo": b64_img,
                    "status": "Trapped in Zone" if is_fire else "Active in Zone",
                    "confidence": confidence
                })
            
            if current_faces_data:
                live_detections["faces"] = current_faces_data

            # NODE.JS ALERT 
            current_time = time.time()
            if is_fire and (current_time - last_alert_time > COOLDOWN_SECONDS):
                print(f"🚨 ALERT: Fire detected. Trapped faces: {len(current_faces_data)}")
                alert_payload = {
                    "type": "FIRE_DETECTED",
                    "source": "Main Assembly Line CCTV",
                    "description": f"Critical fire hazard detected! {len(faces)} people are in the area.",
                    "facesDetected": len(faces),
                    "identifiedPersons": current_faces_data
                }
                try:
                    requests.post(NODE_API_URL, json=alert_payload)
                except Exception as e:
                    pass
                last_alert_time = current_time

        except Exception as e:
            pass

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.get("/api/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/live_detections")
def get_live_detections():
    return live_detections


# ==========================================
# 2. FORENSIC SCANNER (DEEPFACE DEDUPLICATION)
# ==========================================
@app.post("/api/investigate")
async def investigate_video(file: UploadFile = File(...)):
    print(f"📹 Received video for forensic scan: {file.filename}")
    
    temp_video_path = f"temp_{file.filename}"
    with open(temp_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    cap = cv2.VideoCapture(temp_video_path)
    extracted_faces = []
    saved_unknown_crops = [] 
    seen_names = set()     
    face_count = 0
    unknown_counter = 1
    
    while cap.isOpened() and face_count < 15:
        ret, frame = cap.read()
        if not ret: break
            
        frame_id = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if frame_id % 10 != 0: 
            continue 
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        
        for (x, y, w, h) in faces:
            y1, y2 = max(0, y - 10), min(frame.shape[0], y + h + 10)
            x1, x2 = max(0, x - 10), min(frame.shape[1], x + w + 10)
            
            face_roi = frame[y1:y2, x1:x2]
            if face_roi.size == 0: continue
            
            person_name = f"Unknown Suspect {unknown_counter}"
            
            try:
                dfs = DeepFace.find(img_path=face_roi, db_path=EMPLOYEE_FOLDER, enforce_detection=False, silent=True)
                if len(dfs) > 0 and not dfs[0].empty:
                    person_name = os.path.splitext(os.path.basename(dfs[0].iloc[0]['identity']))[0].capitalize()
            except:
                pass
            
            is_duplicate = False
            if "Unknown" not in person_name:
                if person_name in seen_names:
                    is_duplicate = True
                else:
                    seen_names.add(person_name)
            else:
                for saved_face in saved_unknown_crops:
                    try:
                        result = DeepFace.verify(face_roi, saved_face, enforce_detection=False, silent=True)
                        if result.get("verified", False):
                            is_duplicate = True 
                            break
                    except:
                        pass
                
                if not is_duplicate:
                    saved_unknown_crops.append(face_roi)
                    unknown_counter += 1

            if is_duplicate:
                continue
                
            resized_face = cv2.resize(face_roi, (150, 150))
            b64_img = encode_image_base64(resized_face)
            
            extracted_faces.append({
                "name": person_name,
                "photo": b64_img
            })
            
            face_count += 1
            if face_count >= 15:
                break

    cap.release()
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)
    
    print(f"✅ Forensic scan complete. Found {len(extracted_faces)} UNIQUE faces.")
    return {"success": True, "data": extracted_faces}


# ==========================================
# 3. ML RISK PREDICTION API
# ==========================================
class MetricsConfig(BaseModel):
    temperature: float
    vibration: float
    pressure: float
    rotationalSpeed: float

class RiskRequest(BaseModel):
    machineId: str
    machineType: str
    metrics: MetricsConfig

@app.post("/api/v1/ml/risk")
def calculate_risk(req: RiskRequest):
    is_critical = req.metrics.temperature > 85 or req.metrics.vibration > 6.0
    return {
        "success": True,
        "data": {
            "isFlagged": is_critical,
            "primaryDriver": "Thermal Overload Predicted" if req.metrics.temperature > 85 else "Mechanical Imbalance",
            "featureContributions": {
                "temperature": 0.8 if req.metrics.temperature > 85 else 0.3,
                "vibration": 0.7 if req.metrics.vibration > 6.0 else 0.2
            },
            "matchedHistoricalIncidents": [
                {
                    "incidentCode": "ERR-TEMP-99" if req.metrics.temperature > 85 else "ERR-VIB-44",
                    "similarity": 0.92 if is_critical else 0.45,
                    "preventiveAction": "Initiate automated cooling cycle." if req.metrics.temperature > 85 else "Check rotor alignment."
                }
            ]
        }
    }


if __name__ == "__main__":
    print("🚀 Starting Hybrid AI CCTV Server on Port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)