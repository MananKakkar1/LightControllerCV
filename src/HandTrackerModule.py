import cv2 as cv
import mediapipe as mp


class HandTracker:
    def __init__(self, mode=False, maxHands=2, detectionCon=0.4, trackCon=0.6):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            model_complexity=1,
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon,
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.results = None

    def findHands(self, img, draw=True):
        imgRGB = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        if self.results and self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img

    def findPosition(self, img, handNo=0, draw=True):
        lmList = []
        if self.results and self.results.multi_hand_landmarks:
            myHand = self.results.multi_hand_landmarks[handNo]
            h, w, _ = img.shape
            for id, lm in enumerate(myHand.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])
                if draw:
                    cv.circle(img, (cx, cy), 7, (255, 0, 0), cv.FILLED)
        return lmList

    def hands_info(self, img, draw=False):
        """Return list of hands with label, center, and pixel landmarks.

        Each entry: { 'label': 'Left'|'Right'|None, 'center': (cx,cy), 'lm': [(x,y)*21] }
        """
        info = []
        if self.results and self.results.multi_hand_landmarks:
            h, w, _ = img.shape
            handed = []
            try:
                handed = self.results.multi_handedness or []
            except Exception:
                handed = []

            for idx, handLms in enumerate(self.results.multi_hand_landmarks):
                lm_xy = []
                sx = 0.0
                sy = 0.0
                n = 0
                for lm in handLms.landmark:
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    lm_xy.append((x, y))
                    sx += lm.x
                    sy += lm.y
                    n += 1
                cx = int((sx / max(1, n)) * w)
                cy = int((sy / max(1, n)) * h)
                label = None
                try:
                    label = handed[idx].classification[0].label
                except Exception:
                    pass
                info.append({"label": label, "center": (cx, cy), "lm": lm_xy})
                if draw:
                    self.mpDraw.draw_landmarks(img, self.results.multi_hand_landmarks[idx], self.mpHands.HAND_CONNECTIONS)
                    cv.circle(img, (cx, cy), 6, (0, 255, 255), -1)
        return info
