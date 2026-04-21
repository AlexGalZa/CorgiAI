"""
Management command: check_dependencies

Runs pip-audit against the project's installed packages and reports
any known vulnerabilities. Optionally alerts via email.

Usage:
    python manage.py check_dependencies
    python manage.py check_dependencies --json          # output raw JSON
    python manage.py check_dependencies --alert-email admin@corgi.insure
    python manage.py check_dependencies --requirements /path/to/requirements.txt
    python manage.py check_dependencies --fail-on-vuln  # exit code 1 if vulns found

Requirements:
    pip install pip-audit

Recommended: run in CI and weekly via cron.
"""

import json
import logging
import subprocess
import sys

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run pip-audit to check for known dependency vulnerabilities"

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="output_json",
            help="Output raw JSON from pip-audit.",
        )
        parser.add_argument(
            "--requirements",
            type=str,
            default=None,
            help="Path to requirements file. If not set, audits the current environment.",
        )
        parser.add_argument(
            "--alert-email",
            type=str,
            default=None,
            help="Email address to send a vulnerability alert to if issues are found.",
        )
        parser.add_argument(
            "--fail-on-vuln",
            action="store_true",
            help="Exit with code 1 if any vulnerabilities are found.",
        )

    def handle(self, *args, **options):
        output_json = options["output_json"]
        requirements = options["requirements"]
        alert_email = options["alert_email"]
        fail_on_vuln = options["fail_on_vuln"]

        # Build pip-audit command
        cmd = [
            sys.executable,
            "-m",
            "pip_audit",
            "--format",
            "json",
            "--progress-spinner",
            "off",
        ]
        if requirements:
            cmd += ["-r", requirements]

        self.stdout.write(self.style.NOTICE("Running pip-audit…"))
        self.stdout.write(f"  Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "pip-audit is not installed. Run: pip install pip-audit"
                )
            )
            return
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.ERROR("pip-audit timed out after 120 seconds.")
            )
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running pip-audit: {e}"))
            return

        # pip-audit exits 1 if vulns found, 0 if clean
        raw_output = result.stdout or result.stderr or ""

        if output_json:
            self.stdout.write(raw_output)
            return

        # Parse JSON output
        try:
            audit_data = json.loads(raw_output)
        except (json.JSONDecodeError, ValueError):
            self.stdout.write(
                self.style.WARNING(f"Could not parse pip-audit output:\n{raw_output}")
            )
            return

        # pip-audit JSON format: {"dependencies": [{"name": ..., "version": ..., "vulns": [...]}]}
        dependencies = audit_data.get("dependencies", [])
        vulnerable = [d for d in dependencies if d.get("vulns")]

        if not vulnerable:
            total = len(dependencies)
            self.stdout.write(
                self.style.SUCCESS(f"✓ No vulnerabilities found in {total} package(s).")
            )
            return

        # Format vulnerability report
        self.stdout.write(
            self.style.ERROR(
                f"\n⚠ Found vulnerabilities in {len(vulnerable)} package(s):\n"
            )
        )

        vuln_lines = []
        for dep in vulnerable:
            name = dep.get("name", "unknown")
            version = dep.get("version", "?")
            for vuln in dep.get("vulns", []):
                vid = vuln.get("id", "N/A")
                desc = vuln.get("description", "")[:200]
                fix_versions = vuln.get("fix_versions", [])
                fix_str = (
                    f"Fix: {', '.join(fix_versions)}"
                    if fix_versions
                    else "No fix available"
                )
                line = f"  {name}=={version} [{vid}] {fix_str}\n    {desc}"
                self.stdout.write(self.style.ERROR(line))
                vuln_lines.append(line)

        # Send alert email if requested
        if alert_email and vuln_lines:
            self._send_alert(alert_email, vulnerable, vuln_lines)

        if fail_on_vuln:
            raise SystemExit(1)

    def _send_alert(self, alert_email: str, vulnerable: list, vuln_lines: list):
        try:
            from emails.service import EmailService
            from emails.schemas import SendEmailInput
            from django.conf import settings

            rows_html = ""
            for dep in vulnerable:
                name = dep.get("name", "unknown")
                version = dep.get("version", "?")
                for vuln in dep.get("vulns", []):
                    vid = vuln.get("id", "N/A")
                    desc = vuln.get("description", "")[:300]
                    fix_versions = vuln.get("fix_versions", [])
                    fix_str = ", ".join(fix_versions) if fix_versions else "—"
                    rows_html += (
                        f"<tr>"
                        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;">{name}=={version}</td>'
                        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{vid}</td>'
                        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{fix_str}</td>'
                        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280;">{desc}</td>'
                        f"</tr>"
                    )

            html = f"""
            <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;">
                <h2 style="color:#dc2626;">⚠ Dependency Vulnerability Report</h2>
                <p>{len(vulnerable)} vulnerable package(s) found in the Corgi Insurance API.</p>
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <thead>
                        <tr style="background:#f9fafb;">
                            <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Package</th>
                            <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Vuln ID</th>
                            <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Fix Version</th>
                            <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Description</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                <p style="margin-top:16px;">
                    Run <code>pip install pip-audit &amp;&amp; pip-audit</code> in the api/ directory to see full details.
                </p>
            </body></html>
            """

            from_email = getattr(
                settings, "DEFAULT_FROM_EMAIL", "security@corgi.insure"
            )
            EmailService.send(
                SendEmailInput(
                    to=[alert_email],
                    subject=f"[Security] {len(vulnerable)} dependency vulnerability(s) found",
                    html=html,
                    from_email=from_email,
                )
            )
            self.stdout.write(self.style.SUCCESS(f"  Alert sent to {alert_email}"))
        except Exception as e:
            logger.error("Failed to send vulnerability alert: %s", e)
            self.stdout.write(self.style.WARNING(f"  Could not send alert email: {e}"))
