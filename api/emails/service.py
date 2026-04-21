import resend
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from django.conf import settings
from emails.schemas import SendEmailInput

EMAIL_LOG_DIR = Path(settings.BASE_DIR) / "logs" / "emails"


class EmailService:
    @staticmethod
    def get_client():
        resend.api_key = settings.RESEND_API_KEY
        return resend

    @staticmethod
    def _build_params(input: SendEmailInput) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "from": input.from_email,
            "to": input.to,
            "subject": input.subject,
            "html": input.html,
        }

        if input.reply_to:
            params["reply_to"] = input.reply_to
        if input.cc:
            params["cc"] = input.cc
        if input.bcc:
            params["bcc"] = input.bcc
        if input.attachments:
            params["attachments"] = input.attachments

        return params

    @staticmethod
    def _to_log(params: Dict[str, Any]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        to_str = params.get("to", ["unknown"])[0].replace("@", "_at_").replace(".", "_")
        filepath = EMAIL_LOG_DIR / f"{timestamp}_{to_str}.log"

        filepath.write_text(params.get("html", ""))
        return str(filepath)

    @staticmethod
    def _create_email_log(
        input: SendEmailInput,
        status: str = "sent",
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_by=None,
    ):
        """Create an EmailLog record. Runs in a try/except so it never breaks sending."""
        try:
            from emails.models import EmailLog

            recipient = input.to[0] if input.to else ""
            EmailLog.objects.create(
                recipient=recipient,
                subject=input.subject,
                body=input.html or "",
                status=status,
                provider_message_id=provider_message_id,
                error_message=error_message,
                sent_by=sent_by,
            )
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to create EmailLog for %s", input.to, exc_info=True
            )

    @staticmethod
    def send(input: SendEmailInput, sent_by=None) -> Any:
        params = EmailService._build_params(input)

        if not settings.SEND_EMAILS:
            log_path = EmailService._to_log(params)
            EmailService._create_email_log(input, status="dev_log", sent_by=sent_by)
            return log_path

        client = EmailService.get_client()
        try:
            result = client.Emails.send(params)
            provider_id = getattr(result, "id", None) or (
                result.get("id") if isinstance(result, dict) else None
            )
            EmailService._create_email_log(
                input,
                status="sent",
                provider_message_id=str(provider_id) if provider_id else None,
                sent_by=sent_by,
            )
            return result
        except Exception as e:
            EmailService._create_email_log(
                input, status="failed", error_message=str(e), sent_by=sent_by
            )
            raise

    @staticmethod
    def send_batch(inputs: List[SendEmailInput]) -> Any:
        if not inputs:
            return None

        if not settings.SEND_EMAILS:
            return [EmailService._to_log(EmailService._build_params(i)) for i in inputs]

        client = EmailService.get_client()
        batch_params = [EmailService._build_params(input) for input in inputs]
        return client.Batch.send(batch_params)
