# Portal — Customer-Facing Insurance App

The Corgi portal is where customers get quotes, purchase policies, manage certificates, and file claims.

## Tech Stack

- **Next.js 16** with App Router
- **React 19**
- **Tailwind CSS 4**
- **TanStack Query 5** — server state + caching
- **Zustand 5** — client state
- **React Hook Form 7** + **Zod 4** — form handling + validation

## Routes

### Auth
| Route | Page |
|-------|------|
| `/login` | Email OTP login |
| `/register` | Create account |
| `/verify-code` | Enter OTP code |

### Dashboard
| Route | Page |
|-------|------|
| `/` | Main dashboard (policies overview, quick actions) |
| `/quotes` | Quote history |
| `/billing` | Payment methods, plans, history |
| `/certificates` | Custom certificate management |
| `/claims` | Claims list |
| `/documents` | Document center (all policy docs, COIs) |
| `/organization` | Team management, invites, roles |

### Quoting Flow
| Route | Page |
|-------|------|
| `/quote/get-started` | Coverage selection + packages |
| `/quote/[number]/company/organization-info` | Company basics |
| `/quote/[number]/company/structure-operations` | Business structure |
| `/quote/[number]/company/financial-details` | Revenue, payroll |
| `/quote/[number]/company/business-address` | Address |
| `/quote/[number]/coverage-intro` | Coverage overview |
| `/quote/[number]/[coverageSlug]` | Dynamic coverage questionnaire |
| `/quote/[number]/claims-history/loss-history` | Past claims |
| `/quote/[number]/claims-history/insurance-history` | Prior insurance |
| `/quote/[number]/notices-signatures` | Legal notices |
| `/quote/[number]/products` | Product selection |
| `/quote/[number]/summary` | Quote summary + checkout |

**22 total page routes** across 27 route directories.

## Key Features

- **Email OTP auth** — no passwords for customers, just email codes
- **Multi-step quoting** — 7 form sections with auto-save on each step
- **Dynamic questionnaires** — coverage-specific forms loaded from the Form Builder API
- **Instant pricing** — 8 coverage types rated in real-time by the rating engine
- **Mixed quote handling** — shows instant-quote and underwriting-review sections separately
- **Stripe checkout** — annual (one-time) or monthly (subscription) billing
- **Certificate builder** — create custom COIs with holder info and endorsements, PDF preview
- **Claims filing** — submit claims with file attachments
- **Billing management** — view payment history, update payment methods via Stripe portal, switch billing frequency
- **Multi-org support** — switch between organizations, manage team members and roles
- **Document center** — download policy documents, COIs, endorsements, receipts; download all as ZIP
- **Dark mode** — theme toggle with system preference detection
- **PWA support** — installable as a native app, offline-capable
- **Keyboard shortcuts** — quick navigation and actions
- **Custom components** — `CustomSelect` (accessible dropdown), `DatePicker` (calendar input), `HelpTooltip` (contextual help)
- **Welcome wizard** — guided onboarding for new users
- **Notification center** — in-app notifications
- **NPS survey** — periodic satisfaction survey
- **Mobile responsive** — fully responsive layout for all screen sizes

### Coverage Page Architecture

The coverage page is split into 9 reusable components under `src/components/coverage/`:

| Component | Purpose |
|-----------|---------|
| `CoverageOverview` | Main coverage dashboard layout |
| `CoverageCard` | Individual coverage type card |
| `CoverageDetails` | Expanded coverage details |
| `CoverageLimits` | Limits and retention display |
| `CoverageDocuments` | Policy documents for a coverage |
| `CoverageActions` | Actions (endorse, renew, certificate) |
| `CoverageStatus` | Status badge and indicators |
| `CoverageComparison` | Side-by-side coverage comparison |
| `CoverageSummary` | Aggregate coverage summary |

## Development

```powershell
# One-time: activate pnpm via Node's corepack
corepack enable && corepack prepare pnpm@9.15.0 --activate

pnpm install
pnpm run dev
```

Runs on [http://localhost:3000](http://localhost:3000).

### Environment

Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Test Accounts

Customer accounts use email OTP login (codes printed to Django console):

| Email | Role |
|-------|------|
| `policyholder@corgi.com` | Customer (password: `corgi123` for dev) |
| `sergio@corgi.com` | Customer (password: `corgi123` for dev) |

### Build

```powershell
pnpm run build
pnpm start
```
