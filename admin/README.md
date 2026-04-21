# Admin — Internal Operations Dashboard

The Corgi admin dashboard is a staff-only app for managing quotes, policies, claims, and analytics.

## Tech Stack

- **React 19**
- **Vite** — build tool + dev server
- **Tailwind CSS 4**
- **TanStack Query 5** — data fetching + caching
- **TanStack Table 8** — sortable, filterable data tables
- **Recharts** — charts and data visualization
- **Lucide React** — icon library
- **React Hook Form 7** + **@hookform/resolvers** — form handling
- **Axios** — HTTP client
- **@dnd-kit** — drag-and-drop for kanban boards

## Pages

| Page | File | Description |
|------|------|-------------|
| Dashboard | `Dashboard.tsx` | Role-based dashboards (Ops, Finance, BDR, Broker) with analytics |
| Quotes | `Quotes.tsx` | Quote pipeline with filters, inline actions |
| Quote Detail | `QuoteDetail.tsx` | Full quote view, approve, recalculate, simulate, duplicate |
| Policies | `Policies.tsx` | Policy list with status filters |
| Policy Detail | `PolicyDetail.tsx` | Policy details, endorse, cancel, reactivate |
| Claims | `Claims.tsx` | Claims list with status workflow |
| Claim Detail | `ClaimDetail.tsx` | Claim details, status editor, internal docs kanban |
| Brokered Requests | `BrokeredRequests.tsx` | Pipeline view (kanban + table) for brokered coverages |
| Certificates | `Certificates.tsx` | Certificate management, form, detail panel |
| Payments | `Payments.tsx` | Payment tracking with detail panel |
| Organizations | `Organizations.tsx` | Org management with create/edit form |
| Producers | `Producers.tsx` | Insurance producer management |
| Users | `Users.tsx` | User list with impersonation, create/edit |
| Reports | `Reports.tsx` | Reporting and exports |
| Profile | `Profile.tsx` | Staff profile settings |
| Login | `Login.tsx` | Staff authentication |
| Not Found | `NotFound.tsx` | 404 page |

**17 pages** total.

## Key Features

- **RBAC** — 7 roles enforced via `permissions.ts` role matrix (admin, ae, ae_underwriting, bdr, finance, broker, policyholder). UI adapts to show/hide features per role
- **Role-based dashboards** — Operations, Finance, BDR, and Broker views with tailored analytics
- **Analytics suite** — pipeline overview, premium by carrier, coverage breakdown, claims summary, monthly premium trend, loss ratio, action items, analytics event tracking
- **Quote management** — approve, recalculate (re-rate), simulate (what-if), duplicate quotes
- **Policy lifecycle** — endorse (modify limits, add/remove coverage, backdate), cancel with Stripe refund, reactivate with gap premium
- **Claims workflow** — status transitions, internal document kanban board
- **Brokered pipeline** — kanban and table views for brokered coverage requests with inline status/carrier editing, bulk actions
- **Commissions page** — commission tracking and payouts (visible to finance + admin roles)
- **Audit log** — filterable log of all system changes
- **User impersonation** — view the portal as any customer for support, with TTL-limited sessions and visible impersonation banner
- **Command palette** — Ctrl+K quick navigation
- **Bulk actions** — select multiple records for batch operations
- **CSV export** — export data tables to CSV
- **StaffNotifications** — real-time notification system for staff
- **UserTimeline** — activity timeline on user detail pages
- **CustomerContextSidebar** — customer context panel for support workflows
- **FormBuilder version history** — track and compare form definition changes

## Components

| Directory | Contents |
|-----------|----------|
| `components/dashboards/` | OperationsDashboard, FinanceDashboard, BDRDashboard, BrokerDashboard |
| `components/brokerage/` | RequestPipeline, RequestTable, RequestForm, RequestDetailPanel, filters, inline editors |
| `components/claims/` | ClaimStatusEditor, InternalDocsKanban |
| `components/certificates/` | CertificateForm, CertificateDetailPanel |
| `components/payments/` | PaymentDetailPanel |
| `components/organizations/` | OrganizationForm |
| `components/producers/` | ProducerForm |
| `components/users/` | UserForm |
| `components/layout/` | AppLayout, Sidebar, TopBar |
| `components/ui/` | DataTable, MetricCard, ChartCard, StatusBadge, CommandPalette, Pagination, ExportButton, Spinner, EmptyState, ErrorBoundary, etc. |

## Hooks

| Hook | Purpose |
|------|---------|
| `useAnalytics` | Fetch all analytics endpoints |
| `useAuditLog` | Paginated audit log queries |
| `useBrokeredRequests` | Brokered request CRUD |
| `useCertificates` | Certificate management |
| `useClaims` | Claims queries and mutations |
| `useFocusTrap` | Accessibility focus management |
| `useOrganizations` | Org CRUD |
| `usePayments` | Payment queries |

## Development

```powershell
# One-time: activate pnpm via Node's corepack
corepack enable && corepack prepare pnpm@9.15.0 --activate

pnpm install
pnpm run dev -- --port 3001
```

Runs on [http://localhost:3001](http://localhost:3001).

### Environment

Create `.env`:
```
VITE_API_URL=http://localhost:8000
```

### Test Accounts

All staff accounts use password `corgi123`:

| Email | Role | Dashboard |
|-------|------|-----------|
| `admin@corgi.com` | admin | Full access |
| `ae@corgi.com` | ae | Account Executive |
| `ae_underwriting@corgi.com` | ae_underwriting | AE + Underwriting |
| `bdr@corgi.com` | bdr | Business Development |
| `finance@corgi.com` | finance | Finance + Commissions |
| `broker@corgi.com` | broker | Broker (scoped) |

### Build

```powershell
pnpm run build
pnpm run preview
```
