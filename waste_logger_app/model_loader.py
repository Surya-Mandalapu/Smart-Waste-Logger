# model_loader.py
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
import tensorflow as tf
import numpy as np
from PIL import Image
import io

model = MobileNetV2(weights="imagenet")  # No file needed

def classify_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
    image_array = np.array(image)
    image_array = preprocess_input(image_array)
    image_array = np.expand_dims(image_array, axis=0)

    predictions = model.predict(image_array)
    decoded = decode_predictions(predictions, top=1)[0][0]  # (class_id, label, confidence)

    return decoded[1], float(decoded[2])  # label, confidence