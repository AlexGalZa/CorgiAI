"""
Intake data extraction — runs Claude on a completed transcript, stores results.
Mirrors server/src/services/extraction.js

Supports both PostgreSQL and in-memory fallback.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.database import query, query_one, is_db_available
from app.services import session as session_svc
from app.services import anthropic_client
from app.prompts.extraction import EXTRACTION_PROMPT

# In-memory intake store (used when DB is unavailable)
_intakes: dict[str, dict] = {}


def extract_intake_data(session_id: str) -> dict:
    """
    Build a transcript from the session's messages, run extraction via Claude,
    and store the structured result.
    """
    messages = session_svc.get_messages(session_id)
    if not messages:
        raise ValueError("No messages found for session")

    # Build transcript including attachment metadata
    lines: list[str] = []
    for m in messages:
        line = f"{m['role'].upper()}: {m['content']}"
        attachments = m.get("attachments") or []
        if isinstance(attachments, str):
            attachments = json.loads(attachments)
        if attachments:
            file_list = ", ".join(
                f"{a['filename']} ({a['type']})" for a in attachments
            )
            line += f"\n[Attachments: {file_list}]"
        lines.append(line)

    transcript = "\n\n".join(lines)
    full_prompt = EXTRACTION_PROMPT + transcript

    extracted = anthropic_client.extract(full_prompt)
    intake = _store_intake(session_id, extracted)
    return intake


def _store_intake(session_id: str, data: dict) -> dict:
    """Upsert extracted data into the intakes table or in-memory store."""
    if is_db_available():
        return query_one(
            """INSERT INTO intakes (
                session_id, company_name, dba, address, fein,
                business_description, annual_revenue, employees_total,
                employees_ft_pt, annual_payroll, policy_type,
                total_limit_requested, existing_policies, financials_available,
                records_count, cyber_incidents, shareholders_5pct,
                fye_financials, last_12mo_revenue, epl_international_entities,
                epl_claims, erisa_plan_assets, media_content_type,
                contract_required, contract_provided, uploaded_documents,
                client_questions_flagged, additional_notes, raw_extraction
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                dba = EXCLUDED.dba,
                address = EXCLUDED.address,
                fein = EXCLUDED.fein,
                business_description = EXCLUDED.business_description,
                annual_revenue = EXCLUDED.annual_revenue,
                employees_total = EXCLUDED.employees_total,
                employees_ft_pt = EXCLUDED.employees_ft_pt,
                annual_payroll = EXCLUDED.annual_payroll,
                policy_type = EXCLUDED.policy_type,
                total_limit_requested = EXCLUDED.total_limit_requested,
                existing_policies = EXCLUDED.existing_policies,
                financials_available = EXCLUDED.financials_available,
                records_count = EXCLUDED.records_count,
                cyber_incidents = EXCLUDED.cyber_incidents,
                shareholders_5pct = EXCLUDED.shareholders_5pct,
                fye_financials = EXCLUDED.fye_financials,
                last_12mo_revenue = EXCLUDED.last_12mo_revenue,
                epl_international_entities = EXCLUDED.epl_international_entities,
                epl_claims = EXCLUDED.epl_claims,
                erisa_plan_assets = EXCLUDED.erisa_plan_assets,
                media_content_type = EXCLUDED.media_content_type,
                contract_required = EXCLUDED.contract_required,
                contract_provided = EXCLUDED.contract_provided,
                uploaded_documents = EXCLUDED.uploaded_documents,
                client_questions_flagged = EXCLUDED.client_questions_flagged,
                additional_notes = EXCLUDED.additional_notes,
                raw_extraction = EXCLUDED.raw_extraction
            RETURNING *""",
            (
                session_id,
                data.get("company_name"),
                data.get("dba"),
                data.get("address"),
                data.get("fein"),
                data.get("business_description"),
                data.get("annual_revenue"),
                data.get("employees_total"),
                data.get("employees_ft_pt"),
                data.get("annual_payroll"),
                data.get("policy_type"),
                data.get("total_limit_requested"),
                data.get("existing_policies"),
                data.get("financials_available"),
                data.get("records_count"),
                data.get("cyber_incidents"),
                data.get("shareholders_5pct"),
                data.get("fye_financials"),
                data.get("last_12mo_revenue"),
                data.get("epl_international_entities"),
                data.get("epl_claims"),
                data.get("erisa_plan_assets"),
                data.get("media_content_type"),
                data.get("contract_required", False),
                data.get("contract_provided", False),
                json.dumps(data.get("uploaded_documents", [])),
                json.dumps(data.get("client_questions_flagged", [])),
                data.get("additional_notes"),
                json.dumps(data),
            ),
        )

    # In-memory fallback
    intake = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    _intakes[session_id] = intake
    return intake


def get_intake(session_id: str) -> dict | None:
    """Get intake data for a session."""
    if is_db_available():
        return query_one(
            "SELECT * FROM intakes WHERE session_id = %s",
            (session_id,),
        )
    return _intakes.get(session_id)


def list_intakes() -> list[dict]:
    """List all completed intakes."""
    if is_db_available():
        return query(
            """SELECT i.*, s.status AS session_status, s.created_at AS session_created_at
               FROM intakes i
               JOIN sessions s ON s.id = i.session_id
               ORDER BY i.created_at DESC"""
        )
    return list(_intakes.values())
