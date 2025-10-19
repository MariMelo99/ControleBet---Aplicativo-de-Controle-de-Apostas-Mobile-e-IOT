ControleBet + IoT/IOB – Aposta Consciente (XP)

App mobile em React Native (Expo) integrado a um gateway IoT (FastAPI) que recebe eventos de análise facial (OpenCV) para incentivar apostas responsáveis.
Quando o módulo facial detecta estresse acima do limiar, ele envia eventos à API – que o app consome – e o usuário recebe orientações (ex.: Pausa guiada (respiração 60s)).

🔗 Módulos do projeto
Módulo	Pasta	Função	Tecnologias
Mobile (ControleBet)	Sprint-MobileDevelop/	App do usuário; dashboards, metas, perfil de risco	React Native, Expo, TypeScript
Gateway IoT (API)	Mobile_Challange-main/Mobile_Challange-main/	Recebe POST /events, expõe GET /events/last	FastAPI, Uvicorn
Análise Facial	Mobile_Challange-main/Mobile_Challange-main/	Processa vídeo, calcula stress score e envia para API	Python, OpenCV, NumPy

Importante: se você não tem webcam, use um arquivo de vídeo (ex.: face_400.mp4).

🧠 Como a integração funciona
flowchart LR
U[Usuário (vídeo/rosto)] --> F[OpenCV Python<br/>main_no_mediapipe.py]
F -- POST JSON --> A[FastAPI (IoT Gateway)<br/>/events, /events/last]
A -- GET JSON --> M[App Mobile (ControleBet)]
M --> UI[UI: alertas, metas, status]


O Python (OpenCV) calcula um score ∈ [0..1] e classifica:
leve (score < threshold), medio (score < 0.70), alto (≥ 0.70)

Envia payloads para a API:
{
  "deviceId": "xp-edge-01",
  "userId": "admin",
  "score": 0.72,
  "level": "alto",
  "route": "Pausa guiada (respiracao 60s)",
  "ts": 1734636000
}


O app consulta /events/last periodicamente e exibe as recomendações.
✅ Pré-requisitos
Node.js 18+ (para o app mobile)
Python 3.10+ (recomendado 3.10 ou 3.11 para máxima compatibilidade)
pip atualizado
Expo CLI (npx expo)
(Opcional) Android Studio/Xcode para emuladores

🛠️ Instalação das dependências (uma vez)
API + Facial (Python)
No Windows/PowerShell:

# Vá para a pasta da API/facial
cd "C:\Users\Meu Computador\Downloads\Mobile_Challange-main\Mobile_Challange-main"

# Crie e ative um venv
python -m venv .venv
.\.venv\Scripts\activate

# Instale libs
pip install --upgrade pip
pip install fastapi uvicorn requests opencv-python numpy

Mobile (React Native)

No diretório do app:
cd "C:\caminho\para\Sprint-MobileDevelop"
npm install --legacy-peer-deps

# Dependências do Expo usadas no projeto
npx expo install react-native-screens react-native-safe-area-context

▶️ Como rodar os 3 módulos (ordem recomendada)
1) Inicie o Gateway IoT (API FastAPI)
cd "C:\Users\Meu Computador\Downloads\Mobile_Challange-main\Mobile_Challange-main"
.\.venv\Scripts\activate
python -m uvicorn api:app --host 127.0.0.1 --port 8081 --reload


Teste no navegador: http://127.0.0.1:8081/docs
Você verá o Swagger com:
POST /events (recebe eventos do facial)
GET /events/last (último evento, para o Mobile consumir)
Teste rápido via PowerShell:

$body = @{
  deviceId = "xp-edge-01"
  userId   = "admin"
  score    = 0.72
  level    = "alto"
  route    = "Pausa guiada (respiracao 60s)"
  ts       = [int][double]::Parse((Get-Date -UFormat %s))
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8081/events" -Method Post -Body $body -ContentType "application/json"
Invoke-RestMethod -Uri "http://127.0.0.1:8081/events/last" -Method Get

2) Rode o processador facial (OpenCV)

Com o mesmo venv ativado:

# ainda em Mobile_Challange-main\Mobile_Challange-main
python .\main_no_mediapipe.py --video ".\face_400.mp4" --width 400 --api "http://127.0.0.1:8081" --user-id admin --device-id xp-edge-01 --push-interval 1.0 --threshold 0.35 --csv ".\scores_face.csv"


Você deve ver:
Janela do vídeo com retângulo no rosto;
Painel lateral com score/nível/sugestão;
No terminal da API, POST /events 200 aparecendo.
Sem webcam? Sem problemas. O comando acima já usa face_400.mp4.
Sem GUI? Gere um vídeo processado:
--out-video ".\output_face.mp4"

3) Rode o app Mobile (ControleBet)
cd "C:\caminho\para\Sprint-MobileDevelop"
npx expo start


Aponte o app para a API (duas opções):
Opção A – Arquivo de configuração
Crie .env na raiz do app:

EXPO_PUBLIC_API_BASE=http://127.0.0.1:8081

E no código (ex. services/api.ts):
export const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "http://127.0.0.1:8081";


Opção B – Valor fixo em código (rápido)
export const API_BASE = "http://127.0.0.1:8081";


Consumo do evento no app (exemplo de polling a cada 5s):

// services/events.ts
export async function fetchLastEvent() {
  const res = await fetch(`${API_BASE}/events/last`);
  if (!res.ok) throw new Error("API error");
  return res.json();
}

// Em Home.tsx (ou Context)
useEffect(() => {
  let isMounted = true;
  const tick = async () => {
    try {
      const data = await fetchLastEvent();
      if (isMounted && data?.level) setStressInfo(data); // exibe no UI
    } catch {}
  };
  tick();
  const id = setInterval(tick, 5000);
  return () => { isMounted = false; clearInterval(id); };
}, []);


Abra no Expo Go (QR), Android emulator (a) ou iOS simulator (i).
Credenciais de teste (app):
Usuário: admin
Senha: 12345

📡 Endpoints expostos pela API

POST /events – recebe um evento do facial
Body (JSON):

{
  "deviceId": "xp-edge-01",
  "userId": "admin",
  "score": 0.55,
  "level": "medio",
  "route": "Pausa guiada (respiracao 60s)",
  "ts": 1734636000
}


GET /events/last – retorna o último evento recebido
Exemplo de resposta:

{
  "ok": true,
  "event": {
    "deviceId": "xp-edge-01",
    "userId": "admin",
    "score": 0.72,
    "level": "alto",
    "route": "Pausa guiada (respiracao 60s)",
    "ts": 1734636000
  }
}

🧮 Como o score e o nível funcionam (facial)

Score ∈ [0..1] calculado por heurística leve:

jitter (variação quadro a quadro no ROI facial),

mouth_open (brilho médio metade inferior − superior na região da boca).

Níveis:
leve → score < --threshold (padrão 0.35)
medio → score < 0.70
alto → score ≥ 0.70

Sugestão:
leve → “Continuar tranquilo”
medio/alto → “Pausa guiada (respiracao 60s)”

🧪 Roteiro de demo (até 5 min)
Arquitetura (30–45s): mostre o diagrama (Flowchart).
API (30s): rode o Uvicorn e abra http://127.0.0.1:8081/docs.
Facial (1–2min): rode main_no_mediapipe.py, mostre o vídeo e os POST no terminal da API.
Mobile (1–2min): abra o app (Expo), mostre que a tela consome /events/last e atualiza sugestões.
Fechamento (30s): reforço de uso responsável + próximos passos (notificações, dashboard, etc.).

🧯 Troubleshooting rápido
“Não abre vídeo”: use check_video.py e teste com caminho absoluto; se necessário recodifique para H.264.
ModuleNotFoundError: cv2: instale opencv-python no mesmo venv ativo.
CORS no mobile: se testar em dispositivo físico, troque 127.0.0.1 pelo IP da máquina na mesma rede (ex.: http://192.168.15.123:8081) e use esse IP no .env do app.
Porta ocupada: mude --port no Uvicorn (ex.: 8082) e atualize API_BASE no app.
Sem webcam: passe --video "face_400.mp4" (já previsto).

📦 Tecnologias

Mobile: React Native, Expo, TypeScript, AsyncStorage, react-navigation, chart-kit, SVG
API: FastAPI, Uvicorn
Facial: Python, OpenCV, NumPy, Requests

👥 Equipe

Irana Pereira – RM98593
Lucas Vinicius – RM98480
Mariana Melo – RM98121
Mateus Iago – RM550270

📄 Licença
Projeto acadêmico – FIAP (2025). Uso educacional.
