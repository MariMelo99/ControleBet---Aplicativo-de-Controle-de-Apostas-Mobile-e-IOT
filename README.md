🎯 ControleBet + IoT/IOB – Aposta Consciente (XP)

🧩 App mobile em React Native (Expo) integrado a um gateway IoT (FastAPI) que recebe eventos de análise facial (OpenCV) para incentivar apostas responsáveis.
Quando o módulo facial detecta estresse acima do limiar, ele envia eventos à API – que o app consome – e o usuário recebe orientações como:
💬 “Pausa guiada (respiração 60s)”.

🔗 Módulos do Projeto
Módulo	Pasta	Função	Tecnologias
Mobile (ControleBet)	Sprint-MobileDevelop/	App do usuário; dashboards, metas, perfil de risco	React Native, Expo, TypeScript
Gateway IoT (API)	Mobile_Challange-main/Mobile_Challange-main/	Recebe POST /events, expõe GET /events/last	FastAPI, Uvicorn
Análise Facial	Mobile_Challange-main/Mobile_Challange-main/	Processa vídeo, calcula stress score e envia para API	Python, OpenCV, NumPy

📸 Sem webcam?
Use um arquivo de vídeo (ex.: face_400.mp4).

🧠 Como a integração funciona
flowchart LR
U[🎥 Usuário (vídeo/rosto)] --> F[🧠 OpenCV Python<br/>main_no_mediapipe.py]
F -- POST JSON --> A[🌐 FastAPI (IoT Gateway)<br/>/events & /events/last]
A -- GET JSON --> M[📱 App Mobile (ControleBet)]
M --> UI[🖥️ UI: alertas, metas, status]


Heurística de Score:

score ∈ [0..1]
leve:   score < threshold
médio:  score < 0.70
alto:   score ≥ 0.70


Payload enviado à API:

{
  "deviceId": "xp-edge-01",
  "userId": "admin",
  "score": 0.72,
  "level": "alto",
  "route": "Pausa guiada (respiracao 60s)",
  "ts": 1734636000
}


O app consome periodicamente /events/last e atualiza recomendações na UI.

✅ Pré-requisitos
Componente	Versão recomendada
Node.js	18+
Python	3.10+ (ideal 3.10 ou 3.11)
pip	Atualizado
Expo CLI	npm install -g expo-cli
Emulador (opcional)	Android Studio ou Xcode
🛠️ Instalação das dependências (1x)
🔹 API + Facial (Python)
# Vá para a pasta da API/facial
cd "C:\Users\Meu Computador\Downloads\Mobile_Challange-main\Mobile_Challange-main"

# Crie e ative um ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate

# Instale dependências
pip install --upgrade pip
pip install fastapi uvicorn requests opencv-python numpy

🔹 Mobile (React Native)
cd "C:\caminho\para\Sprint-MobileDevelop"
npm install --legacy-peer-deps

# Dependências Expo usadas no projeto
npx expo install react-native-screens react-native-safe-area-context

▶️ Execução – Ordem recomendada
1️⃣ Inicie o Gateway IoT (API FastAPI)
cd "C:\Users\Meu Computador\Downloads\Mobile_Challange-main\Mobile_Challange-main"
.\.venv\Scripts\activate
python -m uvicorn api:app --host 127.0.0.1 --port 8081 --reload


🌍 Teste no navegador: http://127.0.0.1:8081/docs

Endpoints disponíveis:

POST /events → recebe eventos do facial

GET /events/last → último evento para o app consumir

Teste rápido (PowerShell):

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

2️⃣ Rode o Processador Facial (OpenCV)
# ainda em Mobile_Challange-main\Mobile_Challange-main
python .\main_no_mediapipe.py --video ".\face_400.mp4" --width 400 `
  --api "http://127.0.0.1:8081" --user-id admin --device-id xp-edge-01 `
  --push-interval 1.0 --threshold 0.35 --csv ".\scores_face.csv"


🟢 Você deve ver:

Janela do vídeo com retângulo no rosto;

Painel lateral com score / nível / sugestão;

No terminal da API: [POST] 200 {"ok": true} aparecendo.

💡 Sem webcam? Já usa face_400.mp4.
💾 Sem GUI? Gere vídeo processado com:

--out-video ".\output_face.mp4"

3️⃣ Rode o App Mobile (ControleBet)
cd "C:\caminho\para\Sprint-MobileDevelop"
npx expo start


📱 Configuração da API (duas opções)

Opção A – .env

Crie um arquivo .env na raiz do app:

EXPO_PUBLIC_API_BASE=http://127.0.0.1:8081


E no código:

export const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "http://127.0.0.1:8081";

Opção B – Fixo
export const API_BASE = "http://127.0.0.1:8081";

🔁 Polling do evento no app (exemplo)
// services/events.ts
export async function fetchLastEvent() {
  const res = await fetch(`${API_BASE}/events/last`);
  if (!res.ok) throw new Error("API error");
  return res.json();
}

// Exemplo em Home.tsx
useEffect(() => {
  let active = true;
  const tick = async () => {
    try {
      const data = await fetchLastEvent();
      if (active && data?.event) setStressInfo(data.event);
    } catch {}
  };
  tick();
  const id = setInterval(tick, 5000);
  return () => { active = false; clearInterval(id); };
}, []);


💡 Abra com Expo Go (QR), Android emulator (a) ou iOS simulator (i).

🔑 Credenciais de teste:
Usuário: admin
Senha: 12345

📡 Endpoints da API
POST /events

Recebe eventos do facial:

{
  "deviceId": "xp-edge-01",
  "userId": "admin",
  "score": 0.55,
  "level": "medio",
  "route": "Pausa guiada (respiracao 60s)",
  "ts": 1734636000
}

GET /events/last

Retorna o último evento:

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

🧮 Como o score e nível funcionam

Heurística leve baseada em:

🎞️ Jitter (variação quadro a quadro do ROI facial);

👄 Mouth_open (diferença de brilho entre metade superior e inferior da face).

Classificação:
Nível	Condição	Sugestão
leve	score < 0.35	Continuar tranquilo
médio	< 0.70	Pausa guiada (respiração 60s)
alto	≥ 0.70	Pausa guiada (respiração 60s)
🧪 Roteiro de Demo (5 min)
Etapa	Tempo	Ação
Arquitetura	30–45s	Mostre o diagrama Mermaid
API	30s	Rode o Uvicorn e abra /docs
Facial	1–2min	Mostre o vídeo com score + POST 200
Mobile	1–2min	Abra o app e mostre /events/last
Fechamento	30s	Enfatize o uso responsável + próximos passos

🧯 Troubleshootin
Problema	Solução
“Não abre vídeo”	Use check_video.py e reencode para H.264
ModuleNotFoundError: cv2	Instale opencv-python no venv ativo
CORS no mobile	Use o IP da máquina (ex.: http://192.168.15.123:8081)
Porta ocupada	Troque --port e ajuste API_BASE
Sem webcam	Use --video "face_400.mp4"

📦 Tecnologias
Mobile: React Native · Expo · TypeScript · AsyncStorage · React Navigation · ChartKit · SVG
API: FastAPI · Uvicorn
Facial: Python · OpenCV · NumPy · Requests

👥 Equipe
Nome	RM
Irana Pereira	RM98593
Lucas Vinicius	RM98480
Mariana Melo	RM98121
Mateus Iago	RM550270

📄 Licença

📚 Projeto acadêmico desenvolvido para FIAP (2025).
Uso educacional e não comercial.
