import sys, cv2

path = sys.argv[1] if len(sys.argv) > 1 else ""
print("OpenCV:", cv2.__version__, "| video:", path or "(webcam)")

cap = cv2.VideoCapture(path if path else 0)
if not cap.isOpened():
    print("[WARN] CAP_ANY falhou; tentando CAP_FFMPEG...")
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)

print("Opened?", cap.isOpened())
ok, frame = cap.read()
print("First frame:", ok)

if ok:
    cv2.imshow("Teste OpenCV", frame)
    cv2.waitKey(0)

cap.release()
cv2.destroyAllWindows()
