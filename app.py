import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import threading
import time
import os
import numpy as np
from collections import deque


# Direktori penyimpanan gambar
IMG_DIR = "captured_images"
os.makedirs(IMG_DIR, exist_ok=True)

# MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose  # Tambahkan pose
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Variabel
captured_images = []
capture_triggered = False
countdown_active = False
countdown_text = "Lambaikan kedua tangan\nuntuk mengambil gambar"
latest_frame = None  # Simpan frame terbaru
hand_movements = []
wave_count = 0  # Hitungan jumlah lambaian



video_width = 960   # Placeholder, nanti diperbarui dari kamera
video_height = 540  # Placeholder, nanti diperbarui dari kamera


# Load gambar yang sudah ada ke slideshow
if os.listdir(IMG_DIR):
    captured_images = [os.path.join(IMG_DIR, f) for f in os.listdir(IMG_DIR) if f.endswith(".jpg")]

# Fungsi untuk update slideshow
def update_slideshow():
    while True:
        if captured_images:
            for img_path in captured_images:
                img = Image.open(img_path)
                
                # Resize berdasarkan ukuran video
                img = img.resize((video_width, video_height), Image.Resampling.LANCZOS)
                
                img_tk = ImageTk.PhotoImage(img)
                slideshow_label.config(image=img_tk)
                slideshow_label.image = img_tk
                time.sleep(3)

def detect_hand_wave(hand_landmarks, pose_landmarks=None):

    global hand_movements, wave_count

    if hand_landmarks and pose_landmarks:
        wrist_y = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y
        nose_y = pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE].y  # Gunakan NOSE dari pose

        # Cek apakah tangan di atas kepala
        if wrist_y >= nose_y:  
            return False  # Abaikan kalau tangan di bawah kepala

        # Simpan pergerakan tangan
        hand_movements.append(wrist_y)
        if len(hand_movements) > 10:  
            del hand_movements[0]

        # Cek perubahan arah untuk mendeteksi lambaian
        if len(hand_movements) >= 2:
            if (hand_movements[-1] > hand_movements[-2]) and (len(hand_movements) > 2 and hand_movements[-2] < hand_movements[-3]):
                wave_count += 1  

        # Jika sudah melambai 3 kali, reset dan return True
        if wave_count >= 3:
            wave_count = 0
            hand_movements.clear()
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
    # Load logo
    logo_path = "logo.png"  # Pastikan path benar
    logo = Image.open(logo_path)

    # Resize logo (misal: 20% dari lebar gambar)
    frame_h, frame_w, _ = frame.shape
    logo_width = int(frame_w * 0.2)
    aspect_ratio = logo.height / logo.width
    logo_height = int(logo_width * aspect_ratio)
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

    # Konversi frame ke format PIL
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Posisi logo di bawah tengah
    x_offset = (frame_w - logo_width) // 2
    y_offset = frame_h - logo_height - 20  # Beri jarak 20px dari bawah

    # Tempel logo ke frame
    frame_pil.paste(logo, (x_offset, y_offset), logo)

    # Simpan gambar dengan watermark
    img_path = os.path.join(IMG_DIR, f"selfie_{int(time.time())}.jpg")
    frame_pil.save(img_path)

    # Tambahkan ke daftar slideshow
    captured_images.append(img_path)


# Fungsi untuk menangani video streaming
def video_stream():
    global capture_triggered, countdown_text, latest_frame
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cv2.setUseOptimized(True)

    # Dapatkan resolusi asli kamera
    global video_width, video_height
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Sesuaikan lebar dengan window (misal 50% dari 1920)
    target_width = 960
    target_height = int((video_height / video_width) * target_width)  # Jaga rasio

    video_width, video_height = target_width, target_height  # Update ukuran

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
root = tk.Tk()
root.title("Fun Selfie App")
root.geometry("1920x1080")  # Ukuran Full HD
root.configure(bg="white")  # Background putih

# Load gambar logo
image_path = "logo.png"  # Pastikan path sesuai
original_img = Image.open(image_path)

# Resize agar lebarnya 300px
new_width = 800
aspect_ratio = original_img.height / original_img.width
new_height = int(new_width * aspect_ratio)
resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
img_tk = ImageTk.PhotoImage(resized_img)

# Label untuk logo
logo_label = Label(root, image=img_tk, bg="white")
logo_label.image = img_tk  # Simpan referensi agar tidak dihapus GC
logo_label.grid(row=0, column=0, columnspan=2, pady=80)  # Tengah atas

# Atur Grid Layout
root.grid_columnconfigure(0, weight=1)  # Kolom 1 (Slideshow)
root.grid_columnconfigure(1, weight=1)  # Kolom 2 (Video)
root.grid_rowconfigure(0, weight=0)  # Logo (Kecil)
root.grid_rowconfigure(1, weight=1)  # Slideshow & Video (Sama Besar)

# Label Slideshow (Kiri)
slideshow_label = Label(root, bg="white")
slideshow_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

# Label Video Stream (Kanan)
video_label = Label(root, bg="white")
video_label.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")


# Thread untuk slideshow
threading.Thread(target=update_slideshow, daemon=True).start()
# Thread untuk video stream
threading.Thread(target=video_stream, daemon=True).start()

root.mainloop()
