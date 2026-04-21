from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class SendEmailInput:
    to: List[str]
    subject: str
    html: str
    from_email: str
    reply_to: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
