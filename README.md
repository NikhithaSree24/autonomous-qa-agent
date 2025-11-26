#  Autonomous QA Agent – Test Case & Selenium Script Generator

This project implements an intelligent QA agent capable of building a knowledge base from project documentation and generating:

 Structured, documentation-grounded **test cases**  
 Executable **Selenium Python scripts**  

Backend uses **FastAPI**, UI uses **Streamlit**, and reasoning is grounded strictly in uploaded documents.

---

#  Features

### Phase 1 — Knowledge Base Ingestion
- Upload documentation (`.md`, `.txt`, `.json`, `.pdf`)
- Upload `checkout.html`
- Extract text, chunk, embed, store in vector DB
- Build a persistent "Testing Brain"

###  Phase 2 — Test Case Generation (RAG + LLM)
- Retrieve relevant documentation sections
- Generate JSON-structured test cases only
- 100% grounded in:
  - product_specs.md  
  - ui_ux_guide.txt  
  - api_endpoints.json  
  - checkout.html

### Phase 3 — Selenium Script Generator
- Select generated test case
- Upload HTML again
- Produce runnable Selenium Python code  
  (Chrome WebDriver, explicit waits, correct selectors, assertions)

---

# Project Structure
AUTONOMOUS-QA-AGENT/
│
├── app/
│ ├── agent.py
│ ├── ingest.py
│ ├── kb.py
│ └── main.py
│
├── assets/
│ ├── api_endpoints.json
│ ├── checkout.html
│ ├── product_specs.md
│ └── ui_ux_guide.txt
│
├── uploads/
├── examples/
│ └── example_generated_script_TC-001.py
│
├── streamlit_app.py
├── requirements.txt
├── testcases.json
└── README.md


---

# Installation

### 1️. Clone the repo
```bash
git clone https://github.com/<your-username>/autonomous-qa-agent.git
cd autonomous-qa-agent

2️. Create venv
python -m venv .venv
.venv\Scripts\activate

3️. Install dependencies
pip install -r requirements.txt

Setup Secrets

Create:

.streamlit/secrets.toml


Add:

OPENAI_API_KEY = "your_openai_key_here"
API_BASE = "http://localhost:8000"

Running
Start FastAPI backend:
uvicorn app.main:app --reload --port 8000

Start Streamlit UI:
streamlit run streamlit_app.py

How to Use
Step 1 — Upload documents

Upload all 4 files:

product_specs.md

ui_ux_guide.txt

api_endpoints.json

checkout.html
Then click Build Knowledge Base.

Step 2 — Generate Test Cases

Enter:

Generate positive and negative test cases for discount code SAVE15.


Click Generate Test Cases.

Step 3 — Select Test Case

Choose from dropdown:
TC-001 - Discount Code - Valid, etc.

Step 4 — Generate Selenium Script

Upload checkout.html again.
Click Generate Selenium Script.

You will receive a fully runnable Python script.



