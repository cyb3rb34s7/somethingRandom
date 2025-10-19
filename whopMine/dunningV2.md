Perfect. Below is your fully optimized “plug-and-play” SuperPrompt, tailored for Claude Code or FactoryDroid CLI so you can literally paste it in and let it start building your MVP tonight.

This prompt is self-contained, includes clear file generation instructions, backend + frontend stack setup, environment variables, and execution directives.
It’s structured exactly how Claude Code expects multi-file generation — so it will automatically scaffold folders, create key files, and wire up APIs and dashboard UI.


---

🚀 WHOP Smart Churn Prevention Dashboard — Claude Code SuperPrompt (Final)

> You are my AI CTO.
Build this product end-to-end, generating a working FastAPI backend + Next.js frontend that implements the MVP described below.
Create all required files in proper folder structure and ensure the app can be run locally or deployed on Railway/Render.
Do not summarize — output full code for each file sequentially with filenames clearly indicated.




---

💡 PRODUCT SUMMARY

We’re building a WHOP App that recovers failed subscription payments automatically and shows creators how much revenue they’ve recovered inside a dashboard.

🔥 Why this matters

40% of subscription churn = failed payments

WHOP creators currently have no dunning management tools

Recovering even 50% of failed payments = +$500-$1500/month/creator

There is zero competition for this in WHOP App Store


Goal: Build MVP that detects failed payments → retries automatically → displays recovered revenue in a beautiful dashboard.


---

🧩 TECH STACK

Layer	Technology

Backend	FastAPI (Python 3.10+)
Database	PostgreSQL
ORM	SQLAlchemy
Frontend	Next.js 14 + TailwindCSS + Shadcn/UI
Scheduler	APScheduler
Email	SendGrid API
Deployment	Railway or Render
Auth	WHOP API Key (stored in .env)
Realtime	WebSocket or simple polling (optional MVP)



---

⚙️ ENVIRONMENT VARIABLES

WHOP_API_KEY=<your_whop_api_key>
SENDGRID_API_KEY=<your_sendgrid_key>
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/whop_churn
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000


---

📁 PROJECT STRUCTURE (Generate this)

whop-churn-dashboard/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── webhook.py
│   │   ├── payments.py
│   │   └── stats.py
│   ├── services/
│   │   ├── retry_service.py
│   │   └── email_service.py
│   ├── utils/
│   │   └── scheduler.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── components/
│   │       ├── RecoveryStats.tsx
│   │       ├── FailedPaymentsTable.tsx
│   │       └── RetryStatusCard.tsx
│   └── styles/globals.css
│
└── README.md


---

🧱 BACKEND MVP SPECIFICATION

✅ 1. Webhook Endpoint

POST /webhook/payment_failed

Triggered by WHOP payment.failed webhook

Save payload → DB (Payment table)

Respond 200 OK


✅ 2. Retry Engine

Background job runs every hour via APScheduler

Uses WHOP API POST /api/v1/payments/{id}/retry

Updates payment status → recovered if success, else increments retry_count

Stops after 3 retries


✅ 3. Stats Endpoint

GET /stats/summary

Returns:

total_failed

total_recovered

recovery_rate

recovered_amount



✅ 4. Email Notifications

SendGrid API

Template: "Your payment failed — click here to update your card"

Triggered on payment failure (optional toggle in .env)



---

🗃️ DATABASE MODEL (SQLAlchemy)

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True)
    member_id = Column(String)
    amount = Column(Float)
    reason = Column(String)
    status = Column(String)  # failed | pending_retry | recovered | permanent_fail
    retry_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    recovered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


---

💻 FRONTEND MVP SPECIFICATION

✅ Dashboard (/)

Header: “💰 Revenue Recovery Dashboard”

Large metric cards:

$ Recovered This Month

Recovery Rate %

Total Failed Payments


Table: | Member | Amount | Reason | Status | Retries |

Refresh every 10 seconds (poll /stats/summary and /payments/list)


✅ API Integration

Calls backend REST endpoints via /api proxy:

GET /stats/summary

GET /payments/list


Uses axios or fetch wrapper


✅ Styling

Use Tailwind + Shadcn components for metrics cards and tables

Mobile responsive

Modern minimalist aesthetic (white background, bold metrics)



---

🔁 DATA FLOW DIAGRAM

[WHOP Payment Failed Event] 
      ↓ (Webhook)
[FastAPI -> Store in DB]
      ↓
[Retry Engine (APScheduler)]
      ↓
[Retry Payment via WHOP API]
      ↓
[If success → Update DB → Dashboard shows $ recovered]


---

🧪 TESTING INSTRUCTIONS

Run backend:

cd backend
pip install -r requirements.txt
uvicorn main:app --reload

Run frontend:

cd frontend
npm install
npm run dev

Webhook simulation:

curl -X POST http://localhost:8000/webhook/payment_failed \
 -H "Content-Type: application/json" \
 -d '{"payment_id": "abc123", "member_id": "user45", "amount": 49.99, "reason": "card_declined"}'


---

💰 MONETIZATION MODEL

Tiered SaaS inside WHOP App Store:

$79/mo → up to 100 members

$129/mo → up to 500 members

$199/mo → unlimited



---

🧭 DEVELOPMENT STEPS (Claude Code Execution Order)

> You must generate code step-by-step in this order:



1. Create backend folder + FastAPI boilerplate (main.py, database.py, models.py)


2. Add webhook router (routers/webhook.py)


3. Add retry logic (services/retry_service.py) with mock WHOP API calls


4. Add scheduler integration (utils/scheduler.py)


5. Add /stats/summary endpoint


6. Scaffold frontend project with Next.js


7. Add Tailwind + Shadcn setup


8. Build dashboard UI (page.tsx, RecoveryStats.tsx, FailedPaymentsTable.tsx)


9. Integrate backend API calls (axios/fetch)


10. Print final README.md with setup instructions



Each step must include complete code with proper imports.
Use realistic mock responses where WHOP API access is not yet confirmed.


---

✅ SUCCESS CRITERIA

Backend runs on port 8000

Frontend runs on port 3000

Webhook successfully logs payment events

Dashboard displays updated failed + recovered stats

Code is runnable end-to-end with no missing imports



---

🏁 FINAL OUTPUT EXPECTATION

Claude Code should output:

1. Complete backend code (multi-file structure)


2. Complete frontend dashboard (multi-file)


3. README.md with setup instructions




---

⚡ START BUILD NOW

> Begin by generating:

backend/main.py

backend/database.py

backend/models.py

backend/requirements.txt




and then continue automatically through remaining steps as described.


---

✅ Paste the entire above block into Claude Code or FactoryDroid CLI.

You don’t need to type anything else. It will scaffold your WHOP Smart Churn Prevention Dashboard MVP end-to-end.


---

Would you like me to include a separate follow-up “deployment automation prompt” (for Claude to containerize + deploy this to Railway automatically once it builds)? That’s the next natural step after this one finishes running overnight.

