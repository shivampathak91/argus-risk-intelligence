# ARGUS - Autonomous Risk Intelligence & Early Warning Platform

<div align="center">

![ARGUS Logo](https://img.shields.io/badge/ARGUS-Risk%20Intelligence-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal?style=for-the-badge&logo=fastapi)

**AI-Powered Multi-Agent System for Infrastructure Risk Assessment & Disaster Response**

[Features](#features) • [Architecture](#architecture) • [Setup](#setup) • [Demo](#demo) • [Contributing](#contributing)

</div>

---

## 🎯 Overview

ARGUS is a production-grade AI platform that analyzes infrastructure incidents and natural disasters using a sophisticated multi-agent architecture. It combines computer vision, document analysis, historical pattern matching, and AI-driven simulation to provide actionable risk intelligence for emergency responders and infrastructure managers.

### What It Does

- **Analyzes uploaded images** of infrastructure damage (bridges, buildings, roads, power lines) to detect structural issues
- **Extracts data from documents** (PDFs, CSVs, reports) to understand incident context
- **Matches incidents to historical data** to identify patterns and lessons learned
- **Runs "what-if" simulations** to predict outcomes under different scenarios
- **Generates prioritized recommendations** with evidence-based rationale
- **Resolves conflicts between agents** through AI debate for authoritative decisions
- **Produces professional reports** suitable for emergency management and government use

### Key Differentiators

- **Explainable AI**: Every risk assessment and recommendation cites specific evidence from uploaded files or historical data
- **Multi-Agent Architecture**: 8 specialized AI agents work together, each with distinct expertise
- **Real-Time Progress**: WebSocket-based live updates show agent execution as it happens
- **Model Fallback**: Automatic switching between AI models when quota limits are reached
- **Local-First**: MCP (Model Context Protocol) servers ensure secure local data access

---

## ✨ Features

### Multi-Agent Pipeline

| Agent | Purpose | Output |
|-------|---------|--------|
| **Vision** | Analyzes images for damage indicators | Detected objects, severity estimates, visual evidence |
| **OCR** | Extracts structured data from documents | Key entities, measurements, timeline events |
| **Knowledge** | Matches to historical incidents | Similar events, patterns, lessons learned |
| **Risk** | Synthesizes evidence into risk score | Risk level (0-100), confidence, contributing factors |
| **Simulation** | Runs "what-if" scenario modeling | Predicted outcomes for different interventions |
| **Recommendation** | Generates prioritized actions | Actionable recommendations with evidence and priority |
| **Debate** | Resolves agent conflicts | Structured debate with final authoritative decision |
| **Commander** | Produces final authoritative output | Final risk level, mission summary, top recommendations |
| **Report** | Compiles professional documentation | Executive-grade risk intelligence report |

### Advanced Capabilities

- **AI Debate System**: When agents disagree (e.g., Risk says HIGH, Simulation says CRITICAL), the Commander orchestrates a structured debate to resolve conflicts
- **Automatic Model Fallback**: If primary AI models hit quota limits, automatically switches to backup models without interruption
- **Real-Time WebSocket Updates**: Live dashboard shows agent execution status, logs, and results as they're generated
- **Evidence-Based Reasoning**: Every conclusion cites specific evidence from vision analysis, documents, or historical data
- **Demo Mode**: 4 built-in scenarios (Bridge Failure, Urban Flood, Wildfire, Power Grid) for instant demonstration

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI** - High-performance async web framework
- **SQLAlchemy** - ORM with SQLite database
- **Pydantic** - Data validation and settings management
- **Google Gemini** - Primary AI model for vision and reasoning
- **Groq** - Fast LLM inference for text-based agents
- **WebSockets** - Real-time progress broadcasting
- **MCP (Model Context Protocol)** - Secure local data access

**Frontend:**
- **React 19** - Latest React with concurrent features
- **TanStack Start** - Full-stack React framework
- **Tailwind CSS v4** - Utility-first styling
- **Shadcn UI** - High-quality component library
- **React Flow** - Interactive workflow visualization
- **Leaflet** - Interactive maps for incident location
- **Recharts** - Data visualization

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard  │  │  Upload UI  │  │  Report View │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│                  Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Multi-Agent Orchestrator                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │ Vision   │ │   OCR    │ │Knowledge │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │  Risk    │ │Simulation│ │Recommend │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘            │  │
│  │  ┌──────────┐ ┌──────────┐                         │  │
│  │  │  Debate  │ │ Commander│                         │  │
│  │  └──────────┘ └──────────┘                         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              MCP Servers                              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │  File    │ │ Database │ │  Search  │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SQLite Database                         │  │
│  │  Users, Incidents, Workflows, Reports, Knowledge     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Google Gemini API key (get free at https://aistudio.google.com/app/apikey)
- Groq API key (get free at https://console.groq.com)
- (Optional) Tavily API key for web search (get free at https://tavily.com)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kaggle-capstone-project
   ```

2. **Create virtual environment**
   ```bash
   cd backend
   python -m venv .venv
   
   # Activate virtual environment
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here  # Optional
   SECRET_KEY=change-me-to-a-random-string
   ```

5. **Run the backend server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run the development server**
   ```bash
   npm run dev
   ```
   
   Frontend will be available at `http://localhost:3000`

### Quick Start

1. Open `http://localhost:3000` in your browser
2. Login with default credentials (or create an account)
3. Click "New Incident" to upload images/documents
4. Or use "Demo Mode" to try built-in scenarios instantly

---

## 🎮 Demo Mode

ARGUS includes 4 pre-configured demo scenarios that demonstrate the full AI pipeline without requiring file uploads:

1. **Bridge Failure** - Structural collapse with visible damage
2. **Urban Flood** - Flash flooding with infrastructure impact
3. **Wildfire** - Fire spread with wind conditions
4. **Power Grid Failure** - Electrical infrastructure failure

To use Demo Mode:
1. Navigate to the Mission Control Dashboard
2. Click "Launch Demo Scenario"
3. Select a scenario from the dropdown
4. Watch the multi-agent pipeline execute in real-time

---

## 📊 Use Cases

### Emergency Management
- Rapid assessment of infrastructure damage after natural disasters
- Prioritized response recommendations based on risk level
- Historical pattern matching to predict escalation

### Infrastructure Management
- Regular monitoring of bridges, roads, and power infrastructure
- Early detection of structural issues from visual inspection
- Maintenance prioritization based on AI risk assessment

### Government & Municipalities
- Professional-grade reports for decision-makers
- Evidence-based budget allocation for infrastructure repairs
- Documentation for insurance and regulatory compliance

---

## 🔒 Security

- **Local-First Data**: All data stored locally in SQLite database
- **MCP Protocol**: Secure local file and database access
- **API Key Management**: Environment variables for sensitive keys
- **Authentication**: JWT-based user authentication
- **Audit Logging**: Complete audit trail of all actions

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write tests for new features
- Update documentation as needed

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Google Gemini for AI model capabilities
- Groq for fast LLM inference
- The open-source community for the amazing tools and libraries used

---

## 📞 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review demo scenarios for examples

---

<div align="center">

**Built with ❤️ for safer infrastructure and better emergency response**

</div>
#   a r g u s - r i s k - i n t e l l i g e n c e  
 