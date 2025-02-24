import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import threading
import time
import os
import numpy as np

# Direktori penyimpanan gambar
IMG_DIR = "captured_images"
os.makedirs(IMG_DIR, exist_ok=True)

# MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Variabel
captured_images = []
capture_triggered = False
countdown_active = False
countdown_text = "Lambaikan kedua tangan\nuntuk mengambil gambar"
latest_frame = None  # Simpan frame terbaru
hand_movements = []

# Load gambar yang sudah ada ke slideshow
if os.listdir(IMG_DIR):
    captured_images = [os.path.join(IMG_DIR, f) for f in os.listdir(IMG_DIR) if f.endswith(".jpg")]

# Fungsi untuk update slideshow
def update_slideshow():
    while True:
        if captured_images:
            for img_path in captured_images:
                img = Image.open(img_path)
                img = img.resize((600, 300), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                slideshow_label.config(image=img_tk)
                slideshow_label.image = img_tk
                time.sleep(3)

# Fungsi untuk mendeteksi pergerakan tangan
def detect_hand_wave(landmarks):
    global hand_movements
    if landmarks:
        wrist_y = landmarks.landmark[mp_hands.HandLandmark.WRIST].y  # Posisi y pergelangan tangan
        shoulder_y = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y  # Gunakan pangkal jari telunjuk sebagai referensi bahu

        # Cek apakah tangan berada di atas kepala (lebih tinggi dari bahu)
        if wrist_y > shoulder_y:
            return False  # Tidak di atas kepala

        hand_movements.append(wrist_y)
        if len(hand_movements) > 10:
            del hand_movements[0]
        
        # Cek jika ada gerakan naik turun yang cukup signifikan (>= 0.1)
        if len(hand_movements) >= 10 and max(hand_movements) - min(hand_movements) > 0.1:
            return True
    return False


# Fungsi untuk menampilkan aba-aba
def start_countdown():
    global countdown_active, countdown_text, latest_frame
    if not countdown_active:
        countdown_active = True
        for i in range(5, 0, -1):
            countdown_text = f"Bersiap!\nFoto dalam {i} detik..."
            time.sleep(1)
        countdown_text = "Smile! 😊"
        time.sleep(1)
        if latest_frame is not None:
            capture_image(latest_frame)
        countdown_text = "Lambaikan kedua tangan\nuntuk mengambil gambar"
        countdown_active = False

# Fungsi untuk menangkap gambar
def capture_image(frame):
    img_path = os.path.join(IMG_DIR, f"selfie_{int(time.time())}.jpg")
    cv2.imwrite(img_path, frame)
    captured_images.append(img_path)

# Fungsi untuk menangani video streaming
def video_stream():
    global capture_triggered, countdown_text, latest_frame
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue

        latest_frame = frame.copy()  # Simpan frame terbaru untuk diambil nanti

        # Konversi ke RGB untuk MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        # Deteksi tangan
        hand_count = 0
        wave_detected = False
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                hand_count += 1
                
                # Cek apakah tangan melambai (bergerak naik turun)
                if detect_hand_wave(hand_landmarks):
                    wave_detected = True

        # Jika dua tangan melambai, mulai aba-aba
        if hand_count >= 2 and wave_detected and not countdown_active:
            threading.Thread(target=start_countdown, daemon=True).start()
        
        # Menjaga rasio asli kamera
        h, w, _ = frame.shape
        new_w = 600  # Sesuaikan dengan lebar window
        new_h = int((h / w) * new_w)  # Hitung tinggi agar tidak stretch
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # === Tambahkan overlay hitam transparan (opacity 40%) ===
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (new_w, new_h), (0, 0, 0), -1)  # Kotak hitam penuh
        alpha = 0.6  # Opacity 40%
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # === Tambahkan teks dengan warna emas ===
        text_size = 1.2  # Ukuran teks
        text_thickness = 4
        text_color = (0, 215, 255)  # Warna emas dalam format BGR
        for i, line in enumerate(countdown_text.split('\n')):
            text_width, text_height = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, text_size, text_thickness)[0]
            line_x = (new_w - text_width) // 2
            line_y = (new_h // 2) + (i * text_height * 2)  # Pusatkan lebih baik
            cv2.putText(frame, line, (line_x, line_y), cv2.FONT_HERSHEY_SIMPLEX, text_size, text_color, text_thickness, cv2.LINE_AA)
        
        # Convert ke format ImageTk
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img_tk = ImageTk.PhotoImage(img)
        video_label.config(image=img_tk)
        video_label.image = img_tk
    
    cap.release()
    cv2.destroyAllWindows()


# GUI Setup
# GUI Setup
root = tk.Tk()
root.title("Fun Selfie App")
root.geometry("600x1900")  # Rasio 6:19
root.configure(bg="white")  # Mengubah latar belakang menjadi putih

# Frame untuk slideshow
slideshow_label = Label(root, bg="white")  # Tambahkan bg putih
slideshow_label.pack(fill=tk.BOTH, expand=True)

# Load dan tampilkan gambar PNG
image_path = "logo.png"  # Ganti dengan path gambar PNG
original_img = Image.open(image_path)

# Resize agar lebarnya 600px (sesuai window)
new_width = 600
aspect_ratio = original_img.height / original_img.width
new_height = int(new_width * aspect_ratio)
resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
img_tk = ImageTk.PhotoImage(resized_img)

# Label untuk gambar PNG (Ditempatkan di tengah)
image_label = Label(root, image=img_tk, bg="white")  # Tambahkan bg putih
image_label.pack(fill=tk.BOTH, expand=True)  # Menempatkan gambar di antara slideshow dan video stream

# Frame untuk video stream
video_label = Label(root, bg="white")  # Tambahkan bg putih
video_label.pack(fill=tk.BOTH, expand=True)

# Thread untuk slideshow
threading.Thread(target=update_slideshow, daemon=True).start()
# Thread untuk video stream
threading.Thread(target=video_stream, daemon=True).start()

root.mainloop()
