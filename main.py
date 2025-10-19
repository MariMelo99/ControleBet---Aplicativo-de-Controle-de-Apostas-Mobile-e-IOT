#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_final.py — Versão sem MediaPipe (compatível com Python 3.13)
- Detecta rosto com Haar Cascade (OpenCV)
- Calcula um score simples (0..1) usando:
    * jitter (movimento no ROI do rosto entre frames)
    * mouth_open_proxy (média da metade inferior do rosto vs superior)
- Exibe painel lateral com quebra de linha
- Gera CSV opcional
- Dispara "rota" (leve/médio/alto) via TrainingRouter
- Integração REST/FastAPI (#3): POST /events (deviceId, userId, score, level, route, ts)
- (Opcional) salva vídeo processado com --out-video quando não há GUI

Dependências: opencv-python, numpy, (opcional) requests
"""

import argparse, time, csv, os, sys, json
from collections import deque
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np

try:
    import requests  # recomendado para REST
except Exception:
    requests = None

from training_router import TrainingRouter  # seu router já existente


# ==================== UI helpers ====================
def put_text(img, text, org, scale=0.6, thickness=2):
    cv2.putText(img, text, (org[0]+1, org[1]+1),
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0,0,0), thickness, cv2.LINE_AA)
    cv2.putText(img, text, org,
                cv2.FONT_HERSHEY_SIMPLEX, scale, (255,255,255), thickness, cv2.LINE_AA)

def draw_panel(frame, score, level, route_label, *,
               pos="tr", panel_w=280, alpha=0.75, font_scale=0.6,
               line_spacing=6, margin=10):
    h, w = frame.shape[:2]
    panel_w = int(max(180, min(panel_w, w * 0.6)))
    avail_w = panel_w - 2 * margin

    def txt_sz(t: str) -> Tuple[int,int]:
        (tw, th), _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        return tw, th

    def wrap_line(text: str) -> list[str]:
        words = text.split()
        if not words: return [""]
        lines, cur = [], ""
        for tok in words:
            test = (cur + " " + tok).strip()
            if not cur or txt_sz(test)[0] <= avail_w:
                cur = test
            else:
                lines.append(cur); cur = tok
        if cur: lines.append(cur)
        return lines

    base = [
        "Aposta Consciente - XP (proto)",
        f"Stress score: {score:.2f}",
        f"Nível: {level}",
        "Sugestão:",
    ]
    expanded = []
    for L in base: expanded.extend(wrap_line(L))
    expanded.extend(wrap_line(route_label))

    heights = [txt_sz(L)[1] for L in expanded]
    total_text_h = sum(heights) + line_spacing*(len(expanded)-1)
    panel_h = total_text_h + 2*margin

    x0 = (w - panel_w - 10) if pos in ("tr","br") else 10
    y0 = 10 if pos in ("tr","tl") else (h - panel_h - 10)

    overlay = frame.copy()
    cv2.rectangle(overlay, (x0,y0), (x0+panel_w, y0+panel_h), (0,0,0), -1)
    cv2.rectangle(overlay, (x0,y0), (x0+panel_w, y0+panel_h), (255,255,255), 1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)

    y = y0 + margin + heights[0]
    for i, L in enumerate(expanded):
        put_text(frame, L, (x0+margin, y), scale=font_scale)
        if i < len(expanded)-1:
            y += heights[i+1] + line_spacing


# ==================== Integração REST (FastAPI) ====================
def post_event(base_url: str, payload: Dict[str,Any], timeout: float=2.5) -> Optional[int]:
    """
    Envia POST para {base_url}/events com JSON payload.
    Espera FastAPI em api.py (endpoint /events).
    """
    if not base_url:
        return None
    endpoint = base_url.rstrip("/") + "/events"
    try:
        if requests is not None:
            resp = requests.post(endpoint, json=payload, timeout=timeout)
            return getattr(resp, "status_code", None)
        # fallback nativo
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return getattr(r, "status", None)
    except Exception as e:
        print("[WARN] Falha ao enviar evento:", e)
        return None


# ==================== Heurísticas simples (sem landmarks) ====================
class SimpleFaceHeuristics:
    def __init__(self):
        self.prev_roi = None

    @staticmethod
    def _norm01(x):
        return float(max(0.0, min(1.0, x)))

    def compute(self, frame_bgr, face_rect) -> Tuple[float, Dict[str,float]]:
        x,y,w,h = face_rect
        roi = frame_bgr[y:y+h, x:x+w]
        if roi.size == 0:
            return 0.0, {"jitter":0.0, "mouth_open":0.0, "eye_open":0.0,
                         "eye_tension":0.0, "brow_tension":0.0, "mouth_press":0.0,
                         "mouth_gasp":0.0, "brow_eye_min":0.0}

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # --- JITTER: movimento médio no ROI (normalizado)
        jitter = 0.0
        if self.prev_roi is not None and self.prev_roi.shape == gray.shape:
            diff = cv2.absdiff(gray, self.prev_roi)
            jitter = float(diff.mean())/255.0
        self.prev_roi = gray.copy()

        # --- "Abertura da boca" proxy: média brilho metade inferior vs superior
        h2 = gray.shape[0]//2
        top = gray[:h2, :]
        bot = gray[h2:, :]
        diff_mean = max(0.0, float(bot.mean() - top.mean())) / 255.0
        mouth_open = self._norm01(diff_mean * 2.0)  # ganho

        # score final simples
        score = self._norm01(0.55*jitter + 0.45*mouth_open)

        parts = {
            "jitter": float(jitter),
            "mouth_open": float(mouth_open),
            "eye_open": 0.0,
            "eye_tension": 0.0,
            "brow_tension": 0.0,
            "mouth_press": 0.0,
            "mouth_gasp": 0.0,
            "brow_eye_min": 0.0
        }
        return score, parts


# ==================== Main ====================
def main():
    parser = argparse.ArgumentParser()
    # vídeo/execução
    parser.add_argument("--video", type=str, default="", help="Caminho do arquivo de vídeo. Vazio = webcam.")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--no-draw", action="store_true", help="Não desenhar retângulo do rosto.")
    parser.add_argument("--threshold", type=float, default=0.65, help="Limiar de alerta (0..1)")
    parser.add_argument("--cooldown", type=float, default=8.0, help="Tempo mínimo (s) entre alertas")
    parser.add_argument("--csv", type=str, default="", help="Se definido, exporta CSV com score por frame.")
    # REST/FastAPI
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", type=str, default="demo-admin")
    parser.add_argument("--device-id", type=str, default="xp-edge-01")
    parser.add_argument("--push-interval", type=float, default=1.0)
    help="Intervalo mínimo (s) entre POSTs de eventos"
    # painel
    parser.add_argument("--panel-pos", type=str, default="tr", help="tr, tl, br, bl")
    parser.add_argument("--panel-w", type=int, default=280, help="Largura do painel (px)")
    parser.add_argument("--panel-alpha", type=float, default=0.75, help="Transparência (0..1)")
    parser.add_argument("--font-scale", type=float, default=0.6, help="Fonte do painel")
    parser.add_argument("--no-panel", action="store_true", help="Não desenhar painel")
    # headless
    parser.add_argument("--out-video", type=str, default="", help="Se informado, salva MP4 processado (sem janela).")

    args = parser.parse_args()

    # vídeo
    cap = cv2.VideoCapture(0 if not args.video else args.video)
    if args.video:
        print(f"[INFO] Abrindo vídeo: {args.video}")
    if not cap.isOpened():
        print("[ERRO] Não foi possível abrir webcam/arquivo de vídeo.")
        return

    # CSV
    csv_writer, csv_file = None, None
    if args.csv:
        out_dir = os.path.dirname(args.csv)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        try:
            csv_file = open(args.csv, "w", newline="", encoding="utf-8")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                "frame_idx", "time_sec", "score", "level", "route",
                "eye_tension", "brow_tension", "mouth_press", "mouth_gasp", "jitter",
                "eye_open", "mouth_open", "brow_eye_min"
            ])
            print(f"[CSV] Gravando em: {args.csv}")
        except Exception as e:
            print(f"[WARN] CSV indisponível ({e}). Segue sem CSV.")
            csv_writer = None

    target_w = max(320, int(args.width))
    router = TrainingRouter()
    heur = SimpleFaceHeuristics()
    score_window = deque(maxlen=30)
    last_alert_t = 0.0
    frame_idx = 0
    t0 = time.time()

    # controle de envio REST
    last_push = 0.0

    # Haar Cascade
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # VideoWriter (headless)
    writer = None
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # resize mantendo proporção
        h, w = frame.shape[:2]
        if w <= 0 or h <= 0:
            continue
        scale = target_w / float(w)
        frame = cv2.resize(frame, (target_w, int(h*scale)), interpolation=cv2.INTER_AREA)

        # inicializa writer se for salvar vídeo processado
        if writer is None and args.out_video:
            out_h, out_w = frame.shape[:2]
            writer = cv2.VideoWriter(args.out_video, fourcc, 30.0, (out_w, out_h))

        # detecção de rosto
        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_full = cv2.equalizeHist(gray_full)
        faces = face_cascade.detectMultiScale(gray_full, scaleFactor=1.1, minNeighbors=5, minSize=(60,60))

        if len(faces) > 0:
            faces = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)
            x, y, w0, h0 = faces[0]

            score, parts = heur.compute(frame, (x,y,w0,h0))
            score_window.append(score)
            score_smooth = float(np.mean(score_window))

            level, route_key = router.map_score_to_route(score_smooth, args.threshold)
            alert_label = router.routes[route_key]["label"]

            if not args.no_draw:
                cv2.rectangle(frame, (x,y), (x+w0, y+h0),
                              (0,255,0) if score_smooth < args.threshold else (0,0,255), 2)

            # barra + HUD
            bar_w = 220; bar_x, bar_y = 20, 20
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 18), (50,50,50), 1)
            fill = int(bar_w * max(0.0, min(1.0, score_smooth)))
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + 18),
                          (0,255,0) if score_smooth < args.threshold else (0,0,255), -1)
            put_text(frame, f"score={score_smooth:.2f}  thr={args.threshold:.2f}", (bar_x, bar_y+38), 0.55, 2)

            if not args.no_panel:
                draw_panel(frame, score_smooth, level, alert_label,
                           pos=args.panel_pos, panel_w=args.panel_w,
                           alpha=args.panel_alpha, font_scale=args.font_scale)

            # evento/rota (cooldown) — apenas log
            now = time.time()
            if score_smooth >= args.threshold and (now - last_alert_t) > args.cooldown:
                last_alert_t = now
                print(f"[ROTA] {alert_label} | score={score_smooth:.2f} | parts={parts}")

            # ===== envio REST periódico =====
            if args.api and (time.time() - last_push) >= args.push_interval:
                payload = {
                    "deviceId": args.device_id,
                    "userId": args.user_id,
                    "score": float(round(score_smooth, 3)),
                    "level": level,             # "leve" | "medio" | "alto" | "neutro"
                    "route": alert_label,
                    "ts": int(time.time())
                }
                status = post_event(args.api, payload)
                if status is not None:
                    print(f"[POST] /events -> HTTP {status}  payload={payload}")
                last_push = time.time()

            # CSV
            if csv_writer is not None:
                t_rel = time.time() - t0
                csv_writer.writerow([
                    frame_idx, f"{t_rel:.3f}", f"{score_smooth:.6f}", level, alert_label,
                    f"{parts.get('eye_tension', 0.0):.6f}",
                    f"{parts.get('brow_tension', 0.0):.6f}",
                    f"{parts.get('mouth_press', 0.0):.6f}",
                    f"{parts.get('mouth_gasp', 0.0):.6f}",
                    f"{parts.get('jitter', 0.0):.6f}",
                    f"{parts.get('eye_open', 0.0):.6f}",
                    f"{parts.get('mouth_open', 0.0):.6f}",
                    f"{parts.get('brow_eye_min', 0.0):.6f}",
                ])

        else:
            # sem rosto
            level = "neutro"
            alert_label = "Sem rosto - pausar e respirar"
            score_smooth = 0.0

            if not args.no_panel:
                draw_panel(frame, score_smooth, level, alert_label,
                           pos=args.panel_pos, panel_w=args.panel_w,
                           alpha=args.panel_alpha, font_scale=args.font_scale)

            # envio REST periódico mesmo sem rosto (útil p/ presença)
            if args.api and (time.time() - last_push) >= args.push_interval:
                payload = {
                    "deviceId": args.device_id,
                    "userId": args.user_id,
                    "score": 0.0,
                    "level": level,
                    "route": alert_label,
                    "ts": int(time.time())
                }
                status = post_event(args.api, payload)
                if status is not None:
                    print(f"[POST] /events -> HTTP {status}  payload={payload}")
                last_push = time.time()

            if csv_writer is not None:
                t_rel = time.time() - t0
                csv_writer.writerow([
                    frame_idx, f"{t_rel:.3f}", "0.000000", level,
                    alert_label, 0,0,0,0,0,0,0,0
                ])

        # saída: janela ou arquivo
        if writer is not None:
            writer.write(frame)
        else:
            try:
                put_text(frame, "ESC para sair", (20, 30), 0.6, 2)
                cv2.imshow("XP - Aposta Consciente (proto) — sem MediaPipe", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
            except Exception as e:
                print("[WARN] Sem GUI; salve com --out-video. Detalhe:", e)
                break

        frame_idx += 1

    # limpeza
    try: cap.release()
    except: pass
    if writer is not None:
        try: writer.release()
        except: pass
    try: cv2.destroyAllWindows()
    except: pass
    if csv_file is not None:
        try: csv_file.close(); print(f"[CSV] Finalizado: {args.csv}")
        except: pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try: cv2.destroyAllWindows()
        except: pass
        sys.exit(130)
