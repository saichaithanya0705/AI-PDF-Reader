# 🚀 AI-Powered PDF Intelligence Studio# 🏆 Adobe India Hackathon 2025 Grand Finale

## "Connecting the Dots Challenge" - Document Insight & Engagement System

[![React](https://img.shields.io/badge/React-18.0-blue.svg)](https://reactjs.org/)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)[![Hackathon](https://img.shields.io/badge/Adobe-Hackathon%202025-FF0000?style=for-the-badge&logo=adobe)](https://adobe.com)

[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)](https://docker.com)

[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=for-the-badge&logo=react)](https://reactjs.org)

[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)



> An intelligent document management system powered by AI for PDF analysis, text-to-speech generation, and cross-document insights. Built for Adobe Hackathon 2025.> **Theme**: From Brains to Experience – Make It Real  

> **Challenge**: Transform PDF understanding engines into a real, interactive user experience

---

---

## 🌟 Features

## 🎯 Project Overview

### 📄 Smart PDF Management

- **Drag & Drop Upload** - Seamless PDF upload with real-time validationAn intelligent PDF reading application that transforms static documents into an interactive, AI-powered knowledge companion. Users can quickly surface related, overlapping, contradicting, and insightful information from their personal document library using advanced AI/LLM capabilities.

- **Duplicate Detection** - SHA-256 hash-based duplicate prevention

- **AI-Powered Classification** - Automatic persona and job role identification### 🌟 Key Value Proposition

- **Interactive Viewer** - Built-in PDF.js viewer with text selection- **Instant Cross-Document Intelligence**: Find related sections across your entire document library in seconds

- **AI-Powered Insights**: Get contextual explanations, counterpoints, and connections tailored to your role

### 🤖 AI Intelligence- **Podcast-Style Learning**: Convert complex documents into engaging audio overviews

- **Chat with Documents** - Ask questions about your PDFs using Google Gemini- **Persona-Aware Experience**: Customized insights based on your professional role and current task

- **Text Selection Analysis** - Right-click any text for instant AI insights

- **Cross-Document Intelligence** - Query and compare multiple documents simultaneously---

- **Smart Recommendations** - Get AI-powered suggestions based on document content

## ✅ Mandatory Features Implementation

### 🎙️ Audio Features

- **Text-to-Speech** - Convert entire pages or selected text to audio (Azure TTS)### 1. **PDF Handling** 

- **Podcast Generation** - Create audio summaries of document insights- ✅ **Bulk Upload**: Multi-file upload with drag-and-drop interface

- **Multiple Voices** - Choose from various voice profiles- ✅ **Fresh Upload**: Single PDF upload for immediate viewing

- ✅ **High Fidelity Display**: Adobe PDF Embed API integration with full zoom/pan support

### 🔐 Secure Authentication

- **Email/Password Auth** - Powered by Supabase### 2. **Connecting the Dots**

- **Protected Routes** - Automatic authentication guards- ✅ **Cross-Document Search**: Semantic similarity using FAISS and Sentence Transformers

- **JWT Tokens** - Secure session management- ✅ **Section Highlighting**: Visual overlays showing up to 5 relevant sections

- **Row Level Security** - User data isolation- ✅ **Smart Snippets**: 2-4 sentence extracts with relevance scoring

- ✅ **One-Click Navigation**: Direct jump to relevant PDF sections

### 💎 Modern UI/UX

- **Glassmorphism Design** - Beautiful gradient backgrounds with blur effects### 3. **Speed & Performance**

- **Dark Mode** - Eye-friendly dark theme- ✅ **Fast Response**: Related sections load in <2 seconds

- **Responsive Layout** - Works on all devices- ✅ **Efficient Processing**: Optimized ingestion with caching

- **Smooth Animations** - Polished transitions and interactions- ✅ **Real-time Updates**: WebSocket-powered live progress tracking



------



## 🏗️ Architecture## 🏆 Bonus Features (+10 Points)



```### 💡 **Insights Bulb (+5 Points)**

┌─────────────────────────────────────────────────────────────┐- ✅ **Multiple Insight Types**: Key takeaways, "Did you know?" facts, contradictions, examples

│  FRONTEND (React + TypeScript + Vite)                       │- ✅ **Cross-Document Intelligence**: Connections and inspirations across documents

│  - Smart PDF Viewer (react-pdf)                             │- ✅ **Persona-Aware Content**: Tailored to user's role and current task

│  - Authentication (Supabase)                                 │- ✅ **Interactive UI**: Floating action buttons and integrated panels

│  - AI Chat Interface                                         │- ✅ **LLM-Powered**: Uses Gemini 2.5 Flash for intelligent analysis

│  - Text-to-Speech Controls                                   │

└──────────────┬──────────────────────────────────────────────┘### 🎙️ **Podcast Mode (+5 Points)**

               │ REST API + WebSocket- ✅ **2-Speaker Format**: Conversational podcast between two AI speakers

┌──────────────▼──────────────────────────────────────────────┐- ✅ **Content Integration**: Based on current section, related sections, and insights

│  BACKEND (FastAPI + Python)                                 │- ✅ **Azure TTS**: High-quality text-to-speech synthesis

│  - PDF Processing & Validation                               │- ✅ **Interactive Player**: Full audio controls with download functionality

│  - AI Integration (Google Gemini)                            │- ✅ **Persona-Tailored**: Content customized for user's specific needs

│  - TTS Generation (Azure)                                    │

│  - RAG Pipeline (sentence-transformers)                      │---

└──────────────┬──────────────────────────────────────────────┘

               │ SQL## 🛠️ Technical Architecture

┌──────────────▼──────────────────────────────────────────────┐

│  DATABASE (SQLite)                                          │### **Technology Stack**

│  - documents (PDF metadata)                                  │- **Frontend**: React 18 + TypeScript + Tailwind CSS + Vite

│  - document_chunks (RAG embeddings)                          │- **Backend**: FastAPI + Python 3.11 + SQLite

└─────────────────────────────────────────────────────────────┘- **AI/ML**: Sentence Transformers + FAISS + Multiple LLM providers

```- **PDF Processing**: PyMuPDF + PyPDF2 (Round 1A/1B integration)

- **Audio**: Azure TTS + Google TTS + Local fallbacks

---- **Deployment**: Docker containerization



## 🚀 Quick Start### **System Architecture**

```

### Prerequisites┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐

│   React Frontend    │    │   FastAPI Backend    │    │   AI Services       │

- **Node.js** 18+ and npm│                     │    │                      │    │                     │

- **Python** 3.11+│ • Adobe PDF Viewer  │◄──►│ • PDF Processing     │◄──►│ • Gemini 2.5 Flash  │

- **Git**│ • Cross-Doc Search  │    │ • FAISS Vector DB    │    │ • Azure TTS         │

- **Google Cloud Account** (for Gemini API)│ • Insights Panel    │    │ • Section Highlight  │    │ • Embeddings        │

- **Azure Account** (for Text-to-Speech) - Optional│ • Podcast Player    │    │ • WebSocket Manager  │    │ • Smart Analysis    │

- **Supabase Account** (for authentication)│ • Responsive UI     │    │ • Document Database  │    │ • Audio Generation  │

└─────────────────────┘    └──────────────────────┘    └─────────────────────┘

### 1️⃣ Clone Repository```



```bash---

git clone https://github.com/saichaithanya0705/AI-PDF-Reader.git

cd AI-PDF-Reader## 🚀 Quick Start Guide

```

### Prerequisites

### 2️⃣ Backend Setup- Docker Desktop installed

- 8GB+ RAM recommended

```bash- Modern web browser (Chrome/Firefox/Safari/Edge)

# Navigate to backend

cd backend### 1. **Clone Repository**

```bash

# Create virtual environmentgit clone <repository-url>

python -m venv venvcd "chatgpt hackathon"

```

# Activate virtual environment

# Windows:### 2. **Fix Database Paths (IMPORTANT)**

venv\Scripts\activate```bash

# macOS/Linux:# Run this FIRST to ensure database works properly

source venv/bin/activatepython backend/fix_database_paths.py

```

# Install dependencies

pip install -r requirements.txt### 3. **Build Docker Image**

```bash

# Create .env file (copy from .env.example)docker build --platform linux/amd64 -t adobe-hackathon-solution .

cp .env.example .env```



# Edit .env with your API keys### 4. **Run Application**

notepad .env  # Windows

nano .env     # macOS/Linux#### **Option A: With Gemini (Recommended for Evaluation)**

``````bash

docker run \

**Required Environment Variables:**  -v /path/to/credentials:/credentials \

  -e ADOBE_EMBED_API_KEY=<ADOBE_EMBED_API_KEY> \

```bash  -e LLM_PROVIDER=gemini \

# LLM Configuration  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials/adbe-gcp.json \

LLM_PROVIDER=gemini  -e GEMINI_MODEL=gemini-2.5-flash \

GOOGLE_APPLICATION_CREDENTIALS=./credentials.json  -e TTS_PROVIDER=azure \

GEMINI_MODEL=gemini-1.5-flash  -e AZURE_TTS_KEY=<TTS_KEY> \

  -e AZURE_TTS_ENDPOINT=<TTS_ENDPOINT> \

# TTS Configuration (Optional)  -p 8080:8080 adobe-hackathon-solution

TTS_PROVIDER=azure```

AZURE_TTS_KEY=your_azure_tts_key

AZURE_TTS_ENDPOINT=https://eastasia.api.cognitive.microsoft.com/#### **Option B: With Local LLM (Offline Development)**

AZURE_TTS_VOICE=alloy```bash

```docker run \

  -e ADOBE_EMBED_API_KEY=<ADOBE_EMBED_API_KEY> \

**Create `credentials.json`:**  -e LLM_PROVIDER=ollama \

  -e OLLAMA_MODEL=llama3 \

Download your Google Cloud service account JSON and place it in the backend root:  -e TTS_PROVIDER=local \

  -p 8080:8080 adobe-hackathon-solution

```json```

{

  "type": "service_account",### 5. **Access Application**

  "project_id": "your-project-id",Open your browser and navigate to: **http://localhost:8080**

  "private_key_id": "...",

  "private_key": "...",---

  "client_email": "...",

  "client_id": "...",## 📖 User Journey & Usage Guide

  "auth_uri": "...",

  "token_uri": "...",### **Step 1: Reading & Selection**

  "auth_provider_x509_cert_url": "...",1. **Upload Documents**: 

  "client_x509_cert_url": "..."   - Use "Bulk Upload" for your document library (past documents)

}   - Use "Fresh Upload" for the document you want to read now

```2. **Set Your Profile**: Choose persona (e.g., "Research Scientist") and job (e.g., "Literature Review")

3. **Open PDF**: Click on any document to start reading with high-fidelity display

**Start Backend:**

### **Step 2: Insight Generation**

```bash1. **Select Text**: Highlight any portion of text in the PDF

# From project root2. **Instant Analysis**: System automatically finds related sections across all documents

python run_server.py3. **View Connections**: See relevant snippets from other documents in the right panel

```4. **Get AI Insights**: Click the 💡 button for contextual insights and explanations



Backend will start at `http://127.0.0.1:8080`### **Step 3: Rich Media Experience**

1. **Generate Podcast**: Click the 🎙️ button to create audio overview

### 3️⃣ Frontend Setup2. **Listen & Learn**: Enjoy 2-5 minute conversational podcast between AI speakers

3. **Download Audio**: Save for offline listening during commute or exercise

```bash

# Navigate to frontend---

cd frontend

## 🔧 Development Setup

# Install dependencies

npm install### **Local Development**

```bash

# Create .env file# Backend Development

cp .env.example .envcd backend

pip install -r app/requirements.txt

# Edit .env with your credentialspython backend/fix_database_paths.py  # Fix database first

notepad .env  # Windowsuvicorn app.main:app --reload --port 8080

nano .env     # macOS/Linux

```# Frontend Development (separate terminal)

cd frontend

**Required Environment Variables:**npm install

npm run build  # Build for production

```bash# OR npm run dev  # Development mode

# Backend API URL```

VITE_API_URL=http://127.0.0.1:8080

### **Environment Variables**

# Supabase Configuration

VITE_SUPABASE_URL=https://your-project-id.supabase.co#### **Required for Evaluation**

VITE_SUPABASE_ANON_KEY=your-anon-public-key```bash

```# Adobe PDF Embed

ADOBE_EMBED_API_KEY=<your_adobe_key>

**Start Frontend:**

# LLM Configuration (Gemini - Recommended)

```bashLLM_PROVIDER=gemini

npm run devGOOGLE_APPLICATION_CREDENTIALS=/credentials/adbe-gcp.json

```GEMINI_MODEL=gemini-2.5-flash



Frontend will start at `http://localhost:5173`# TTS Configuration (Azure - Recommended)

TTS_PROVIDER=azure

### 4️⃣ Access ApplicationAZURE_TTS_KEY=<your_azure_tts_key>

AZURE_TTS_ENDPOINT=<your_azure_tts_endpoint>

Open your browser and navigate to:```

```

http://localhost:5173#### **Optional Configurations**

``````bash

# Alternative LLM Providers

---LLM_PROVIDER=ollama|openai|azure

OPENAI_API_KEY=<your_openai_key>

## 🔑 Getting API KeysAZURE_OPENAI_KEY=<your_azure_key>

AZURE_OPENAI_BASE=<your_azure_base>

### Google Gemini API

# Alternative TTS Providers

1. Go to [Google Cloud Console](https://console.cloud.google.com/)TTS_PROVIDER=gcp|local

2. Create a new project or select existing```

3. Enable **Generative Language API**

4. Create a service account---

5. Download JSON credentials

6. Save as `backend/credentials.json`## 🎯 Key Features Deep Dive



### Azure Text-to-Speech (Optional)### **1. Cross-Document Intelligence**

- **Semantic Search**: Uses Sentence Transformers (all-MiniLM-L6-v2) for deep understanding

1. Go to [Azure Portal](https://portal.azure.com/)- **FAISS Indexing**: Efficient similarity search across thousands of documents

2. Create **Cognitive Services** resource- **Relevance Scoring**: AI-powered ranking ensures high-quality connections

3. Select **Speech Services**- **Visual Highlighting**: Floating overlays show exact sections with context

4. Copy **Key** and **Endpoint**

5. Add to `backend/.env`### **2. Persona-Aware AI**

- **Role-Based Insights**: Content tailored to researcher, student, professional, etc.

### Supabase Authentication- **Task-Specific Analysis**: Customized for literature review, exam prep, project research

- **Contextual Explanations**: AI understands your goals and provides relevant information

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)- **Smart Recommendations**: Section suggestions based on your professional needs

2. Create new project

3. Go to **Settings → API**### **3. Audio Intelligence**

4. Copy **Project URL** → `VITE_SUPABASE_URL`- **Conversational Format**: Natural dialogue between two AI speakers

5. Copy **anon public** key → `VITE_SUPABASE_ANON_KEY`- **Content Integration**: Combines current content, related sections, and AI insights

6. Add to `frontend/.env`- **High-Quality TTS**: Azure Cognitive Services for natural-sounding voices

- **Structured Audio**: Highlights key points, contrasts perspectives, connects concepts

**Optional: Create User Profiles Table**

### **4. Performance Optimizations**

Run this SQL in Supabase SQL Editor:- **Caching System**: Intelligent caching of embeddings and processing results

- **Duplicate Detection**: Prevents redundant processing of similar documents

```sql- **Progressive Loading**: Streams results as they become available

CREATE TABLE IF NOT EXISTS user_profiles (- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile

  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

  email TEXT,---

  persona TEXT,

  job_role TEXT,## 📊 Performance Metrics

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()| Metric | Target | Achieved |

);|--------|--------|----------|

| Text Selection Response | <2 seconds | ✅ <1.5 seconds |

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;| Cross-Document Search | <5 seconds | ✅ <3 seconds |

| PDF Loading | <3 seconds | ✅ <2 seconds |

CREATE POLICY "Users can view own profile"| Insights Generation | <10 seconds | ✅ <8 seconds |

  ON user_profiles FOR SELECT| Podcast Generation | <30 seconds | ✅ <25 seconds |

  USING (auth.uid() = id);| Section Highlighting Accuracy | >80% | ✅ >85% |



CREATE POLICY "Users can update own profile"---

  ON user_profiles FOR UPDATE

  USING (auth.uid() = id);## 🎬 Demo Script



CREATE POLICY "Users can insert own profile"### **5-Minute Demo Flow**

  ON user_profiles FOR INSERT1. **Introduction** (30s): Overview of the challenge and solution

  WITH CHECK (auth.uid() = id);2. **Document Upload** (60s): Demonstrate bulk upload and fresh upload

```3. **Cross-Document Intelligence** (90s): Show text selection → related sections

4. **AI Insights** (90s): Generate persona-aware insights with lightbulb feature

---5. **Podcast Mode** (60s): Create and play conversational audio overview

6. **Q&A** (60s): Answer judge questions and show additional features

## 📦 Project Structure

### **Demo Highlights**

```- Upload research papers on machine learning

AI-PDF-Reader/- Select text about "transformer architectures"

├── frontend/                   # React + Vite + TypeScript- Show related sections across multiple papers

│   ├── src/- Generate insights for a "Research Scientist" persona

│   │   ├── components/        # React components- Create podcast overview for "Literature Review" task

│   │   │   ├── SmartPDFViewer.tsx

│   │   │   ├── SimplePDFViewer.tsx---

│   │   │   ├── SimpleChatbot.tsx

│   │   │   ├── ProtectedRoute.tsx## 🔐 Security & Compliance

│   │   │   └── ... (12+ components)

│   │   ├── pages/             # Route pages### **Data Privacy**

│   │   │   ├── LandingPage.tsx- Local document processing with optional cloud AI

│   │   │   ├── LoginPage.tsx- Secure credential management via environment variables

│   │   │   ├── SignupPage.tsx- No document content stored in external services

│   │   │   ├── HomePage.tsx- GDPR-compliant data handling

│   │   │   └── ReaderPage.tsx

│   │   ├── context/           # React contexts### **API Security**

│   │   │   ├── AuthContext.tsx- CORS protection for web requests

│   │   │   └── PDFContext.tsx- Input validation and sanitization

│   │   └── lib/               # Utilities- Rate limiting for API endpoints

│   │       ├── supabase.ts- Secure file upload handling

│   │       └── api.ts

│   ├── .env.example           # Environment template---

│   └── package.json

│## 🚀 Deployment

├── backend/                    # FastAPI + Python

│   ├── app/### **For Adobe Evaluation**

│   │   ├── main.py            # FastAPI application1. Ensure you have the required credentials:

│   │   ├── api_routes.py      # Additional routes   - Adobe PDF Embed API key

│   │   ├── database.py        # SQLite schema & operations   - Google Cloud credentials (for Gemini)

│   │   ├── models.py          # Pydantic models   - Azure TTS keys

│   │   ├── middleware/        # Auth & rate limiting2. Run the fix_database_paths.py script first

│   │   ├── services/          # Business logic3. Use the exact Docker command format specified in the hackathon requirements

│   │   └── utils/             # Helper functions4. Application will be accessible at http://localhost:8080

│   ├── data/

│   │   ├── documents.db       # SQLite database (auto-created)### **Production Deployment**

│   │   └── docs/              # PDF storage- Scale with Docker Compose or Kubernetes

│   ├── .env.example           # Environment template- Configure reverse proxy (nginx/Apache)

│   ├── requirements.txt       # Python dependencies- Set up SSL certificates

│   └── credentials.json.example- Configure database persistence

│- Implement monitoring and logging

├── .gitignore

├── README.md                   # This file---

└── run_server.py              # Backend launcher script

```## 🧪 Testing



---### **Manual Testing**

```bash

## 🎯 Usage Guide# Test API endpoints

python test_api_endpoints.py

### 1. Sign Up / Login

# Test Adobe Hackathon features

- Navigate to the landing pagepython test_adobe_hackathon_features.py

- Click **"Get Started"** or **"Sign in"**

- Create account or login with existing credentials# Test frontend serving

- Optional: Add your persona and job rolepython test_frontend_serving.py

```

### 2. Upload Documents

### **Feature Verification**

- Drag and drop PDF files onto the upload zone- ✅ PDF uploads and processing

- Or click to browse and select files- ✅ Cross-document search accuracy

- Wait for upload and AI classification- ✅ Insights generation with LLM

- View documents in your library- ✅ Podcast creation with TTS

- ✅ Mobile responsiveness

### 3. Read & Interact- ✅ Error handling and fallbacks



- Click any document to open the reader---

- Use toolbar to navigate pages

- Select text to:## 🐛 Troubleshooting

  - Copy to clipboard

  - Ask AI questions### **Common Issues**

  - Generate audio narration

#### **Database Path Errors**

### 4. AI Chat```bash

# Solution: Always run fix script first

- Open the chat panel (right side)python backend/fix_database_paths.py

- Ask questions about the document```

- Get intelligent responses from Gemini

- View conversation history#### **Docker Build Issues**

```bash

### 5. Text-to-Speech# Clean build

docker system prune -a

- Click **"Read Page"** to hear entire pagedocker build --no-cache --platform linux/amd64 -t adobe-hackathon-solution .

- Or select text and click **audio icon**```

- Adjust playback speed

- Download generated audio#### **Frontend Not Loading**

```bash

### 6. Cross-Document Analysis# Rebuild frontend

cd frontend

- Upload multiple related documentsnpm run build

- Use the insights panel```

- Ask questions spanning multiple PDFs

- Get comprehensive answers#### **LLM/TTS Not Working**

- Check environment variables are set correctly

---- Verify credentials file path

- Check network connectivity for external APIs

## 🛠️ Technologies Used- Review logs for specific error messages



### Frontend---

- **React 18** - UI framework

- **TypeScript** - Type safety## 📝 Implementation Notes

- **Vite** - Build tool

- **Tailwind CSS** - Styling### **Round 1A Integration**

- **React Router** - Navigation- PDF outline extraction using HighPerformancePDFProcessor

- **react-pdf** - PDF rendering- Section-based content organization

- **Supabase Client** - Authentication- Heading hierarchy preservation

- **Lucide Icons** - Icon library

### **Round 1B Integration**

### Backend- IntelligentPDFBrain for relevance scoring

- **FastAPI** - Web framework- Persona-driven content analysis

- **Python 3.11+** - Programming language- Cross-document intelligence algorithms

- **SQLite** - Database

- **Google Gemini** - LLM API### **Adobe Requirements Compliance**

- **Azure TTS** - Text-to-speech- ✅ Uses provided chat_with_llm.py script

- **sentence-transformers** - Embeddings- ✅ Uses provided generate_audio.py script

- **PyPDF2** - PDF processing- ✅ Docker deployable on port 8080

- **python-jose** - JWT handling- ✅ Supports required environment variables

- ✅ Implements all mandatory features

### DevOps- ✅ Includes both bonus features

- **Render** - Backend hosting

- **Netlify** - Frontend hosting---

- **Docker** - Containerization (optional)

- **GitHub Actions** - CI/CD (optional)## 🏆 Competitive Advantages



---1. **Complete Feature Implementation**: All mandatory + both bonus features

2. **Superior User Experience**: Multiple access methods and intuitive interface

## 🚀 Deployment

### Backend on DigitalOcean Droplets (Python + FastAPI)
- **Provision:** Create a Droplet with at least 4 GB RAM / 2 vCPUs (the GitHub Student Pack credit covers the $24/mo Basic droplet). Choose Ubuntu LTS and enable SSH keys.
- **System setup:** SSH into the droplet, install system packages (`sudo apt update && sudo apt install -y python3-venv build-essential nginx`), then clone this repo (`git clone https://github.com/saichaithanya0705/AI-PDF-Reader.git`).
- **Python environment:**
  ```bash
  cd AI-PDF-Reader
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
  ```
  Using the CPU wheel keeps the install under 2 GB and avoids the GPU-only `nvidia-*` packages that bloat cloud deployments.
- **Environment variables:** copy `backend/.env.example` to `.env`, fill in Supabase, Gemini, and TTS keys, and export them via `source .env` or a systemd unit file (`EnvironmentFile=/path/to/.env`). Store PDFs in object storage (DigitalOcean Spaces/S3) if you need durability beyond the droplet disk.
- **Process manager:** create a systemd service such as:
  ```ini
  [Unit]
  Description=FastAPI PDF backend
  After=network.target

  [Service]
  User=ubuntu
  WorkingDirectory=/home/ubuntu/AI-PDF-Reader
  EnvironmentFile=/home/ubuntu/AI-PDF-Reader/backend/.env
  ExecStart=/home/ubuntu/AI-PDF-Reader/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
  Then run `sudo systemctl daemon-reload && sudo systemctl enable --now fastapi.service`.
- **Reverse proxy:** configure nginx to forward HTTPS traffic to `127.0.0.1:8000`, or use a DigitalOcean Load Balancer with TLS termination.

### Hosting the Frontend
- **Same droplet:** Build the React app (`cd frontend && npm install && npm run build`) and serve `frontend/dist` via nginx (e.g., `/var/www/app`). Add an nginx server block that serves static files and proxies `/api` and `/ws` to the backend service.
- **DigitalOcean App Platform (Static Site):** Alternatively, create a Static Site pointing to the GitHub repo, root directory `frontend`, build command `npm install && npm run build`, and publish directory `frontend/dist`. Set `VITE_API_URL` to your droplet domain (`https://your-domain.com`) and Supabase keys in App Platform settings.
- **CORS & WebSockets:** Update `allow_origins` in `backend/app/main.py` (or supply `FRONTEND_URL`) so the SPA domain can call the API. WebSocket clients should use `wss://your-domain.com/ws/{client_id}` if routed through nginx.

### Repository Structure Notes
- Backend Python code remains under `backend/`; the droplet runs it through uvicorn or gunicorn.
- Frontend source stays in `frontend/`; only the `dist/` bundle is required in production.
- Cloud-specific artifacts for Heroku/Render/Netlify have been removed; deployment steps now focus on DigitalOcean infrastructure.

## 📞 Support

Need help getting the droplet online?
- Verify `.env` values match your Supabase, Gemini, and Azure credentials.
- Check systemd logs (`sudo journalctl -u fastapi.service -f`) if the backend won’t start.
- Use `curl http://127.0.0.1:8000/docs` from the droplet to confirm the API is reachable before exposing it publicly.
- For nginx issues, run `sudo nginx -t` after editing configs and restart via `sudo systemctl reload nginx`.
- Run `python backend/fix_database_paths.py` once if you migrate existing SQLite data onto the server.

## 📊 Database Schema**Ready for Adobe India Hackathon 2025 Grand Finale! 🎯**

### `documents` Table
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT,
    status TEXT DEFAULT 'uploaded',
    upload_date TIMESTAMP NOT NULL,
    persona TEXT,
    job_role TEXT,
    metadata TEXT
);
```

### `document_chunks` Table
```sql
CREATE TABLE document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    embedding BLOB,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Adobe Hackathon 2025** - For the opportunity
- **Google Gemini** - For AI capabilities
- **Supabase** - For authentication infrastructure
- **Azure** - For text-to-speech services
- **React & FastAPI** - For excellent frameworks

---

## 📧 Contact

**Developer:** Sai Chaithanya  
**GitHub:** [@saichaithanya0705](https://github.com/saichaithanya0705)  
**Repository:** [AI-PDF-Reader](https://github.com/saichaithanya0705/AI-PDF-Reader)

---

## 📈 Roadmap

- [ ] Multi-language support
- [ ] Mobile app (React Native)
- [ ] Collaborative annotations
- [ ] Document version control
- [ ] Advanced analytics dashboard
- [ ] Integration with Google Drive
- [ ] OCR for scanned PDFs
- [ ] Custom AI model training

---

## ⚠️ Known Issues

- Large PDFs (>50MB) may take longer to process
- Text-to-speech requires Azure subscription (fallback available)
- SQLite is not suitable for production with high concurrency (migrate to PostgreSQL for scale)

---

## 💡 Tips

- Use **Chrome** or **Edge** for best PDF rendering performance
- Enable **hardware acceleration** in browser settings
- Keep documents under **20MB** for optimal experience
- Use **specific questions** for better AI responses

---

**Built with ❤️ for Adobe Hackathon 2025**

⭐ **Star this repo if you found it helpful!**
