# Completed Column Audit — Re-verification on `master`

Date: 2026-04-18
Auditor: `backend-dev-1`
Branch audited: `master` @ `617b2e0`

Re-verifies every card listed in the Trello "Completed" column against the current state of the monorepo, after session deliveries backfilled cards previously flagged `❌` / `⚠`.

Legend: `✅` present, `⚠` partial/placeholder/stub, `❌` missing on master.

| Card | Status | Evidence |
| --- | --- | --- |
| Brokered Policy Cancellation Notifications | ❌ | No brokered-specific cancel notification path. No template `api/templates/emails/brokered_cancel*.html`, no `notify_broker_cancel` / `send_brokered` symbols anywhere in `api/brokered/` or `api/policies/`. Only the generic customer `policy_cancelled.html` exists (`api/templates/emails/policy_cancelled.html`, rendered at `api/webhooks/service.py:623`). |
| Legacy Stripe Product Coverage Type Lookup | ✅ | `api/stripe_integration/legacy.py` with `infer_coverage_for_legacy_product`, `list_legacy_products`, `migrate_legacy_metadata`; references "Trello card 4.8" in the module docstring. |
| Fix Policy/Contact Data Mixing | ⚠ | No dedicated fix module / migration commit. Org-scoping exists in query paths (`api/policies/api.py` uses `organization_id`; tests `api/organizations/tests.py`, `api/certificates/tests.py`), but there is no identifiable "mixing" remediation PR/commit or symbol. Treat as likely addressed inline in existing isolation queries — needs card-owner confirmation. |
| BROKERED Stripe Product Variants | ✅ | Commit `c0cb112 Create BROKERED Stripe Product Variants (1.1)`. Files: `api/products/migrations/0004_brokered_variants.py` (adds `is_brokered_variant`, `parent_variant`), `api/products/management/commands/create_brokered_variants.py`, plus `api/products/selection.py` & `models.py` updates. |
| Brokered Bot Auto-Restart (dropped) | ✅ | Explicitly dropped. No `restart_bot` / `keep_alive` / `skyvern.*restart` symbols — consistent with drop. |
| Migrate Existing Clients to New Stripe | ✅ | `api/stripe_integration/management/commands/migrate_legacy_subscriptions.py` (docstring: "Migrate existing clients to the new Stripe product structure (Trello card 2.2)"). Merge `5e3dcb8 feat/2.1-stripe-payout-ids` and `0cd6b9a feat/2.2-migrate-legacy-subs`. |
| Email Existence Verification (dropped) | ✅ | Dropped per card. No `VerifyEmail` / dedicated `email_verification` service; only `hubspot_sync` + `users` touch `verify_email` incidentally. |
| $5M Limits | ✅ | `api/common/constants.py` defines `MAX_SELF_SERVE_LIMIT`; validated at `api/policies/api.py:1571` (`if payload.new_limit > MAX_SELF_SERVE_LIMIT`). |
| Self-Serve Increasing Limits | ✅ | `POST /api/v1/policies/{id}/raise-limit` at `api/policies/api.py:1507` with `RaiseLimitRequest` schema (line 1490), portal page `portal/src/app/(dashboard)/coverages/[id]/raise-limit/page.tsx`. |
| Reinstatement Emails + Self-Service | ✅ | Commit `e876eae Add reinstatement emails + self-service page (6.5)`. Token helpers at `api/policies/api.py:437-462` (`generate_reinstatement_token`, `decode_reinstatement_token`, `REINSTATEMENT_TOKEN_SALT`). Template `api/templates/emails/policy_reinstatement.html`. |
| Fix Effective Date / Trial Period | ✅ | `api/policies/service.py:126-279` computes `effective_date`, derives `trial_end` for deferred effective dates (Stripe `trial_end = int(effective_datetime.timestamp())`). Migration `api/quotes/migrations/0021_remove_quote_effective_date_and_more.py` normalizes storage. |
| Dashboard Redesign (Coverages) | ✅ | `portal/src/components/coverage/PolicyCard.tsx`, `PolicyDetailModal.tsx`, `index.ts`, `LimitDisclaimerModal.tsx`; consumed from `portal/src/app/(dashboard)/page.tsx`. |
| Add Cancellation Email | ✅ | Template `api/templates/emails/policy_cancelled.html`; sent from `api/webhooks/service.py:623` (`render_to_string('emails/policy_cancelled.html', ...)`) with error handling at line 646. |
| Fix Certificate/Download Button | ✅ | Hook `useDownloadCertificate` at `portal/src/hooks/use-certificates.ts:192`; consumed in `portal/src/components/certificate-detail-modal.tsx:8,31` and `portal/src/app/(dashboard)/certificates/page.tsx:10,103`. |
| Additional Insured Flow in Certificates | ✅ | `api/certificates/additional_insured_service.py`, migration `api/certificates/migrations/0007_add_additional_insured.py`, template `api/templates/emails/additional_insured_coi.html`, plus `api/certificates/models.py` / `schemas.py` / `api.py`. |
| Update Django Roles | ✅ | `api/users/migrations/0022_add_read_only_role.py` (adds `read_only` role; covers H18). Seed script `api/seed_roles.py`. Admin permissions in `api/common/admin_permissions.py`. Commit `3bd6fff Add read_only role + read-only API key provisioning (H18)`. |
| Crime & Fidelity Product | ✅ | Crime seeded in `api/products/migrations/0002_seed_product_configurations.py:111` (`custom-crime` / "Commercial Crime"); Fidelity added by `api/products/migrations/0003_add_fidelity_product.py` (`custom-fidelity` / "Fidelity Bond"). |
| Umbrella Product | ✅ | Seeded in `api/products/migrations/0002_seed_product_configurations.py:167` (`custom-umbrella` / "Umbrella / Excess Liability"). Also referenced in `api/quotes/migrations/0047_add_bop_umbrella_excess_coverage_choices.py`. |
| Legal Disclaimer on Landing Page | ✅ | `portal/src/app/(public)/legal/page.tsx`, `portal/src/app/(public)/disclaimers/page.tsx`, `portal/src/app/(public)/layout.tsx`, and `portal/src/components/coverage/LimitDisclaimerModal.tsx`. |
| Comparison Pages (Embroker, Vouch) | ✅ | `portal/src/app/(public)/embroker/page.tsx` (metadata: "Corgi vs Embroker — Compare Business Insurance"), `portal/src/app/(public)/vouch/page.tsx`. Both have filler `TODO(marketing)` blocks pending legal review — status remains `✅` for code presence. |
| Submit Updated Sitemaps | ⚠ | `portal/src/app/sitemap.ts` exists (home/product/comparison/legal tiers) and M5 commit `149e16b Sitemap Organization + CWV (M5)` is on master. No docs/ops record of the post-deploy *submission* to Google/Bing Search Console — that action is external. Code-side artifact is complete. |
| Brokered Policy Notification Bot (dropped) | ✅ | Dropped. `brokered_stuck_alert.html` + `feat/H10-stuck-brokering-alert` (commit `6f199b5`) replace it at a smaller scope. |
| Add Stripe Fees to Brokered Policies | ✅ | `api/stripe_integration/fees.py` (docstring: "Passes Stripe processing fees (2.9% + $0.30 for card, 0.8% capped at $5.00..."). Referenced from `api/stripe_integration/service.py`, `api/stripe_integration/api.py`, and commit `1f922c4 Add Taxes & Fees section on brokered policies (3.5)`. |
| Fix Stripe Quote Session Creation | ✅ | `api/stripe_integration/service.py:201,229,277,325` all call `client.checkout.Session.create(**checkout_params)` on four quote flows; wired through `api/quotes/service.py` and `api/policies/renewal_service.py`. |

## Summary

- ✅ 21
- ⚠ 2  (Fix Policy/Contact Data Mixing; Submit Updated Sitemaps)
- ❌ 1  (Brokered Policy Cancellation Notifications)

Total: 24 cards re-verified. (The brief names 24 cards, not 27 — see list above.)

### Regressions / open gaps

1. **Brokered Policy Cancellation Notifications** — only the generic customer `policy_cancelled.html` is wired; no brokered-broker-side notification path is present on master. Either the card was merged without code or the notification was intentionally folded into the generic email — needs card-owner reconciliation.
2. **Fix Policy/Contact Data Mixing** — organization-scoping code exists, but no identifiable remediation commit / module. Likely inline-fixed; worth a follow-up note on the card pointing to `api/organizations/tests.py` + `api/certificates/tests.py` as the verification harness.
3. **Submit Updated Sitemaps** — the code artifact is present, but the external submission step (Search Console) is not recorded anywhere in the repo. Non-blocking for code verification.
