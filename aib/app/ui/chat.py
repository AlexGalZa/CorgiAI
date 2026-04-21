"""
Gradio chat interface — the main UI for the AI Insurance Advisor.
Handles chat, file uploads, quick-start chips, and intake completion.
"""

from __future__ import annotations
import json
import os
import traceback

import gradio as gr

from app.services import session as session_svc
from app.services import anthropic_client
from app.services import file_processor
from app.services import extraction as extraction_svc
from app.ui.theme import CUSTOM_CSS, build_theme

# ── Quick-start chips ───────────────────────────────────────────────────
QUICK_START_CHIPS = [
    "I need cyber liability insurance",
    "Looking for D&O coverage",
    "Help me with EPL insurance",
    "I need ERISA/fiduciary coverage",
    "Media liability insurance",
    "Not sure what I need — help me figure it out",
]

WELCOME_MD = """
<div class="aib-welcome">
  <div class="aib-welcome-logo">🛡️</div>
  <div class="aib-welcome-title">Welcome to AI Insurance Advisor</div>
  <div class="aib-welcome-text">
    Hi! I'm your AI insurance co-pilot. I'll help you get started with your
    specialty insurance needs — including analyzing your existing policies
    and recommending additional coverages. What can I help you with today?
  </div>
</div>
"""


def _format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _build_completion_html(intake: dict) -> str:
    """Build an HTML summary panel for a completed intake."""
    fields = [
        ("Company Name", intake.get("company_name")),
        ("DBA", intake.get("dba")),
        ("Address", intake.get("address")),
        ("FEIN", intake.get("fein")),
        ("Business Description", intake.get("business_description")),
        ("Annual Revenue", intake.get("annual_revenue")),
        ("Total Employees", intake.get("employees_total")),
        ("FT/PT Breakdown", intake.get("employees_ft_pt")),
        ("Annual Payroll", intake.get("annual_payroll")),
        ("Policy Type", intake.get("policy_type")),
        ("Coverage Limit", intake.get("total_limit_requested")),
        ("Existing Policies", intake.get("existing_policies")),
        ("Additional Notes", intake.get("additional_notes")),
    ]
    rows = ""
    for label, value in fields:
        if value:
            rows += f"<tr><td>{label}</td><td>{value}</td></tr>\n"

    questions_html = ""
    questions = intake.get("client_questions_flagged") or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except (json.JSONDecodeError, TypeError):
            questions = []
    if questions:
        items = "".join(f"<li>{q}</li>" for q in questions)
        questions_html = (
            '<h4 style="margin-top:12px;">Questions for Broker Follow-up</h4>'
            f"<ul>{items}</ul>"
        )

    return f"""
<div class="aib-completion">
  <h3>✅ Intake Complete</h3>
  <p class="subtitle">Here's a summary of the information collected.
  Your broker will review this and prepare quotes.</p>
  <table>{rows}</table>
  {questions_html}
</div>
"""


# ── Chat handler ────────────────────────────────────────────────────────

def _handle_message(
    user_text: str,
    file: str | None,
    history: list[dict],
    session_id: str | None,
    is_complete: bool,
):
    """
    Core chat handler called by Gradio.

    Parameters
    ----------
    user_text : str
        The user's typed message.
    file : str | None
        Path to an uploaded file (Gradio temp path), or None.
    history : list[dict]
        Gradio messages-format chat history (list of {"role", "content"} dicts).
    session_id : str | None
        Current session UUID (stored in gr.State).
    is_complete : bool
        Whether the intake has already been completed.

    Returns
    -------
    tuple of (history, session_id, is_complete, completion_html, file_value)
    """
    if is_complete:
        return history, session_id, is_complete, gr.update(), None

    # Create session on first message
    if not session_id:
        sess = session_svc.create_session()
        session_id = str(sess["id"])

    # ── Process file if present ─────────────────────────────────────
    message_content = None  # what goes to Claude (str or list)
    stored_content = ""     # what goes to DB (always str)
    attachment_meta: list[dict] = []

    if file:
        filename = os.path.basename(file)
        error = file_processor.validate_file(file, filename)
        if error:
            history.append({"role": "assistant", "content": f"⚠️ {error}"})
            return history, session_id, is_complete, gr.update(), None

        saved_path = file_processor.save_upload(file, filename)
        file_data = file_processor.process_file(saved_path, filename)

        message_content = anthropic_client.build_multimodal_content(
            user_text or "", file_data
        )

        if file_data["type"] == "image":
            stored_content = (
                f"{user_text}\n\n[Attached image: {filename}]"
                if user_text
                else f"[Attached image: {filename}]"
            )
        else:
            stored_content = (
                f"{user_text}\n\n[Attached PDF: {filename} — {file_data.get('page_count', '?')} pages]"
                if user_text
                else f"[Attached PDF: {filename} — {file_data.get('page_count', '?')} pages]"
            )

        attachment_meta = [{
            "filename": filename,
            "type": file_data["type"],
            "size": file_data["size"],
            "storedAs": os.path.basename(saved_path),
            **({"pageCount": file_data["page_count"]} if file_data.get("page_count") else {}),
        }]
    else:
        if not (user_text or "").strip():
            return history, session_id, is_complete, gr.update(), None
        message_content = user_text.strip()
        stored_content = user_text.strip()

    # ── Add user message to UI history ──────────────────────────────
    display_text = stored_content
    if file and attachment_meta:
        att = attachment_meta[0]
        icon = "📄" if att["type"] == "pdf" else "🖼️"
        display_text = f"{icon} **{att['filename']}** ({_format_file_size(att['size'])})\n\n{user_text or ''}"

    history.append({"role": "user", "content": display_text.strip()})

    # ── Store user message in DB ────────────────────────────────────
    session_svc.add_message(session_id, "user", stored_content, attachment_meta)

    # ── Build Claude messages from DB ───────────────────────────────
    db_messages = session_svc.get_messages(session_id)
    claude_messages = []
    for idx, m in enumerate(db_messages):
        if idx == len(db_messages) - 1 and file:
            claude_messages.append({"role": m["role"], "content": message_content})
        else:
            claude_messages.append({"role": m["role"], "content": m["content"]})

    # ── Call Claude ─────────────────────────────────────────────────
    try:
        ai_response = anthropic_client.chat(claude_messages)
    except Exception as exc:
        traceback.print_exc()
        history.append({
            "role": "assistant",
            "content": f"⚠️ AI service error: {exc}. Please try again.",
        })
        return history, session_id, is_complete, gr.update(), None

    # ── Store assistant response ────────────────────────────────────
    session_svc.add_message(session_id, "assistant", ai_response)

    # Strip [INTAKE_COMPLETE] from display
    display_response = ai_response.replace("[INTAKE_COMPLETE]", "").strip()
    history.append({"role": "assistant", "content": display_response})

    # ── Check for intake completion ─────────────────────────────────
    completion_html = ""
    if "[INTAKE_COMPLETE]" in ai_response:
        is_complete = True
        try:
            intake = extraction_svc.extract_intake_data(session_id)
            session_svc.update_session_status(session_id, "completed")
            completion_html = _build_completion_html(intake)
        except Exception as exc:
            traceback.print_exc()
            completion_html = f"<p>⚠️ Failed to extract intake data: {exc}</p>"

    return (
        history,
        session_id,
        is_complete,
        gr.update(value=completion_html, visible=bool(completion_html)),
        None,  # clear file input
    )


def _handle_chip(chip_text: str, history, session_id, is_complete):
    """Handle a quick-start chip click — just delegates to _handle_message."""
    return _handle_message(chip_text, None, history, session_id, is_complete)


def _new_chat():
    """Reset everything for a new conversation."""
    return [], None, False, gr.update(value="", visible=False)


# ── Build the Gradio Blocks app ─────────────────────────────────────────

def create_app() -> tuple[gr.Blocks, object, str]:
    """
    Construct and return (blocks, theme, css).

    In Gradio 6.x theme/css are passed to launch() or mount_gradio_app(),
    not to the Blocks constructor.
    """
    theme = build_theme()

    with gr.Blocks(
        title="AI Insurance Advisor",
    ) as app:
        # ── State ───────────────────────────────────────────────────
        session_state = gr.State(value=None)
        complete_state = gr.State(value=False)

        # ── Header ──────────────────────────────────────────────────
        gr.HTML("""
        <div class="aib-header">
          <div class="aib-header-left">
            <div class="aib-header-logo">🛡️</div>
            <div>
              <div class="aib-header-title">AI Insurance Advisor</div>
              <div class="aib-header-subtitle">AI Insurance Co-Pilot</div>
            </div>
          </div>
        </div>
        """)

        # ── Chatbot ─────────────────────────────────────────────────
        chatbot = gr.Chatbot(
            value=[],
            label="Chat",
            show_label=False,
            height=480,
            avatar_images=(None, "https://em-content.zobj.net/source/twitter/408/shield_1f6e1-fe0f.png"),
        )

        # ── Welcome + quick-start chips (visible when chat is empty) ─
        with gr.Column(visible=True) as welcome_col:
            gr.HTML(WELCOME_MD)
            with gr.Row():
                chip_btns = []
                for chip in QUICK_START_CHIPS[:3]:
                    chip_btns.append(gr.Button(chip, size="sm", variant="secondary"))
            with gr.Row():
                for chip in QUICK_START_CHIPS[3:]:
                    chip_btns.append(gr.Button(chip, size="sm", variant="secondary"))

        # ── Completion panel (hidden until intake is done) ──────────
        completion_panel = gr.HTML(value="", visible=False)

        # ── Input row ───────────────────────────────────────────────
        with gr.Row():
            file_input = gr.File(
                label="Attach",
                file_types=[".jpg", ".jpeg", ".png", ".pdf"],
                type="filepath",
                scale=1,
            )
            text_input = gr.Textbox(
                placeholder="Type your message or drop a file above...",
                show_label=False,
                lines=1,
                max_lines=4,
                scale=5,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

        with gr.Row():
            new_chat_btn = gr.Button("🔄 New Chat", variant="secondary", size="sm")

        # ── Wiring ──────────────────────────────────────────────────

        # Send button / Enter key
        send_inputs = [text_input, file_input, chatbot, session_state, complete_state]
        send_outputs = [chatbot, session_state, complete_state, completion_panel, file_input]

        def on_send(text, file, history, sid, done):
            result = _handle_message(text, file, history, sid, done)
            return result

        send_btn.click(
            fn=on_send,
            inputs=send_inputs,
            outputs=send_outputs,
        ).then(
            fn=lambda: ("", gr.update(visible=False)),
            outputs=[text_input, welcome_col],
        )

        text_input.submit(
            fn=on_send,
            inputs=send_inputs,
            outputs=send_outputs,
        ).then(
            fn=lambda: ("", gr.update(visible=False)),
            outputs=[text_input, welcome_col],
        )

        # Quick-start chip buttons
        for btn in chip_btns:
            btn.click(
                fn=lambda chip=btn.value: _handle_chip(
                    chip, [], None, False
                ),
                outputs=send_outputs,
            ).then(
                fn=lambda: ("", gr.update(visible=False)),
                outputs=[text_input, welcome_col],
            )

        # New chat
        new_chat_btn.click(
            fn=_new_chat,
            outputs=[chatbot, session_state, complete_state, completion_panel],
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[welcome_col],
        )

    return app, theme, CUSTOM_CSS
