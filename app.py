from flask import Flask, Response, render_template, request, jsonify, send_from_directory, stream_with_context
import os
import json
from ultralytics import YOLO
import cv2
import numpy as np
import time
import requests

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
RESULT_FOLDER = os.path.join(os.getcwd(), "results")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER

model = YOLO("model/best.pt") # load model

camera = None
camera_active = False

selected_category_global = "semua"
confidence_threshold = 0.5 # default threshold 50%

CATEGORY_MAP = {
    "Kulit Pisang": "Organik",
    "Kulit Jeruk": "Organik",
    "Nasi Sisa": "Organik",
    "Tulang Ayam": "Organik",
    "Tulang Ikan": "Organik",
    "Kulit Telur": "Organik",
    "Kulit Bawang": "Organik",
    "Kulit Kuaci": "Organik",
    "Botol Plastik": "Anorganik",
    "Kantong Plastik": "Anorganik",
    "Wadah Plastik": "Anorganik",
    "Kaleng Minuman": "Anorganik",
    "Kardus": "Anorganik",
    "Kertas": "Anorganik",
    "Tisu": "Anorganik",
    "Styrofoam": "Anorganik",
    "Baterai": "B3",
    "Bohlam Lampu": "B3",
    "Kaleng Cairan Anti Nyamuk": "B3",
    "Botol Hand Sanitizer": "B3"
}

CLASS_COLORS = {
    # Format BGR, bukan RGB
    # warna dasar hijau
    "Kulit Pisang": (149, 234, 149),     
    "Kulit Jeruk": (91, 163, 91),      
    "Nasi Sisa": (152, 244, 152),        
    "Tulang Ayam": (121, 186, 121),      
    "Tulang Ikan": (78, 216, 78),      
    "Kulit Telur": (63, 246, 63),       
    "Kulit Bawang": (51, 188, 51),      
    "Kulit Kuaci": (32, 147, 32),       

    #  warna dasar biru
    "Botol Plastik": (234, 227, 149),    
    "Kantong Plastik": (196, 196, 110),   
    "Wadah Plastik": (229, 244, 152),     
    "Kaleng Minuman": (208, 202, 136),    
    "Kardus": (216, 216, 78),           
    "Kertas": (246, 228, 63),           
    "Tisu": (211, 196, 58),             
    "Styrofoam": (180, 126, 39),        

    # warna dasar merah
    "Baterai": (78, 78, 216),          
    "Bohlam Lampu": (63, 63, 246),     
    "Kaleng Cairan Anti Nyamuk": (58, 58, 211),  
    "Botol Hand Sanitizer": (39, 39, 180)        
}

RECOMMENDATION_MAP = {
    "Kulit Pisang": "Masukkan ke tempat sampah organik atau buat kompos.",
    "Kulit Jeruk": "Masukkan ke tempat sampah organik atau kompos.",
    "Nasi Sisa": "Masukkan ke tempat sampah organik atau buat kompos.",
    "Tulang Ayam": "Sebaiknya dibuang ke termpat sampah organik.",
    "Tulang Ikan": "Masukkan ke tempat sampah organik.",
    "Kulit Telur": "Masukkan ke tempat sampah organik.",
    "Kulit Bawang": "Masukkan ke termpat sampah organik atau buat kompos.",
    "Kulit Kuaci": "Masukkan ke tempat sampah organik.",

    "Botol Plastik": "Bersihkan lalu bawa ke bank sampah.",
    "Kantong Plastik": "Gunakan ulang atau bawa ke bank sampah.",
    "Wadah Plastik": "Bersihkan lalu bawa ke bank sampah.",
    "Kaleng Minuman": "Masukkan ke tempat sampah anorganik atau daur ulang.",
    "Kardus": "Masukkan ke tempat sampah anorganik atau jual ke pengepul.",
    "Kertas": "Daur ulang atau jual ke pengepul.",
    "Tisu": "Masukkan ke tempat sampah anorganik (tidak bisa didaur ulang).",
    "Styrofoam": "Masukkan ke sampah anorganik, sulit didaur ulang.",

    "Baterai": "Jangan dibuang sembarangan, kumpulkan ke tempat sampah B3.",
    "Bohlam Lampu": "Jangan dibuang ke tempat biasa, bawa ke tempat sampah B3.",
    "Kaleng Cairan Anti Nyamuk": "Buang ke tempat sampah B3.",
    "Botol Hand Sanitizer": "Buang ke tempat sampah B3."
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/lokasi")
def lokasi():
    return render_template("lokasi.html")

def draw_annotations(frame, results, selected_category="semua"):
    global confidence_threshold
    annoted_frame = frame.copy()
    recommendations = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            kategori = CATEGORY_MAP.get(label, "Lainnya")
            conf = float(box.conf[0])

            # ===== Filter Kategori =====
            if selected_category.lower() != "semua" and kategori.lower() != selected_category.lower():
                continue # skip kalau kategori tidak sesuai

            # ===== Filter Confidence Score =====
            if conf < confidence_threshold:
                continue    # skip kalau confidence score-nya lebih kecil
                            # hanya tampilkan conf >= confidence_score

            conf_percent = conf * 100

            text = f"{kategori} - {label} ({conf_percent:.1f}%)"
            color = CLASS_COLORS.get(label, (255, 255, 255)) # default putih

            # koordinat
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

            # bounding box
            cv2.rectangle(annoted_frame, (x1, y1), (x2, y2), color, 2)

            # background teks
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annoted_frame, (x1, y1 - th - 4), (x1 + tw, y1), color, -1)

            # teks
            cv2.putText(annoted_frame, text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if label in RECOMMENDATION_MAP and RECOMMENDATION_MAP[label] not in recommendations:
                recommendations.append(RECOMMENDATION_MAP[label])

    return annoted_frame, recommendations

# Filter
@app.route("/set_category", methods=["POST"])
def set_category():
    global selected_category_global
    data = request.get_json()
    selected_category_global = data.get("kategori", "semua")
    return jsonify({"message": f"Kategori: {selected_category_global}"})

@app.route("/set_confidence", methods=["POST"])
def set_confidence():
    global confidence_threshold
    data = request.get_json()
    confidence_threshold = float(data.get("confidence", 0.5))
    return jsonify({"message": f"Confidence threshold: {confidence_threshold}"})

def run_detection(image_path, filename, selected_category="semua"):
    results = model(image_path, conf=0.5)
    img = cv2.imread(image_path)
    annoted_frame, recommendations = draw_annotations(img, results, selected_category)

    result_path = os.path.join(app.config["RESULT_FOLDER"], filename)
    cv2.imwrite(result_path, annoted_frame)
    return f"/results/{filename}", recommendations

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang diunggah"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400
    
    kategori = request.args.get("kategori", "semua") # ambil dari parameter link
    
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # run deteksi dengan YOLO
    result_url, recommendations = run_detection(file_path, file.filename, kategori)

    return jsonify({
        "message": "File berhasil diunggah",
        "filename": file.filename,
        "url": result_url,
        "recommendations": recommendations
    })

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/results/<filename>")
def result_file(filename):
    return send_from_directory(app.config["RESULT_FOLDER"], filename)

def gen_frames():
    global camera, camera_active, selected_category_global
    while True:
        if not camera_active or camera is None:
            break # loop generate frame berhenti saat kamera dimatikan

        success, frame = camera.read()
        if not success or frame is None:
            break

        # run deteksi
        results = model(frame, conf=0.5)

        annoted_frame, _ = draw_annotations(frame, results, selected_category_global)

        ret, buffer = cv2.imencode('.jpg', annoted_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
@app.route("/recommendations_feed")
def recommendation_feed():
    def generate():
        global camera, camera_active, selected_category_global
        while True:
            if not camera_active or camera is None:
                time.sleep(0.5)
                continue
            
            success, frame = camera.read()
            if not success or frame is None:
                break
            
            results = model(frame, conf=0.5)
            _, recommendations = draw_annotations(frame, results, selected_category_global)

            if recommendations:
                yield f"data: {json.dumps(recommendations)}\n\n"
            else:
                yield "data: []\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/video_feed")
def video_feed():
    global camera, camera_active
    if not camera_active:
        camera = cv2.VideoCapture(0) # kamera real-time
        camera_active = True

    return Response(gen_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stop_feed")
def stop_feed():
    global camera, camera_active
    camera_active = False
    if camera is not None:
        camera.release()
        camera = None
    
    return jsonify({"status": "stopped"})

# ========== Lokasi Bank Sampah ==========
GOOGLE_API_KEY = "AIzaSyCtUUGV-q1wIaYzj0qAozT_kpHmj4cQq9E"

@app.route('/get_banksampah')
def get_banksampah():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    
    # Query Google Places API
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "keyword": "bank sampah",
        "key": GOOGLE_API_KEY
    }
    
    response = requests.get(url, params=params).json()
    
    # Ambil hanya data penting (nama + koordinat)
    locations = []
    if "results" in response:
        for r in response["results"]:
            locations.append({
                "name": r.get("name"),
                "lat": r["geometry"]["location"]["lat"],
                "lng": r["geometry"]["location"]["lng"]
            })
    
    return jsonify(locations)

if __name__ == "__main__":
    app.run(debug=True)