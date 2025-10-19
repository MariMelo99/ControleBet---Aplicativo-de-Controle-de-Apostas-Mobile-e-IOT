#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_no_mediapipe.py — Versão simplificada (sem MediaPipe)
- Detecta rosto com Haar Cascade (OpenCV)
- Calcula score simples com base em jitter + brilho da boca
- Exibe painel com texto e envia eventos para API FastAPI
"""

import argparse, time, csv, os
from collections import deque
import cv2
import numpy as np

try:
    import requests
except Exception:
    requests = None


# ------------------------ util: texto ------------------------

def normalize(text: str) -> str:
    """Troca acentos para evitar 'fantasmas' no putText do OpenCV."""
    return (text
            .replace("ç", "c").replace("Ç", "C")
            .replace("ã", "a").replace("Ã", "A")
            .replace("á", "a").replace("Á", "A")
            .replace("à", "a").replace("À", "A")
            .replace("â", "a").replace("Â", "A")
            .replace("é", "e").replace("É", "E")
            .replace("ê", "e").replace("Ê", "E")
            .replace("í", "i").replace("Í", "I")
            .replace("ó", "o").replace("Ó", "O")
            .replace("ô", "o").replace("Ô", "O")
            .replace("õ", "o").replace("Õ", "O")
            .replace("ú", "u").replace("Ú", "U")
            .replace("ñ", "n").replace("Ñ", "N"))

def put_text(img, text, org, scale=0.55, color=(255,255,255), thickness=2):
    """Texto com contorno leve para melhor leitura."""
    x, y = org
    cv2.putText(img, normalize(text), (x+1, y+1),
                cv2.FONT_HERSHEY_DUPLEX, scale, (0,0,0), thickness, cv2.LINE_AA)
    cv2.putText(img, normalize(text), (x, y),
                cv2.FONT_HERSHEY_DUPLEX, scale, color, thickness, cv2.LINE_AA)

def draw_panel(frame, score, level, route_label, *, pos="br",
               panel_w=300, alpha=0.7, margin=10, line_h=22):
    """Painel lateral com transparência e quebra simples."""
    h, w = frame.shape[:2]
    panel_w = int(max(220, min(panel_w, w*0.6)))

    # define canto
    x0 = w - panel_w - 10 if "r" in pos else 10
    y0 = h - 150 - 10 if "b" in pos else 10
    x1, y1 = x0 + panel_w, y0 + 150

    # fundo translucido
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (0,0,0), -1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (255,255,255), 1)

    # conteúdo
    y = y0 + margin + 18
    put_text(frame, "Aposta Consciente - XP (proto)", (x0+margin, y)); y += line_h
    put_text(frame, f"Stress score: {score:.2f}",         (x0+margin, y)); y += line_h
    put_text(frame, f"Nivel: {level}",                    (x0+margin, y)); y += line_h
    put_text(frame, "Sugestao:",                          (x0+margin, y)); y += line_h
    put_text(frame, route_label,                          (x0+margin, y))


# ------------------------ REST ------------------------

def post_event(api_base: str, payload: dict, timeout: float = 3.0):
    if not api_base or requests is None:
        return
    try:
        r = requests.post(f"{api_base}/events", json=payload, timeout=timeout)
        print(f"[POST] {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print("[WARN] Falha ao enviar evento:", e)


# ------------------------ Heuristica simples ------------------------

class SimpleFaceHeuristics:
    """Jitter (mudanca de pixels) + 'abertura de boca' por brilho na metade inferior."""
    def __init__(self):
        self.prev_roi = None

    def compute(self, frame_bgr, rect):
        x, y, w, h = rect
        roi = frame_bgr[y:y+h, x:x+w]
        if roi.size == 0:
            return 0.0, {"jitter": 0.0, "mouth_open": 0.0}

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        jitter = 0.0
        if self.prev_roi is not None and self.prev_roi.shape == gray.shape:
            jitter = float(cv2.absdiff(gray, self.prev_roi).mean()) / 255.0
        self.prev_roi = gray.copy()

        top = gray[:h//2, :]
        bot = gray[h//2:, :]
        mouth_open = max(0.0, float(bot.mean() - top.mean()) / 255.0)

        score = float(0.55 * jitter + 0.45 * mouth_open)
        return score, {"jitter": jitter, "mouth_open": mouth_open}


# ------------------------ Main ------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default="")
    parser.add_argument("--width", type=int, default=400)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8081")
    parser.add_argument("--user-id", type=str, default="admin")
    parser.add_argument("--device-id", type=str, default="xp-edge-01")
    parser.add_argument("--push-interval", type=float, default=1.0)
    parser.add_argument("--csv", type=str, default="")
    args = parser.parse_args()

    # fonte do video
    cap = cv2.VideoCapture(0 if not args.video else args.video)
    if not cap.isOpened():
        print("[ERRO] Não foi possivel abrir o video/webcam.")
        return

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    heur = SimpleFaceHeuristics()
    score_window = deque(maxlen=30)
    last_post_t = 0.0
    frame_idx = 0

    # CSV opcional
    csv_writer, csv_file = None, None
    if args.csv:
        csv_file = open(args.csv, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["frame", "score", "level", "jitter", "mouth_open"])

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]
        scale = args.width / float(w)
        frame = cv2.resize(frame, (args.width, int(h * scale)), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60,60))

        if len(faces) > 0:
            # maior rosto
            x, y, fw, fh = max(faces, key=lambda r: r[2]*r[3])

            score, parts = heur.compute(frame, (x, y, fw, fh))
            score_window.append(score)
            avg = float(np.mean(score_window))

            if   avg < args.threshold: level = "leve"
            elif avg < 0.70          : level = "medio"
            else                      : level = "alto"

            route = "Pausa guiada (respiracao 60s)" if level != "leve" else "Continuar tranquilo"

            color = (0,255,0) if level == "leve" else (0,0,255)
            cv2.rectangle(frame, (x,y), (x+fw,y+fh), color, 2)

            draw_panel(frame, avg, level, route, pos="br", panel_w=320)

            # envia evento com cooldown
            now = time.time()
            if now - last_post_t > args.push_interval and args.api:
                payload = {
                    "deviceId": args.device_id,
                    "userId":   args.user_id,
                    "score":    round(avg, 2),
                    "level":    level,
                    "route":    route,
                    "ts":       int(now)
                }
                post_event(args.api, payload)
                last_post_t = now

            if csv_writer:
                csv_writer.writerow([frame_idx, f"{avg:.4f}", level,
                                     f"{parts['jitter']:.4f}", f"{parts['mouth_open']:.4f}"])
        else:
            # sem rosto
            draw_panel(frame, 0.0, "neutro", "Sem rosto - pausar e respirar",
                       pos="br", panel_w=320)
            if csv_writer:
                csv_writer.writerow([frame_idx, "0.0000", "neutro", "0.0000", "0.0000"])

        put_text(frame, "ESC para sair", (20, 30), scale=0.6)
        cv2.imshow("XP - Aposta Consciente (no MediaPipe)", frame)
        if (cv2.waitKey(1) & 0xFF) == 27:
            break

        frame_idx += 1

    cap.release()
    if csv_file:
        csv_file.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
