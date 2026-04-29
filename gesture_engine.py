"""
gesture_engine.py
-----------------
MediaPipe-powered hand gesture detection module.
Exports GestureEngine class with gesture enum and wrist position tracking.
"""

import cv2
import mediapipe as mp
import numpy as np
from enum import Enum, auto


class Gesture(Enum):
    NONE        = auto()
    OPEN_PALM   = auto()   # 5 fingers → move
    FIST        = auto()   # 0 fingers → shoot
    PEACE       = auto()   # 2 fingers (index+middle) → shield
    PINCH       = auto()   # thumb+index close → mega blast
    THUMBS_UP   = auto()   # thumb up, rest down → pause


class GestureEngine:
    """
    Captures webcam frames, runs MediaPipe Hands, classifies gestures.
    """

    # Tuning knobs
    PINCH_THRESHOLD   = 0.08   # normalised distance for pinch detection
    MIN_DETECTION_CONF = 0.70
    MIN_TRACKING_CONF  = 0.60

    def __init__(self, camera_index: int = 0, flip: bool = True):
        self.cap = cv2.VideoCapture(camera_index)
        self.flip = flip
        self.available = self.cap.isOpened()

        self.mp_hands    = mp.solutions.hands
        self.mp_drawing  = mp.solutions.drawing_utils
        self.mp_styles   = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=self.MIN_DETECTION_CONF,
            min_tracking_confidence=self.MIN_TRACKING_CONF,
        )

        # Public state (updated each frame)
        self.gesture:    Gesture = Gesture.NONE
        self.wrist_x:    float   = 0.5   # 0.0 (left) – 1.0 (right)
        self.wrist_y:    float   = 0.5
        self.landmarks             = None
        self.annotated_frame       = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self):
        """Read one frame, detect gesture, update public attributes."""
        if not self.available:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        if self.flip:
            frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        annotated = frame.copy()

        if results.multi_hand_landmarks:
            hand_lm = results.multi_hand_landmarks[0]

            # Draw landmarks with custom style
            self.mp_drawing.draw_landmarks(
                annotated,
                hand_lm,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )

            self.landmarks = hand_lm.landmark
            wrist = self.landmarks[0]
            self.wrist_x = float(wrist.x)
            self.wrist_y = float(wrist.y)
            self.gesture = self._classify(self.landmarks)
        else:
            self.landmarks = None
            self.gesture   = Gesture.NONE

        # Overlay gesture label
        label = self.gesture.name.replace("_", " ")
        color_map = {
            Gesture.OPEN_PALM: (0, 255, 120),
            Gesture.FIST:      (0, 60,  255),
            Gesture.PEACE:     (255, 200, 0),
            Gesture.PINCH:     (255, 0,  200),
            Gesture.THUMBS_UP: (0, 220,  255),
            Gesture.NONE:      (180, 180, 180),
        }
        col = color_map.get(self.gesture, (255, 255, 255))
        cv2.putText(annotated, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2, cv2.LINE_AA)

        self.annotated_frame = annotated

    def get_pygame_surface(self, width: int, height: int):
        """Return annotated camera frame as a Pygame-compatible RGB array."""
        import pygame
        if self.annotated_frame is None:
            return None
        frame = cv2.resize(self.annotated_frame, (width, height))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Pygame surface from numpy array
        surf = pygame.surfarray.make_surface(np.rot90(frame_rgb))
        return surf

    def release(self):
        self.cap.release()
        self.hands.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify(self, lm) -> Gesture:
        """Rule-based gesture classifier from MediaPipe landmarks."""
        fingers_up = self._fingers_up(lm)
        total_up   = sum(fingers_up)

        # Pinch: thumb tip close to index tip
        if self._pinch_detected(lm):
            return Gesture.PINCH

        # Thumbs up: only thumb extended, rest curled
        if fingers_up[0] == 1 and total_up == 1:
            return Gesture.THUMBS_UP

        # Fist: no fingers extended
        if total_up == 0:
            return Gesture.FIST

        # Peace: only index + middle up
        if fingers_up[1] == 1 and fingers_up[2] == 1 and fingers_up[3] == 0 and fingers_up[4] == 0:
            return Gesture.PEACE

        # Open palm: 4-5 fingers extended
        if total_up >= 4:
            return Gesture.OPEN_PALM

        return Gesture.NONE

    def _fingers_up(self, lm) -> list:
        """Return [thumb, index, middle, ring, pinky] as 0/1."""
        tips  = [4, 8, 12, 16, 20]
        up    = []

        # Thumb: compare x instead of y (side axis)
        if lm[tips[0]].x < lm[tips[0] - 1].x:
            up.append(1)
        else:
            up.append(0)

        # Other fingers: tip y above pip y
        for i in range(1, 5):
            if lm[tips[i]].y < lm[tips[i] - 2].y:
                up.append(1)
            else:
                up.append(0)

        return up

    def _pinch_detected(self, lm) -> bool:
        dx = lm[4].x - lm[8].x
        dy = lm[4].y - lm[8].y
        dist = (dx**2 + dy**2) ** 0.5
        return dist < self.PINCH_THRESHOLD
