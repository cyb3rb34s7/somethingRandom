Perfect! Here's a **detailed PRD (Product Requirements Document)** for your **Database AI Agent for PostgreSQL Insights**, covering all the aspects you've outlined.

---

# 📄 Product Requirements Document (PRD)

## 🧩 Project Name:

**PostgreSQL AI Agent for Data Insights**

---

## 🧠 1. Problem Statement

Organizations often rely on large, complex PostgreSQL databases with multiple schemas and interconnected tables. Extracting meaningful insights from such databases requires manually writing intricate SQL queries that are:

* Time-consuming and error-prone.
* Difficult to maintain or reuse across different questions.
* Not user-friendly for non-technical users.

This process becomes a bottleneck for business intelligence, especially when the goal is ad-hoc analysis or dashboard generation.

---

## 💡 2. Our Solution

Build an **AI-powered agent** that:

* Accepts **natural language queries** from users.
* **Intelligently inspects** the database structure.
* **Identifies relevant schemas/tables** dynamically.
* **Generates and executes SQL queries** safely.
* Returns structured results (tables) or **visual insights (graphs)**.

### ✅ Key Capabilities:

* Real-time schema discovery (no manual DDL needed)
* Natural language to SQL translation using GenAI
* Visualizations (bar, pie, line) based on the data
* Multi-agent system with roles like schema explorer, query builder, and executor

---

## 🏗️ 3. Architecture Overview

```plaintext
             ┌─────────────────────────────┐
             │  User (via Web UI or API)   │
             └────────────┬────────────────┘
                          │
                          ▼
              ┌────────────────────┐
              │ Orchestrator Agent │
              └────────────────────┘
                          │
  ┌──────────────┬────────┴──────────────┬───────────────┐
  ▼              ▼                       ▼               ▼
[Schema]     [Intent Parser]       [Query Builder]   [Validator]
Inspector         ↓                        ↓               ↓
     └────→ [Relevant Tables] → [SQL Query] → Check → [Final SQL]
                                                            ↓
                                                  ┌─────────▼─────────┐
                                                  │    SQL Executor   │
                                                  └─────────┬─────────┘
                                                            ↓
                                                    [Result + Graph]
```

---

## 🧰 4. Tech Stack

| Component            | Stack                                          |
| -------------------- | ---------------------------------------------- |
| **Backend**          | Python + FastAPI                               |
| **Agents & Tooling** | LangChain + LangGraph                          |
| **Database**         | PostgreSQL (with multiple schemas)             |
| **Frontend**         | Next.js + Tailwind + Recharts                  |
| **AI Model APIs**    | Mistral via Groq, or Together.ai               |
| **Visuals**          | Plotly (backend) or Recharts (frontend)        |
| **Security**         | Query validation, safe SELECTs, query timeouts |

---

## 🧪 5. AI APIs Used

| Provider        | Model                     | Features                  | Cost      |
| --------------- | ------------------------- | ------------------------- | --------- |
| **Groq**        | Mistral 7B/8x             | Fast, cheap, reliable     | Free tier |
| **Together.ai** | Mistral / Mixtral / LLaMA | Hosted open-source models | Free tier |
| *(Optional)*    | Local via Ollama          | Offline testing           | Free      |

We will begin with Groq for fast iteration and test results.

---

## 🚀 6. Implementation Plan

### ✅ Phase 1: MVP (POC)

* Set up FastAPI backend
* Use LangChain agents with tools:

  * `SchemaInspector`
  * `SQLQueryBuilder`
  * `SQLExecutor`
* Connect to PostgreSQL
* Accept English query → SQL → table response

### 🎯 Phase 2: Visual Output

* Add `VisualizerAgent` to choose the right chart
* Use Plotly or Recharts to render

### 🧠 Phase 3: Agent Specialization (MCP)

* Add agents for role-based tasks (intent parsing, table selection, SQL validation)

---

## 📊 7. Open-Source Dataset for Testing

We need a large PostgreSQL-compatible, multi-schema dataset. Here are top options:

### ✅ \[1] **Pagila** (Film rental)

* Based on DVD rental business
* Many interlinked tables, foreign keys
* Good for demo + relational logic
* [GitHub Repo](https://github.com/devrimgunduz/pagila)

### ✅ \[2] **TPCH / TPCC Benchmarks**

* Business dataset with orders, customers, regions
* Supports joins, aggregations
* [TPC-H Dataset Generator](https://github.com/electrum/tpch-dbgen)

### ✅ \[3] **IMDB Dataset (via IMDbpy + Postgres)**

* Very rich multi-entity data (movies, people, genres)
* Needs setup
* Great for real-world demos

Let’s start with **Pagila**, as it has:

* Multiple schemas
* Realistic data
* Ready for PostgreSQL import

---

## 🧪 8. POC Scope

### Input

> “Show me total sales by country over the past year”

### Process

1. `SchemaInspector` looks up where “sales” and “country” live
2. `QueryBuilder` generates SQL
3. `Validator` ensures safe execution
4. `Executor` returns top 10 rows
5. `Visualizer` (optional): bar chart of sales by country

### Output

* SQL: `SELECT country, SUM(amount) ...`
* Table or bar chart

---

## ✅ Next Steps

1. Set up FastAPI project with LangChain
2. Load Pagila into local Postgres
3. Integrate schema inspection + SQL builder
4. Test Groq or Together AI APIs
5. Build first end-to-end prompt-to-query flow

---

Would you like me to scaffold the FastAPI project (backend) and define the schema inspector tool first?
