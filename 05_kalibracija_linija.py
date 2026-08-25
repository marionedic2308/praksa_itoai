import cv2

video_path = "test03.mp4"
tocke = []
linije = []

cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
cap.release()

if not ret:
    print("GREŠKA: Nije moguće učitati video.")
    exit()

def klik_mis(event, x, y, flags, param):
    global tocke, linije, frame

    if event == cv2.EVENT_LBUTTONDOWN:
        tocke.append((x, y))

        if len(tocke) == 2:
            linije.append((tocke[0], tocke[1]))
            cv2.line(frame, tocke[0], tocke[1], (0, 255, 0), 3)
            print(f"Linija {len(linije)}: ({tocke[0]}, {tocke[1]})")
            tocke = []

cv2.namedWindow("Kalibracija linija", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Kalibracija linija", klik_mis)

print("Klikni dvije točke za svaku liniju.")
print("ESC = izlaz")

while True:
    cv2.imshow("Kalibracija linija", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == 27:  # ESC
        break

cv2.destroyAllWindows()

print("\nKopiraj ove linije u kod:")
print("linije = {")

for i, linija in enumerate(linije, start=1):
    print(f'    "Traka {i}": ({linija[0]}, {linija[1]}),')

print("}")