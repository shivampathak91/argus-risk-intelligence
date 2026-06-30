# ARGUS - Autonomous Risk Intelligence & Early Warning Platform

<div align="center">

![ARGUS Logo](https://img.shields.io/badge/ARGUS-Risk%20Intelligence-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal?style=for-the-badge&logo=fastapi)

**AI-Powered Multi-Agent System for Infrastructure Risk Assessment & Disaster Response**

[Features](#features) • [Architecture](#architecture) • [Setup](#setup) • [Demo Mode](#demo-mode) • [Contributing](#contributing)

</div>

---

## 🎯 Overview

### The Problem

Infrastructure risk assessment and disaster response face critical challenges:

- **Slow Manual Analysis**: Emergency responders and infrastructure managers must manually inspect damage, review documents, and assess risks - a process that can take hours or days when every minute counts
- **Lack of Historical Context**: Decisions are made without learning from past incidents, leading to repeated mistakes and missed opportunities
- **Fragmented Data Sources**: Information is scattered across images, PDFs, databases, and web sources with no unified analysis
- **Subjective Risk Assessment**: Risk levels are often estimated based on intuition rather than evidence-based analysis
- **No What-If Modeling**: Decision-makers cannot predict outcomes of different intervention strategies before acting

These challenges result in delayed responses, inefficient resource allocation, and preventable loss of life and infrastructure.

### The Solution

ARGUS (Autonomous Risk Intelligence & Early Warning Platform) is a production-grade AI platform that automates infrastructure risk assessment through a sophisticated multi-agent architecture. It combines computer vision, document analysis, historical pattern matching, and AI-driven simulation to provide actionable risk intelligence in minutes instead of hours.

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

| **Agent**      | **Purpose**                                             | **Output**                                                         |
| -------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| Vision         | Analyze images for damage indicators                    | Detected objects, severity estimates, visual evidence              |
| OCR            | Extract structured information from documents           | Key entities, measurements, timeline events                        |
| Knowledge      | Match findings with historical incidents                | Similar events, patterns, lessons learned                          |
| Risk           | Synthesize evidence into a quantitative risk assessment | Risk score (0–100), confidence, contributing factors               |
| Simulation     | Evaluate intervention scenarios using what-if analysis  | Predicted outcomes for different interventions                     |
| Recommendation | Generate prioritized evidence-based actions             | Actionable recommendations with priorities and supporting evidence |
| Debate         | Resolve disagreements among agent outputs               | Structured debate and consensus decision                           |
| Commander      | Consolidate all agent results into the final decision   | Final risk level, mission summary, top recommendations             |
| Report         | Generate professional documentation                     | Executive-grade risk intelligence report                           |

### Advanced Capabilities

- **AI Debate System**: When agents disagree (e.g., Risk says HIGH, Simulation says CRITICAL), the Commander orchestrates a structured debate to resolve conflicts
- **Automatic Model Fallback**: If primary AI models hit quota limits, automatically switches to backup models without interruption
- **Real-Time WebSocket Updates**: Live dashboard shows agent execution status, logs, and results as they're generated
- **Evidence-Based Reasoning**: Every conclusion cites specific evidence from vision analysis, documents, or historical data
- **Demo Mode**: 4 built-in scenarios (Bridge Failure, Urban Flood, Wildfire, Power Grid) for instant demonstration

---

![Login Page](Disaster%20Images/1.png)
*Figure: Login Page*

![Dashboard](Disaster%20Images/2.png)
*Figure: Dashboard*

![Adding Incidents](Disaster%20Images/3.png)
*Figure: Adding Incidents*

![Agent Pipeline](Disaster%20Images/4.png)
*Figure: Agent Pipeline*

![Risk Assessment](Disaster%20Images/5.png)
*Figure: Risk Assessment*

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI** - High-performance async web framework
- **SQLAlchemy** - ORM with SQLite database
- **Pydantic** - Data validation and settings management
- **Google Gemini** - Primary AI model for vision and reasoning
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

---

## 🚀 Project Journey

### Development Process

ARGUS was developed over 10 days as a capstone project demonstrating advanced AI agent systems and secure local data access protocols. The project evolved through several iterations:

**Phase 1: Foundation (Days 1-2)**
- Set up FastAPI backend with SQLAlchemy ORM
- Implemented JWT authentication and role-based access control
- Created database models for incidents, workflows, and reports
- Built React frontend with TanStack Router

**Phase 2: Multi-Agent System (Days 3-4)**
- Implemented Vision Agent using Google Gemini Vision API
- Built OCR Agent for document text extraction
- Created Knowledge Agent with historical pattern matching
- Developed Risk Agent for quantitative risk scoring
- Implemented orchestrator for parallel and sequential agent execution

**Phase 3: Advanced Features (Days 5-6)**
- Added Simulation Agent for what-if scenario modeling
- Built Recommendation Agent with evidence-based actions
- Implemented Debate Agent for conflict resolution
- Created Commander Agent for final decision synthesis
- Added Report Agent for professional documentation

**Phase 4: MCP Integration (Days 7-8)**
- Implemented Filesystem MCP for secure file access
- Built PDF MCP for document text extraction
- Created Search MCP for web search capabilities
- Developed SQLite MCP for database queries
- Added input validation and path sanitization

**Phase 5: Polish & Testing (Days 9-10)**
- Implemented WebSocket real-time progress updates
- Added automatic model fallback on quota limits
- Created demo scenarios for instant demonstration
- Added audit logging for security compliance
- Fixed bugs and optimized performance

### Key Challenges & Solutions

**Challenge 1: Agent Coordination**
- **Problem**: Agents needed to run in parallel (vision, OCR, knowledge) but sequentially (risk, simulation, recommendation)
- **Solution**: Implemented orchestrator with two-phase execution pattern using asyncio.gather for parallel tasks

**Challenge 2: Knowledge Base Gaps**
- **Problem**: Knowledge agent had no landslide historical data, causing it to return wildfire information
- **Solution**: Added comprehensive historical records for all incident types (landslides, wildfires, floods, etc.) to knowledge base

**Challenge 3: Variable Scoping in Orchestrator**
- **Problem**: When agents failed, subsequent agents couldn't access data due to Python scoping issues
- **Solution**: Initialized all data dictionaries before parallel execution to prevent UnboundLocalError

**Challenge 4: API Quota Limits**
- **Problem**: AI models hit rate limits, causing pipeline failures
- **Solution**: Implemented automatic fallback to backup models with graceful degradation

**Challenge 5: MCP Security**
- **Problem**: File access could lead to directory traversal attacks
- **Solution**: Added path validation, input sanitization, and restricted access to upload directory only

### Lessons Learned

1. **Multi-Agent Systems Require Careful Orchestration**: Parallel execution improves performance but requires careful error handling and state management

2. **Historical Context is Critical**: AI agents need domain-specific historical data to provide accurate assessments

3. **Security Must Be Built In**: MCP servers require input validation at every entry point to prevent attacks

4. **Real-Time Feedback Improves UX**: WebSocket updates make long-running AI processes feel responsive

5. **Fallback Strategies Essential**: AI APIs have limits; systems must gracefully handle failures

6. **Evidence-Based AI Builds Trust**: Every recommendation should cite specific evidence from analysis

### Future Enhancements

- Add more incident types (earthquakes, hurricanes, chemical spills)
- Implement agent fine-tuning on domain-specific data
- Add mobile app for field responders
- Integrate with real-time sensor data streams
- Add collaborative features for multi-user incidents

---

## 🎓 Course Key Concepts Demonstrated

This project demonstrates the following key concepts from the course:

### 1. Multi-Agent System (Code)
**Location:** `backend/app/agents/` and [backend/app/workflow/orchestrator.py]

ARGUS implements a sophisticated multi-agent architecture with 8 specialized agents:
- **Vision Agent**: Analyzes images using Gemini Vision API
- **OCR Agent**: Extracts structured data from documents
- **Knowledge Agent**: Matches incidents to historical patterns
- **Risk Agent**: Synthesizes evidence into risk scores
- **Simulation Agent**: Runs "what-if" scenario modeling
- **Recommendation Agent**: Generates prioritized actions
- **Debate Agent**: Resolves conflicts between agents
- **Commander Agent**: Produces final authoritative decisions
- **Report Agent**: Compiles professional documentation

The orchestrator coordinates agents in parallel (Phase 1) and sequential (Phase 2) execution patterns, broadcasting real-time progress via WebSockets.

### 2. MCP Server (Code)
**Location:** `backend/app/mcp/`

ARGUS implements 4 MCP servers providing secure local data access:

**Filesystem MCP** ([filesystem_mcp.py]
- `read_file` - Read uploaded files
- `write_file` - Write analysis results
- `list_files` - List available files
- `delete_file` - Remove files

**PDF MCP** (`pdf_mcp.py`):
- `extract_text` - Extract text from PDFs
- `extract_tables` - Extract tabular data
- `get_page_count` - Get PDF metadata

**Search MCP** (`search_mcp.py`):
- `web_search` - Web search via DuckDuckGo/Tavily
- `search_news` - Search recent news
- `search_images` - Search for related images

**SQLite MCP** (`sqlite_mcp.py`):
- `query_database` - Execute SQL queries
- `get_schema` - Get database schema
- `list_tables` - List available tables

Each MCP server validates paths, sanitizes inputs, and provides secure tool access to agents.

### 3. Security Features (Code + Video)
**Location:** [backend/app/core/security.py] and [backend/app/core/audit.py]

**Authentication & Authorization:**
- JWT-based access tokens with expiration
- Bcrypt password hashing
- Role-based access control
- Token validation middleware

**Audit Logging:**
- All mutating operations (POST, PUT, PATCH, DELETE) are logged
- Tracks user_id, action, resource_type, resource_id
- Records IP address, user agent, duration
- Non-blocking - never affects request performance

**Security Best Practices:**
- Environment variable management for secrets
- Path validation in MCP servers (prevents directory traversal)
- Input sanitization
- SQL injection prevention via ORM
- CORS configuration

---

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Dashboard  │   │  Upload UI   │  │  Report View │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Multi-Agent Orchestrator                   │   │ 
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │   │
│  │  │ Vision   │ │   OCR    │ │Knowledge │              │   │
│  │  └──────────┘ └──────────┘ └──────────┘              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │   │
│  │  │  Risk    │ │Simulation│ │Recommend │              │   │
│  │  └──────────┘ └──────────┘ └──────────┘              │   │
│  │  ┌──────────┐ ┌──────────┐                           │   │
│  │  │  Debate  │ │ Commander│                           │   │
│  │  └──────────┘ └──────────┘                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MCP Servers                             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │   │
│  │  │  File    │ │ Database │ │  Search  │              │   │
│  │  └──────────┘ └──────────┘ └──────────┘              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SQLite Database                         │   │ 
│  │  Users, Incidents, Workflows, Reports, Knowledge     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Google Gemini API key (get free at https://aistudio.google.com/app/apikey)
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
- The open-source community for the amazing tools and libraries used

---

## 📞 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review demo scenarios for examples

---

<div align="center">

**Built with ❤️ for safer infrastructure and better emergency response.Make sure to Star if you like the project**

</div>

