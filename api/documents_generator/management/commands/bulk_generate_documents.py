"""
Management command: bulk_generate_documents

Generates COIs, declaration pages, and loss runs for multiple policies at once.
Accepts policy IDs or filters (carrier, status, date range).
Output to a directory or zip file.

Usage examples:
    # All active policies → ./bulk_docs/
    python manage.py bulk_generate_documents --status active

    # Specific policy IDs → zip file
    python manage.py bulk_generate_documents --policy-ids 1,2,3 --output-zip /tmp/docs.zip

    # By carrier, date range → directory
    python manage.py bulk_generate_documents \\
        --carrier TechRRG \\
        --effective-from 2024-01-01 \\
        --effective-to 2024-12-31 \\
        --output-dir /tmp/docs

    # Dry run (list what would be generated)
    python manage.py bulk_generate_documents --status active --dry-run

Document types generated per policy group (grouped by quote/purchase):
  - COI (Certificate of Insurance)
  - Declaration Page (CGL or Tech)
  - Audit Confirmation Letter
  - Loss Run (per organization, generated once)
"""

import logging
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bulk generate COIs, dec pages, loss runs and audit confirmations for multiple policies"

    def add_arguments(self, parser):
        # Selection filters
        parser.add_argument(
            "--policy-ids",
            type=str,
            default=None,
            help="Comma-separated list of policy IDs to process.",
        )
        parser.add_argument(
            "--status",
            type=str,
            default=None,
            help="Filter by policy status (active, cancelled, expired, etc.).",
        )
        parser.add_argument(
            "--carrier",
            type=str,
            default=None,
            help="Filter by carrier name (case-insensitive contains).",
        )
        parser.add_argument(
            "--effective-from",
            type=str,
            default=None,
            help="Filter policies with effective_date >= YYYY-MM-DD.",
        )
        parser.add_argument(
            "--effective-to",
            type=str,
            default=None,
            help="Filter policies with effective_date <= YYYY-MM-DD.",
        )
        parser.add_argument(
            "--coverage-type",
            type=str,
            default=None,
            help="Filter by coverage_type slug.",
        )

        # Output options
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Directory to write generated files. Created if it does not exist.",
        )
        parser.add_argument(
            "--output-zip",
            type=str,
            default=None,
            help="Path for output zip file (mutually exclusive with --output-dir).",
        )

        # Document type selection
        parser.add_argument(
            "--doc-types",
            type=str,
            default="coi,dec,loss-run,audit",
            help="Comma-separated list of doc types to generate: coi, dec, loss-run, audit. Default: all.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be generated without writing any files.",
        )

    def handle(self, *args, **options):
        from policies.models import Policy
        from documents_generator.service import DocumentsGeneratorService
        from documents_generator.loss_run import generate_loss_run
        from documents_generator.audit_confirmation import generate_audit_confirmation

        dry_run = options["dry_run"]
        doc_types = {t.strip() for t in options["doc_types"].split(",")}

        # Determine output destination
        output_dir = options["output_dir"]
        output_zip = options["output_zip"]

        if not output_dir and not output_zip:
            output_dir = str(Path.cwd() / "bulk_docs")
            self.stdout.write(
                self.style.NOTICE(f"No output specified — defaulting to {output_dir}")
            )

        if output_dir and output_zip:
            self.stdout.write(
                self.style.ERROR(
                    "Specify either --output-dir or --output-zip, not both."
                )
            )
            return

        # Build queryset
        qs = Policy.objects.select_related(
            "quote", "quote__company", "quote__organization"
        ).all()

        if options["policy_ids"]:
            ids = [
                int(x.strip())
                for x in options["policy_ids"].split(",")
                if x.strip().isdigit()
            ]
            qs = qs.filter(pk__in=ids)

        if options["status"]:
            qs = qs.filter(status=options["status"])

        if options["carrier"]:
            qs = qs.filter(carrier__icontains=options["carrier"])

        if options["effective_from"]:
            qs = qs.filter(effective_date__gte=options["effective_from"])

        if options["effective_to"]:
            qs = qs.filter(effective_date__lte=options["effective_to"])

        if options["coverage_type"]:
            qs = qs.filter(coverage_type=options["coverage_type"])

        policies = list(
            qs.order_by("quote__organization_id", "quote__id", "policy_number")
        )

        if not policies:
            self.stdout.write(
                self.style.WARNING("No policies match the given filters.")
            )
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Found {len(policies)} policy(ies). Doc types: {', '.join(sorted(doc_types))}"
            )
        )

        if dry_run:
            self._dry_run(policies, doc_types)
            return

        # Group policies by quote for COI/dec generation
        from itertools import groupby

        policies.sort(key=lambda p: p.quote_id)
        quote_groups = {}
        for quote_id, group in groupby(policies, key=lambda p: p.quote_id):
            quote_groups[quote_id] = list(group)

        # Track loss runs already generated (once per org)
        org_loss_runs_done = set()

        # Collect generated files: {filename: bytes}
        generated: dict[str, bytes] = {}
        errors = []

        for quote_id, group_policies in quote_groups.items():
            first_policy = group_policies[0]
            quote = first_policy.quote
            org = getattr(quote, "organization", None)
            company = getattr(quote, "company", None)
            org_name = (org.name if org else None) or (
                getattr(company, "entity_legal_name", None) or f"org_{quote_id}"
            )
            safe_org = _safe_name(org_name)

            # COI
            if "coi" in doc_types:
                try:
                    coi_number = (
                        getattr(first_policy, "coi_number", None) or f"COI-{quote_id}"
                    )
                    pdf = DocumentsGeneratorService.generate_coi_for_policies(
                        group_policies, coi_number
                    )
                    if pdf:
                        fname = f"{safe_org}/COI_{coi_number}.pdf"
                        generated[fname] = pdf
                        self.stdout.write(f"  ✓ COI  {fname}")
                except Exception as e:
                    errors.append(f"COI quote={quote_id}: {e}")
                    self.stdout.write(
                        self.style.WARNING(f"  ✗ COI  quote={quote_id}: {e}")
                    )

            # Declaration Page
            if "dec" in doc_types:
                for policy in group_policies:
                    try:
                        from common.constants import CGL_COVERAGE, HNOA_COVERAGE
                        from documents_generator.constants import (
                            TECH_COVERAGE_CONFIG,
                            NTIC_COVERAGE_CONFIG,
                        )
                        from common.constants import NTIC_CARRIER

                        pdf = None
                        if policy.coverage_type in {CGL_COVERAGE, HNOA_COVERAGE}:
                            if getattr(policy, "carrier", "") == NTIC_CARRIER:
                                pdf = DocumentsGeneratorService.generate_ntic_cgl_policy_for_policy(
                                    policy, group_policies
                                )
                            else:
                                pdf = DocumentsGeneratorService.generate_cgl_policy_for_policy(
                                    policy, group_policies
                                )
                        elif (
                            policy.coverage_type in TECH_COVERAGE_CONFIG
                            or policy.coverage_type in NTIC_COVERAGE_CONFIG
                        ):
                            if getattr(policy, "carrier", "") == NTIC_CARRIER:
                                pdf = DocumentsGeneratorService.generate_ntic_tech_policy_for_policy(
                                    policy, group_policies
                                )
                            else:
                                pdf = DocumentsGeneratorService.generate_tech_policy_for_policy(
                                    policy, group_policies
                                )

                        if pdf:
                            fname = f"{safe_org}/DEC_{policy.policy_number}.pdf"
                            generated[fname] = pdf
                            self.stdout.write(f"  ✓ DEC  {fname}")
                    except Exception as e:
                        errors.append(f"DEC policy={policy.policy_number}: {e}")
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ✗ DEC  policy={policy.policy_number}: {e}"
                            )
                        )

            # Audit Confirmation (per policy)
            if "audit" in doc_types:
                for policy in group_policies:
                    try:
                        pdf = generate_audit_confirmation(policy)
                        if pdf:
                            fname = f"{safe_org}/AUDIT_{policy.policy_number}.pdf"
                            generated[fname] = pdf
                            self.stdout.write(f"  ✓ AUDIT  {fname}")
                    except Exception as e:
                        errors.append(f"AUDIT policy={policy.policy_number}: {e}")
                        self.stdout.write(
                            self.style.WARNING(f"  ✗ AUDIT  {fname}: {e}")
                        )

            # Loss Run (once per org)
            if "loss-run" in doc_types and org and org.pk not in org_loss_runs_done:
                try:
                    pdf = generate_loss_run(org)
                    if pdf:
                        fname = f"{safe_org}/LOSS_RUN_{safe_org}.pdf"
                        generated[fname] = pdf
                        org_loss_runs_done.add(org.pk)
                        self.stdout.write(f"  ✓ LOSS-RUN  {fname}")
                except Exception as e:
                    errors.append(f"LOSS-RUN org={org.pk}: {e}")
                    self.stdout.write(
                        self.style.WARNING(f"  ✗ LOSS-RUN org={org.pk}: {e}")
                    )

        # Write output
        if generated:
            if output_zip:
                self._write_zip(output_zip, generated)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Wrote {len(generated)} file(s) to {output_zip}"
                    )
                )
            else:
                self._write_dir(output_dir, generated)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Wrote {len(generated)} file(s) to {output_dir}"
                    )
                )
        else:
            self.stdout.write(self.style.WARNING("\nNo documents were generated."))

        if errors:
            self.stdout.write(self.style.ERROR(f"\n{len(errors)} error(s):"))
            for err in errors:
                self.stdout.write(self.style.ERROR(f"  • {err}"))

    def _dry_run(self, policies, doc_types):
        from itertools import groupby

        policies.sort(key=lambda p: p.quote_id)
        quote_groups = {}
        for quote_id, group in groupby(policies, key=lambda p: p.quote_id):
            quote_groups[quote_id] = list(group)

        self.stdout.write(self.style.NOTICE("\n[DRY RUN] Would generate:"))
        total = 0
        for quote_id, group_policies in quote_groups.items():
            first = group_policies[0]
            q = first.quote
            org = getattr(q, "organization", None)
            org_name = (org.name if org else None) or f"quote_{quote_id}"
            if "coi" in doc_types:
                self.stdout.write(f"  COI  [{org_name}] quote={quote_id}")
                total += 1
            for p in group_policies:
                if "dec" in doc_types:
                    self.stdout.write(
                        f"  DEC  [{org_name}] {p.policy_number} ({p.coverage_type})"
                    )
                    total += 1
                if "audit" in doc_types:
                    self.stdout.write(f"  AUDIT  [{org_name}] {p.policy_number}")
                    total += 1
            if "loss-run" in doc_types and org:
                self.stdout.write(f"  LOSS-RUN  [{org_name}]")
                total += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nTotal: {total} document(s) would be generated.")
        )

    @staticmethod
    def _write_zip(zip_path: str, files: dict[str, bytes]):
        Path(zip_path).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, data in files.items():
                zf.writestr(fname, data)

    @staticmethod
    def _write_dir(dir_path: str, files: dict[str, bytes]):
        base = Path(dir_path)
        for fname, data in files.items():
            out = base / fname
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)


def _safe_name(name: str) -> str:
    """Convert an organization name to a safe directory/file component."""
    import re

    safe = re.sub(r"[^\w\s-]", "", name)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:60] or "unknown"
