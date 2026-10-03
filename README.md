# PersonalOS

PersonalOS is a permission-aware personal life, health, and finance supervisor built as a full-stack web app. It presents a single conversational supervisor that routes user requests to specialized agents for renewals, health analysis, stock analysis, and investment oversight.

## Features

- Unified supervisor agent that understands intent and routes requests
- Renewal management for insurance, subscriptions, and required renewals
- Sensitive health workflows with raw data, statistical observation, and AI interpretation separation
- Stock analysis without execution authority
- High-risk investment workflow with policy checks and explicit user confirmation
- Mock broker sandbox integration and audit logging
- Phase 3 typed routing contracts, capability registry, deterministic policy
  evaluation, and a policy-gated supervisor service
- MCP foundation with typed contracts, deterministic tool registration, and
  policy-approved mock read-only invocation
- Invariant: **LLM proposes. Validator validates. Policy Engine decides. Services execute only permitted operations.**
- Modern React frontend and FastAPI/Python backend
- Docker configuration for local deployment

## Quick start

1. Install dependencies:
   npm install
2. Start the app in development mode:
   npm run dev
3. Open the frontend at http://localhost:5173
4. Backend API runs at http://localhost:4000

## Demo login

- Email: `demo@personalos.ai`
- Password: the value configured by `DEMO_PASSWORD`

## Project structure

- backend/: FastAPI API, SQLAlchemy models, repositories, services, and seed data
- frontend/: Vite React app
- docker-compose.yml: local Docker composition for frontend and backend
- README.md: documentation

## Notes

- This is a demonstration app using mock/sandbox data only.
- Financial transactions are simulated and require explicit approval.
- No real banking or brokerage credentials are used.

## Backend

The backend uses PostgreSQL through SQLAlchemy (SQLite is the default for local
tests). Copy `backend/.env.example` to `backend/.env`, install
`backend/requirements.txt`, and run `uvicorn app.main:app --reload` from the
`backend` directory. `docker compose up --build` provisions PostgreSQL and the
API together. Audit entries are persisted in the database; investment actions
remain a mock sandbox workflow requiring explicit confirmation. Supervisor
routing is validated and policy evaluated before domain work is selected.
The mock `BrokerGateway` has no network or real-money capability and refuses
execution unless both policy approval and explicit user approval are present.
Investment approvals persist explicit `pending_user -> pending_mfa -> approved
-> executed` (or `rejected`) transitions. MFA is a development-only mock
boundary (`000000` or the legacy local assertion); no real MFA provider is
configured. Ownership, permissions, policy, and audit logging remain enforced
at the API boundary.
Routing components live under `backend/app/routing/` and are intentionally
side-effect free except for the application audit/repository boundary.
LangGraph is not installed or used. MCP is now present only as a foundation;
external integrations remain future work.

## MCP integration boundary

The current integration path is:

```text
Supervisor
    ↓
Routing Validator
    ↓
Policy Engine
    ↓
Authorized MCP Client
    ↓
MCP Server
    ↓
External Tool
```

**MCP is the integration/tool layer. The Policy Engine remains outside MCP and
decides whether an operation is permitted.** The MCP client only resolves
explicitly registered tools and accepts an already-approved policy context; it
does not replace authentication, authorization, ownership, approval, or MFA
checks. Only synthetic read-only renewal, health, and market tools are
registered currently. Financial execution remains mock/sandbox-only and is not
registered as an MCP tool.

## Authentication
The API uses short-lived JWT bearer tokens and Argon2 password hashes (with bcrypt verification for staged migrations). Protected resources are isolated by owner ID and permissions are enforced at route boundaries. Permissions use granular dotted names such as `renewal.read`, `renewal.create`, `renewal.update`, `renewal.delete`, `investment.propose`, and `investment.confirm`; there is no administrator bypass for financial actions. Set a strong JWT_SECRET and run `alembic upgrade head` in backend before production deployment. Logout revokes the current JWT and security failures are audited.
