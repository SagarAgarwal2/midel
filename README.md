# Supply Chain Resilience & Decision Intelligence Platform

Full-stack platform for product-agnostic supply chain analytics (FMCG, fashion, electronics, and more).

## Stack

- Frontend: React + Vite + Tailwind CSS + Recharts
- Backend: Flask + Pandas + JSON storage
- File Parsing: Pandas (Excel/CSV), pdfplumber (PDF)
- AI/ML: Rule-based risk + optional Random Forest mode
- LLM: Groq API for PDF-to-JSON extraction, decision explanations, chat assistant

## Project Structure

- `frontend/` React SaaS UI with pages: Dashboard, Risks, Impact, Simulation, Upload, Chat
- `backend/` Flask API with endpoints:
  - `POST /upload`
  - `POST /parse`
  - `POST /risk`
  - `POST /impact`
  - `POST /decision`
  - `POST /chat`
  - `GET /summary`
  - `GET /health`

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add GROQ_API_KEY in .env
python app.py
```

Backend runs on `http://localhost:5000`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Typical Workflow

1. Open Upload page and upload `.xlsx`, `.csv`, or `.pdf`.
2. Parse file into structured records.
3. Open Risks page and run risk detection (Rule-based or Random Forest).
4. Open Impact page to compute stockout and revenue loss.
5. Open Simulation page to run advanced decision engine and LLM explanation.
6. Use Chat page for context-aware operational guidance.

## API Request Examples

### `/risk`

```json
{
  "mode": "ml"
}
```

### `/decision`

```json
{
  "demand_per_day": 120,
  "inventory": 260,
  "delay_days": 7,
  "product_price": 18,
  "supplier_reliability": 0.82,
  "alternative_suppliers": [
    {"name": "AltFast", "cost": 1.12, "delay": 4, "reliability": 0.9, "capacity": 0.7},
    {"name": "AltBudget", "cost": 0.94, "delay": 8, "reliability": 0.72, "capacity": 1.0}
  ],
  "explain": true
}
```

## Notes

- Data storage is JSON-based under `backend/data/`.
- Uploaded files are stored in `backend/uploads/`.
- If Groq key is missing, the app falls back to a rule-based parser/response where possible.
