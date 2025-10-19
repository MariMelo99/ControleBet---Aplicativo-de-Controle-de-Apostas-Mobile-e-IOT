# api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, List
from datetime import datetime
import csv, os

app = FastAPI(title="XP Aposta Consciente - Events API")

# CORS: libere para Expo (web/Android em rede)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, restrinja para seu IP/domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Event(BaseModel):
    deviceId: str
    userId: str
    score: float = Field(ge=0, le=1)
    level: Literal["leve","medio","alto","neutro"]
    route: str
    ts: int  # epoch seconds

EVENTS: List[dict] = []
CSV_PATH = "events_log.csv"

def append_csv(e: Event):
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["ts_iso","deviceId","userId","score","level","route","ts"])
        w.writerow([
            datetime.utcfromtimestamp(e.ts).isoformat()+"Z",
            e.deviceId, e.userId, f"{e.score:.3f}", e.level, e.route, e.ts
        ])

@app.post("/events")
def add_event(e: Event):
    d = e.dict()
    d["receivedAt"] = datetime.utcnow().isoformat()+"Z"
    EVENTS.append(d)
    # limita memória (últimos 2000)
    if len(EVENTS) > 2000:
        del EVENTS[:-2000]
    append_csv(e)
    return {"ok": True}

@app.get("/events/last")
def last_event():
    return EVENTS[-1] if EVENTS else {}

@app.get("/events")
def list_events(limit: int = 100):
    return EVENTS[-limit:]
