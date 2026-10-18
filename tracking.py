"""Camera attention: hold a face, then follow meaningful foreground movement."""

import time


def focus_position(box, width, height):
    x, y, w, h = box
    return [
        max(-1.0, min(1.0, 2 * (x + w / 2) / width - 1)),
        max(-1.0, min(1.0, 1 - 2 * (y + h / 2) / height)),
    ]


class FocusTracker:
    def __init__(self):
        import cv2

        self.cv = cv2
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.previous = None
        self.target = [0.0, 0.0]
        self.gaze = [0.0, 0.0]
        self.seen = 0.0
        self.face_center = None

    def update(self, frame):
        cv = self.cv
        gray = cv.GaussianBlur(cv.cvtColor(frame, cv.COLOR_BGR2GRAY), (9, 9), 0)
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40)
        )
        mode = "none"
        if len(faces):

            def rank(box):
                point = focus_position(box, frame.shape[1], frame.shape[0])
                return (
                    sum((a - b) ** 2 for a, b in zip(point, self.face_center))
                    if self.face_center
                    else -box[2] * box[3]
                )

            box = min(faces, key=rank)
            self.target = focus_position(box, frame.shape[1], frame.shape[0])
            self.face_center = self.target
            mode = "face"
        elif self.previous is not None:
            mask = cv.threshold(
                cv.absdiff(gray, self.previous), 22, 255, cv.THRESH_BINARY
            )[1]
            mask = cv.dilate(mask, None, iterations=2)
            if cv.countNonZero(mask) < mask.size * 0.35:
                contours, _ = cv.findContours(
                    mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE
                )
                contours = [c for c in contours if cv.contourArea(c) > 300]
                if contours:
                    self.target = focus_position(
                        cv.boundingRect(max(contours, key=cv.contourArea)),
                        frame.shape[1],
                        frame.shape[0],
                    )
                    mode = "motion"
        self.previous = gray
        if mode != "none":
            self.seen = time.monotonic()
        elif time.monotonic() - self.seen > 1:
            self.target = [0.0, 0.0]
            self.face_center = None
        self.gaze = [a + (b - a) * 0.38 for a, b in zip(self.gaze, self.target)]
        return self.gaze, mode
