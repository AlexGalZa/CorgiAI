from dataclasses import dataclass
from typing import Optional, BinaryIO


@dataclass
class UploadFileInput:
    file: BinaryIO
    path_prefix: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
