import cv2
import mediapipe as mp
import numpy as np

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

ZOOM_MAX = 2.5
ZOOM_MIN = 1.0
ZOOM_SPEED = 0.5

zoom_factor = 1.0
target_zoom = 1.0

zoom_center = None

def lerp(a, b, t):
    return a + (b - a) * t

import math

def angle_between_points(p1, p2, p3):
    a = np.array([p1.x, p1.y])
    b = np.array([p2.x, p2.y])
    c = np.array([p3.x, p3.y])
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

def is_finger_extended(landmarks, tip_id, pip_id, mcp_id):
    angle = angle_between_points(landmarks[tip_id], landmarks[pip_id], landmarks[mcp_id])
    return angle > 160

def is_spidey_pose(landmarks):
    thumb_extended = abs(landmarks[4].x - landmarks[0].x) > 0.1

    index_extended = is_finger_extended(landmarks, 8, 6, 5)
    middle_extended = is_finger_extended(landmarks, 12, 10, 9)
    ring_extended = is_finger_extended(landmarks, 16, 14, 13)
    pinky_extended = is_finger_extended(landmarks, 20, 18, 17)

    return thumb_extended and index_extended and (not middle_extended) and (not ring_extended) and pinky_extended


with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image)

        spidey_hands = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=4, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(0, 0, 0), thickness=4)
                )
                if is_spidey_pose(hand_landmarks.landmark):
                    spidey_hands.append(hand_landmarks)

        if len(spidey_hands) > 0:
            # Zoom in target
            target_zoom = min(ZOOM_MAX, target_zoom + ZOOM_SPEED)

            if len(spidey_hands) == 2:
                cx1 = int(spidey_hands[0].landmark[9].x * w)
                cy1 = int(spidey_hands[0].landmark[9].y * h)
                cx2 = int(spidey_hands[1].landmark[9].x * w)
                cy2 = int(spidey_hands[1].landmark[9].y * h)
                new_cx = (cx1 + cx2) // 2
                new_cy = (cy1 + cy2) // 2
            else:
                new_cx = int(spidey_hands[0].landmark[9].x * w)
                new_cy = int(spidey_hands[0].landmark[9].y * h)

            if zoom_factor < 1.05:
                zoom_center = (new_cx, new_cy)
        else:
            target_zoom = max(ZOOM_MIN, target_zoom - ZOOM_SPEED)

            if target_zoom == ZOOM_MIN:
                zoom_center = (w // 2, h // 2)

        zoom_factor = lerp(zoom_factor, target_zoom, 0.2)

        if zoom_center is None:
            zoom_center = (w // 2, h // 2)
        cx, cy = zoom_center

        new_w, new_h = int(w / zoom_factor), int(h / zoom_factor)
        x1 = max(0, cx - new_w // 2)
        y1 = max(0, cy - new_h // 2)
        x2 = min(w, x1 + new_w)
        y2 = min(h, y1 + new_h)

        if x2 - x1 < new_w:
            x1 = x2 - new_w
        if y2 - y1 < new_h:
            y1 = y2 - new_h
        x1, y1 = max(0, x1), max(0, y1)

        zoomed_frame = frame[y1:y2, x1:x2]
        zoomed_frame = cv2.resize(zoomed_frame, (w, h))

        cv2.imshow("Spidey Cam Zoom", zoomed_frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

cap.release()
cv2.destroyAllWindows()
