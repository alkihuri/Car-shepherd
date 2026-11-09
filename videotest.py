
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
import easyocr
import time
from datetime import datetime

RTSP_URL = "rtsp://admin:damin999@185.103.165.4:1554/ISAPI/Streaming/Channels/101"

SCAN_INTERVAL = 30

# Инициализация OCR
print("Loading EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)
print("EasyOCR ready")

# Подключение камеры
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Camera connection failed")
    exit()

print("Camera connected")

last_scan_time = 0

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to grab frame")
        break

    # Отображение видеопотока
    cv2.imshow("Camera", frame)

    current_time = time.monotonic()

    # OCR каждые 30 секунд
    if current_time - last_scan_time >= SCAN_INTERVAL:
        last_scan_time = current_time

        print("\n" + "=" * 50)
        print("OCR SCAN:", datetime.now().strftime("%H:%M:%S"))
        print("=" * 50)

        results = reader.readtext(
            frame,
            detail=1
        )

        if not results:
            print("No text detected")
        else:
            for bbox, text, confidence in results:
                print(
                    f"Text: {text} | "
                    f"Confidence: {confidence:.3f}"
                )

    # Выход по q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
