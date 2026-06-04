# ComplaintsGPT

An agentic AI system for analyzing CFPB consumer complaints using structured SQL analytics, semantic search, automated ingestion, and LangGraph orchestration.

The system combines:

- Statistical analysis using PostgreSQL
- Semantic complaint analysis using vector search
- Automated CFPB complaint ingestion
- Natural language querying
- Human approval workflows
- LangGraph agent orchestration
- Agent Chat UI frontend

---

# Features

## Complaint Intelligence

Ask questions such as:

- What are the top complaint issues for Bank of America this year?
- What issues generate the most complaints in Florida?
- What complaint categories are increasing over time?
- Which products have the highest complaint volume?
- What are customers saying about mortgage servicing?

---

## Automated Data Coverage

The system automatically:

1. Determines whether required data exists
2. Creates ingestion jobs when needed
3. Pulls complaint data from the CFPB API
4. Loads data into PostgreSQL
5. Updates vector indexes

No manual data loading is required.

---

## Semantic Analysis

Beyond SQL analytics, the system can answer:

- Why are customers dissatisfied?
- What frustrations are emerging?
- What themes appear in complaint narratives?
- What complaints are associated with a specific issue?

---

## Agentic Workflow

The backend uses a LangGraph workflow:

```text
MessageInput
    ↓
FilterExtraction
    ↓
FilterValidation
    ↓
CompanyValidation
    ↓
CompanyResolutionReview
    ↓
DataCoverageControl
    ↓
Ingestion
    ↓
QueryDecomposition
    ↓
SQLQueryDevelopment
    ↓
SQLQueryValidation
    ↓
TaskExecution
    ↓
Synthesis
```

The agent dynamically decides:

- What filters are needed
- Whether ingestion is required
- Which tasks are statistical
- Which tasks are semantic
- How results should be synthesized

---

# Architecture

## Backend

- Python
- LangGraph
- LangChain
- OpenAI
- PostgreSQL
- DeepLake

## Frontend

- Next.js
- React
- Agent Chat UI

## Data Source

- CFPB Consumer Complaint Database

---

# Project Structure

```text
langgraph-project/
│
├── prod/
│   ├── src/
│   │   ├── db/
│   │   ├── graph/
│   │   ├── nodes/
│   │   ├── scripts/
│   │   └── state/
│   │
│   ├── requirements.txt
│   └── langgraph.json
│
├── complaints-gpt/
│   ├── apps/
│   │   ├── agents/
│   │   └── web/
│   └── package.json
│
└── README.md
```

---

# Prerequisites

Install:

- Python 3.12+
- PostgreSQL
- Node.js 20+
- pnpm
- Git

---

# Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/complaints-gpt.git

cd complaints-gpt
```

---

# Backend Setup

Navigate to the backend:

```bash
cd prod
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

### Mac/Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file inside the `prod` directory and populate it with the following values:

```env
OPENAI_API_KEY=your_own_key
LANGSMITH_API_KEY=your_own_key

dbname=complaints-db
agent=agent_user

host=localhost
port=5432

user=your_own_user
password=your_own_password
```

### Notes

- `OPENAI_API_KEY` is required for all LLM functionality.
- `LANGSMITH_API_KEY` is optional but recommended for tracing and debugging.
- `dbname=complaints-db` should not be modified.
- `agent=agent_user` should not be modified.
- `host=localhost` and `port=5432` are the default PostgreSQL settings and typically do not need to be changed.
- `user` should be a PostgreSQL user with permissions to create databases, roles, and tables during setup.
- `password` should be the password associated with the PostgreSQL user above.

---

# Database Setup

Start PostgreSQL and ensure your configured user can connect.

Run:

```bash
python src/scripts/setup_database.py
```

This script will:

- Create the database if it does not exist
- Create all required tables
- Create supporting metadata tables
- Prepare the application for ingestion

Optional:

```bash
psql -U postgres -f src/scripts/roles.sql
```

This creates a restricted application role that can be used in production environments.

---

# Running the Backend

From the `prod` directory:

```bash
langgraph dev
```

Or expose it publicly:

```bash
langgraph dev --tunnel
```

You should see output similar to:

```text
API: https://xxxx.trycloudflare.com
Studio: https://smith.langchain.com/studio
```

---

# Frontend Setup

Open a new terminal.

Navigate to the frontend:

```bash
cd complaints-gpt
```

Install dependencies:

```bash
pnpm install
```

Create environment variables:

```bash
cp .env.example .env
```

Update the backend URL if necessary.

Run the application:

```bash
pnpm dev
```

---

# Using the Application

Example questions:

```text
What were the top complaint issues for Bank of America in 2025?

What issues generated the most complaints in Florida last year?

What are customers saying about mortgage servicing?

What complaint categories increased the most compared to last year?

What is the least common issue reported for Bank of America this year?
```

---

# Security

The project includes:

- Filter validation
- Company validation
- SQL validation
- Read-only query generation
- Human approval for ambiguous company matches
- Optional restricted PostgreSQL role

The agent cannot execute:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- TRUNCATE

through generated SQL.

---

# Future Improvements

- Visualizations
- Topic clustering
- Scheduled reporting
- Email delivery
- Multi-user support

---

# License

This project is provided for educational and research purposes.

Use at your own risk.
