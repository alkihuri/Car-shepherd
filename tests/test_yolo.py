import os
import cv2
from ultralytics import YOLO
import easyocr

# ---------- 1. Модель для детекции МАШИН ----------
# yolov8n.pt — официальные веса, скачаются автоматически при первом запуске.
# Классы COCO: 2=car, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 5, 7]

model_path = "tests/yolov8n.pt"
if not os.path.isfile(model_path):
    # Ultralytics сам скачает yolov8n.pt в текущую папку, если передать только имя
    print(f"[INFO] {model_path} не найден локально — Ultralytics скачает стандартные веса.")
    model_path = "yolov8n.pt"

model = YOLO(model_path)
print(f"[INFO] Модель загружена: {model_path}")

# ---------- 2. OCR ----------
# Один раз при старте. gpu=True работает на Apple Silicon через MPS (если установлен torch с MPS).
reader = easyocr.Reader(['en'], gpu=True)

# ---------- 3. Кадр ----------
image_path = "tests/test3.png"
image = cv2.imread(image_path)
if image is None:
    raise FileNotFoundError(f"Не удалось загрузить изображение: {image_path}")

# ---------- 4. Детекция машин ----------
# conf=0.4 — порог уверенности, classes — фильтр по классам
results = model(image, conf=0.4, verbose=False, classes=VEHICLE_CLASSES)

vehicle_boxes = []
for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        vehicle_boxes.append((x1, y1, x2, y2, cls_id, conf))

if not vehicle_boxes:
    print("[INFO] Машины на кадре не найдены.")
    cv2.imshow("Result", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    raise SystemExit(0)

print(f"[INFO] Найдено машин: {len(vehicle_boxes)}")

# ---------- 5. Для каждой машины: кроп → OCR ----------
for idx, (vx1, vy1, vx2, vy2, cls_id, conf) in enumerate(vehicle_boxes, 1):
    # Рисуем рамку машины
    cv2.rectangle(image, (vx1, vy1), (vx2, vy2), (255, 0, 0), 2)
    label = f"vehicle {idx} (cls={cls_id}, {conf:.2f})"
    cv2.putText(image, label, (vx1, max(vy1 - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Кроп машины
    car_crop = image[vy1:vy2, vx1:vx2]
    if car_crop.size == 0:
        continue

    # ---------- 5a. Внутри машины ищем номер ----------
    # Вариант "в лоб": прогоняем OCR по всему кропу машины.
    # Он найдёт весь текст (включая надписи на кузове), поэтому фильтруем по длине/формату.
    ocr_results = reader.readtext(car_crop, detail=1)  # detail=1 → (bbox, text, conf)

    # Собираем кандидатов в номер: строки длиной 5–10 символов, буквы+цифры
    plate_candidates = []
    for bbox, text, ocr_conf in ocr_results:
        cleaned = "".join(ch for ch in text.upper() if ch.isalnum())
        # Простая эвристика: номер обычно 5–10 символов, есть и буквы, и цифры
        has_alpha = any(c.isalpha() for c in cleaned)
        has_digit = any(c.isdigit() for c in cleaned)
        if 5 <= len(cleaned) <= 10 and (has_alpha or has_digit):
            plate_candidates.append((cleaned, ocr_conf, bbox))

    if not plate_candidates:
        print(f"[{idx}] Машина {idx}: номер не распознан.")
        continue

    # Берём самого уверенного кандидата
    plate_text, plate_conf, plate_bbox = max(plate_candidates, key=lambda x: x[1])
    print(f"[{idx}] Машина {idx}: найден номер '{plate_text}' (OCR conf={plate_conf:.2f})")

    # Рисуем найденный номер на исходном изображении (координаты относительно машины)
    px1, py1, px2, py2 = map(int, plate_bbox[0])
    # Переводим координаты из кропа машины в координаты исходного изображения
    gx1, gy1 = vx1 + px1, vy1 + py1
    gx2, gy2 = vx1 + px2, vy1 + py2
    cv2.rectangle(image, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
    cv2.putText(image, plate_text, (gx1, max(gy1 - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# ---------- 6. Показ ----------
cv2.imshow("Result", image)
cv2.waitKey(0)
cv2.destroyAllWindows()