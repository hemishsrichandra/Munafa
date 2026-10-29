# Munafa

**Recover what your store is owed. Track credits to resolution.**

A working supplier-credit copilot for the **Paytm Build for India AI Hackathon, Bengaluru · Track 1: Merchant Growth AI**. Built from the nine-slide proposal in `Munafa_IIITBlasters.pptx` for the offline hackathon on **31 October 2026**.

Munafa takes one merchant problem end to end: a supplier bills 12 packs, only 10 arrive, and the promised adjustment gets lost between bills. The merchant confirms the receiving count, reviews the claim, shares evidence, follows up, and records only a documented applied credit or received refund as recovery.

**AI reads. Rules calculate. You approve.**

## Quick start

Requirements: **Node.js 20.19+ or 22.12+**, npm, and **Python 3.11–3.13**. Commands below assume macOS/Linux and run from the repository root.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
npm ci
cp .env.example .env
npm run dev
```

Open **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**.

No API key is needed for the full synthetic demo, manual invoices, evidence downloads, English messages, supplier follow-ups or resolution tracking. Local SQLite data persists at `.data/munafa.db` and is excluded from Git. Three clearly labeled synthetic cases populate an empty database.

### One-process production build

```bash
npm run build
npm start
```

Open **http://127.0.0.1:8000**. Restart the API after the initial frontend build so it registers static assets. This serves a local prototype; it is not a production deployment configuration.

## What works

| Workflow               | Behavior                                                                                                                          |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Invoice intake         | A-104 synthetic example, manual entry, Sarvam text extraction, or image extraction through Sarvam-hosted vision                   |
| Guided confirmation    | Correct supplier/reference/date and every item; confirm actual quantities, matching units, complete delivery and effective prices |
| Claim calculation      | Integer paise arithmetic. Missing counts, unknown/mismatched units, over-deliveries and incomplete receiving block approval       |
| Evidence               | Merchant-reviewed claim card downloadable as PNG, with billed/received quantities and exact arithmetic                            |
| Supplier communication | Preview English message; optional Sarvam Hindi/Kannada translation; open WhatsApp and attach evidence manually                    |
| Sharing confirmation   | A separate merchant confirmation records sharing; opening WhatsApp never marks the case sent                                      |
| Follow-ups             | Record supplier promises and dates; overdue cases remain visible                                                                  |
| Resolution             | Match supplier and original invoice; attach proof; confirm application/receipt; support partial credit and refund                 |
| Accounting safeguards  | Unique supplier evidence references prevent duplicate recovery; excessive credit is rejected; edits invalidate approval           |
| Ledger                 | Searchable cases, status filters, supplier balances, recovery overview and safe CSV export                                        |
| Persistence            | SQLite transactions, optimistic case versions, attachment storage and event history                                               |
| Voice fallback         | Optional browser English speech recognition proposes the first item's count; merchant still checks units                          |

## Sarvam AI integration

Set the following **server-side** values in `.env`, then restart the API:

```dotenv
SARVAM_API_KEY=your-key
SARVAM_CHAT_MODEL=sarvam-105b
SARVAM_VISION_MODEL=gemma4
```

- **Native Sarvam invoice understanding:** `sarvam-105b` via `POST /v1/chat/completions` structures pasted supplier invoice text.
- **Bill image understanding:** the `gemma4` model hosted by Sarvam via `POST /v2/chat/completions` reads a base64 bill image. This is a Sarvam-hosted open-weight vision model, not Sarvam's native chat model. Account/model access must be available.
- **Indian-language communication:** `mayura:v1` via `POST /translate` translates an approved supplier message into Hindi or Kannada. The English original remains available for comparison. Long messages are split within the documented input limit.
- API keys remain in the backend. Provider authentication, timeout, malformed-output and credit/access errors are surfaced without exposing keys. No failed AI call silently becomes a fabricated extraction.
- Model output goes through the same typed validation as manual entry. AI-proposed received counts and unit confirmations are discarded. AI cannot approve, send or resolve a case.

The adapter is implemented and covered by **mocked API contract/error tests**. **Live Sarvam calls have not been validated: no key or credits were supplied.** A successful local synthetic demo does not establish live AI extraction quality or partner-credit eligibility. Check this with your own hackathon account.

Current API references used during implementation: [authentication](https://docs.sarvam.ai/api-reference/authentication), [chat models](https://docs.sarvam.ai/api/api-guides-tutorials/chat-completion/overview), [V2 image input](https://docs.sarvam.ai/api-reference/chat/chat-completions-v2), and [translation](https://docs.sarvam.ai/api-reference/text/translate-text).

## Two-minute demo

1. Choose **Add an invoice → Try a sample → Use sample invoice**.
2. For A-104, enter **10 biscuit packs**, **6 tea packs**, and **24 soap pieces**. Set the soap billed unit to `piece`, set each received unit, and confirm every matching unit.
3. Confirm delivery is complete and effective prices are correct, then **Save delivery review**.
4. Review **(12 − 10) × ₹40 = ₹80** and **Approve evidence**.
5. Download the evidence PNG and preview the supplier message. Opening WhatsApp is optional. Attach the PNG yourself if demonstrating actual sharing. Only confirm sharing if you actually sent it, or explicitly explain you are simulating the merchant step in the synthetic demo.
6. Record “Adjust against next bill” with a follow-up date.
7. Choose **Verify credit / refund → Load synthetic next-bill credit**. Inspect the attached evidence, confirm application, and record ₹80.
8. The case closes with ₹80 verified exactly once. Check the supplier ledger and Insights.

A longer demo script, partial-credit scenario and rehearsal checklist are in [docs/DEMO.md](docs/DEMO.md). A repeatable synthetic reset is provided below.

## Tests

```bash
npm test                 # Domain/API rules and mocked Sarvam contracts
npm run build            # Production frontend compilation
npx playwright install chromium
npm run test:e2e          # Builds frontend, then desktop + mobile workflow tests
```

**Current verification:** 36 backend/API tests and two desktop/mobile browser tests. Live Sarvam calls still require your key.

Browser tests start a separate API on port **8001** and use an isolated `.data/e2e-<process>.db`; your main merchant database is untouched. Stop anything occupying port 8001 first. For an existing Chromium installation, `PLAYWRIGHT_EXECUTABLE_PATH=/absolute/path/to/browser npm run test:e2e` is supported.

### Code maintenance

```bash
npm run format:check
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
```

The frontend is split into workspace, intake, case actions, case detail and shared UI components. The backend separates rules, persistence, provider access and routes.

## Demo fixtures and reset

- `samples/invoice-a104.png`: synthetic photo-intake fixture.
- `samples/invoice-a104.html`: editable source for that fixture.
- `samples/invoice-a104.txt`: billed values plus a separate merchant receiving exercise. Paste only the invoice section when trying AI extraction.
- `samples/credit-a104.txt`: illustrative invoice-referenced adjustment.

To rehearse again, stop the API and run:

```bash
.venv/bin/python -m backend.reset_demo --yes
npm run dev
```

This removes only cases marked synthetic and their attached evidence/recovery keys. It preserves manually entered and AI-extracted cases. An otherwise empty database receives the three demo-ledger cases again. Back up `.data/munafa.db` before manually managing any real records.

## Project map

```text
backend/             FastAPI routes, SQLite persistence, business rules, Sarvam adapter
backend/tests/       API and accounting invariant tests
frontend/src/        React workspace and responsive CSS
samples/             Clearly synthetic bill and credit fixtures
scripts/             Sample document rendering utility
tests/e2e/           Browser workflow tests
docs/ARCHITECTURE.md  Data flow, decisions and API contracts
docs/DEMO.md          Demonstration script and rehearsal checks
docs/ROADMAP.md       Hackathon priorities and merchant pilot plan
docs/PROGRESS.md      Current implementation status and handoff
```

## Scope and limitations

This is a **local, single-store prototype with no authentication**. Keep the supplied loopback host binding. Do not expose it to the internet or use real merchant records before adding authentication, store isolation, access-controlled evidence storage, backups and deployment protections.

The current scope is **short delivery against an invoice**, with **whole quantities** and merchant-verified effective unit prices. It does not infer carton conversions, tax treatment, scheme eligibility, multi-invoice credit allocation, price disputes or returns. Ambiguous evidence stays open; resolution verification is a documented merchant attestation, not forensic validation of an uploaded file.

There is **no live Paytm connection** and **no automatic WhatsApp sending**. Browser voice recognition depends on browser support/permission and may use the browser vendor's speech service. Sarvam extraction/translation sends the selected invoice or approved message to Sarvam only when explicitly requested. The interface uses optional Google Fonts with local system fallbacks.

No recovery outcomes have been measured. The deck's **₹199/month** price remains a hypothesis for a 3–5-merchant pilot. See the roadmap for the production and validation work ahead.

Git remote: `origin` → `https://github.com/hemishsrichandra/Munafa.git`. The prototype is maintained on `main`. Local credentials, databases, dependencies and generated build output are excluded from Git.
