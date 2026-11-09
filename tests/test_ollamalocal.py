import cv2
import os
import os
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'

from app.recognition.qwenlocalrecognizer import OllamaRecognizer
# This finds the directory of the current script and points to 'test.png' next to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(SCRIPT_DIR, "test.png")
 
image = cv2.imread(image_path)
if image is None:
    raise ValueError(f"Failed to load image from {image_path}")

recognizer = OllamaRecognizer(host="127.0.0.1", port=11434, model="llava:7b")
detections = recognizer.recognize(image, camera_id="camera1")

for detection in detections:
    print(f"Plate number: {detection.plate_number}")
    print(f"Confidence: {detection.confidence}")
    print("-" * 40)
