"""
Face Recognition Utilities for Exam System
Handles face encoding, verification, and validation
"""
import face_recognition
import numpy as np
import json
import base64
from PIL import Image
import io
import os


def encode_face_from_image(image_path):
    """
    Extract face encoding from an image file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        tuple: (encoding_json, error_message)
        - encoding_json: JSON string of face encoding if successful, None otherwise
        - error_message: Error description if failed, None otherwise
    """
    try:
        # Load the image
        image = face_recognition.load_image_file(image_path)
        
        # Find all face locations
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            return None, "No face detected in the image. Please upload a clear photo of your face."
        
        if len(face_locations) > 1:
            return None, "Multiple faces detected. Please upload an image with only your face."
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if len(face_encodings) == 0:
            return None, "Could not encode face. Please try a different image."
        
        # Convert numpy array to list and then to JSON
        encoding_list = face_encodings[0].tolist()
        encoding_json = json.dumps(encoding_list)
        
        return encoding_json, None
        
    except Exception as e:
        return None, f"Error processing image: {str(e)}"


def encode_face_from_base64(base64_image):
    """
    Extract face encoding from a base64-encoded image.
    
    Args:
        base64_image: Base64 string of the image (with or without data URI prefix)
        
    Returns:
        tuple: (encoding_json, error_message)
    """
    try:
        # Remove data URI prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Decode base64 to image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL Image to numpy array
        image_array = np.array(image)
        
        # Find face locations
        face_locations = face_recognition.face_locations(image_array)
        
        if len(face_locations) == 0:
            return None, "No face detected. Please ensure your face is clearly visible."
        
        if len(face_locations) > 1:
            return None, "Multiple faces detected. Please ensure only you are in the frame."
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(image_array, face_locations)
        
        if len(face_encodings) == 0:
            return None, "Could not encode face. Please try again with better lighting."
        
        # Convert to JSON
        encoding_list = face_encodings[0].tolist()
        encoding_json = json.dumps(encoding_list)
        
        return encoding_json, None
        
    except Exception as e:
        return None, f"Error processing image: {str(e)}"


def verify_face(known_encoding_json, test_image_base64, tolerance=0.6):
    """
    Verify if a test image matches the known face encoding.
    
    Args:
        known_encoding_json: JSON string of the stored face encoding
        test_image_base64: Base64 string of the test image
        tolerance: How much distance between faces to consider a match (lower is more strict)
        
    Returns:
        tuple: (is_match, similarity_score, error_message)
        - is_match: Boolean indicating if faces match
        - similarity_score: Float between 0-1 (higher is better match)
        - error_message: Error description if failed, None otherwise
    """
    try:
        # Decode the known encoding
        known_encoding = np.array(json.loads(known_encoding_json))
        
        # Get encoding from test image
        test_encoding_json, error = encode_face_from_base64(test_image_base64)
        
        if error:
            return False, 0.0, error
        
        test_encoding = np.array(json.loads(test_encoding_json))
        
        # Calculate face distance (lower is better)
        face_distance = face_recognition.face_distance([known_encoding], test_encoding)[0]
        
        # Convert distance to similarity score (0-1, higher is better)
        similarity_score = 1 - face_distance
        
        # Check if it's a match
        is_match = face_distance <= tolerance
        
        return is_match, float(similarity_score), None
        
    except Exception as e:
        return False, 0.0, f"Verification error: {str(e)}"


def is_valid_face_image(image_path):
    """
    Validate that an image contains exactly one clear face.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        tuple: (is_valid, message)
    """
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            return False, "No face detected in the image."
        
        if len(face_locations) > 1:
            return False, "Multiple faces detected. Please upload an image with only your face."
        
        return True, "Valid face image."
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"
