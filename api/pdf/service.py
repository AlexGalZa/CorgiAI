import math

import fitz
from io import BytesIO
from typing import Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, create_string_object
from django.conf import settings


class PDFService:
    @staticmethod
    def add_watermark(pdf_bytes: bytes, text: str = "SAMPLE") -> bytes:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        font = fitz.Font("helv")

        for page in doc:
            rect = page.rect
            cx, cy = rect.width / 2, rect.height / 2
            font_size = min(rect.width, rect.height) / 4

            tw = fitz.TextWriter(rect)
            tw.append(fitz.Point(0, 0), text, font=font, fontsize=font_size)
            text_length = tw.text_rect.width

            angle = math.radians(45)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            morph = (
                fitz.Point(cx, cy),
                fitz.Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0),
            )

            tw2 = fitz.TextWriter(rect)
            tw2.append(
                fitz.Point(cx - text_length / 2, cy + font_size / 3),
                text,
                font=font,
                fontsize=font_size,
            )
            tw2.write_text(page, morph=morph, color=(0.75, 0.75, 0.75), opacity=0.3)

        output = BytesIO()
        doc.save(output, garbage=3, deflate=True)
        doc.close()

        return output.getvalue()

    @staticmethod
    def flatten_pdf(pdf_bytes: bytes) -> bytes:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page in doc:
            for widget in page.widgets():
                widget.update()

        doc.bake()

        output = BytesIO()
        doc.save(output, garbage=3, deflate=True)
        doc.close()

        return output.getvalue()

    @staticmethod
    def fill_pdf_form(template_path: str, field_data: dict) -> bytes:
        template_full_path = str(settings.TEMPLATES_DIR / template_path)

        reader = PdfReader(template_full_path)

        if reader.is_encrypted:
            reader.decrypt("")

        for page in reader.pages:
            if "/Annots" in page:
                annots = page["/Annots"]

                for annot_ref in annots:
                    annot = annot_ref.get_object()
                    field_name = str(annot.get("/T", ""))

                    if field_name in field_data:
                        value = field_data[field_name]
                        field_type = annot.get("/FT", "")

                        if field_type == "/Btn":
                            annot[NameObject("/V")] = NameObject("/1")
                            annot[NameObject("/AS")] = NameObject("/1")
                        else:
                            annot[NameObject("/V")] = create_string_object(value)

        writer = PdfWriter()
        writer.append(reader)

        if "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = (
                BooleanObject(True)
            )

        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    @staticmethod
    def merge_pdfs_with_bytes(
        pdf_bytes: bytes, pdf_paths: list[str]
    ) -> Optional[bytes]:
        try:
            writer = PdfWriter()

            filled_reader = PdfReader(BytesIO(pdf_bytes))
            for page in filled_reader.pages:
                writer.add_page(page)

            if "/AcroForm" in filled_reader.trailer.get("/Root", {}):
                writer._root_object[NameObject("/AcroForm")] = filled_reader.trailer[
                    "/Root"
                ]["/AcroForm"]
                writer._root_object[NameObject("/AcroForm")][
                    NameObject("/NeedAppearances")
                ] = BooleanObject(True)

            for path in pdf_paths:
                full_path = str(settings.TEMPLATES_DIR / path)
                reader = PdfReader(full_path)
                for page in reader.pages:
                    writer.add_page(page)

            output = BytesIO()
            writer.write(output)
            return output.getvalue()
        except Exception:
            return None

    @staticmethod
    def merge_pdfs_with_form_data(pdf_configs: list[dict]) -> Optional[bytes]:
        try:
            writer = PdfWriter()

            for config in pdf_configs:
                if "bytes" in config:
                    reader = PdfReader(BytesIO(config["bytes"]))
                elif "form_data" in config and config["form_data"]:
                    filled_bytes = PDFService.fill_pdf_form(
                        config["path"], config["form_data"]
                    )
                    reader = PdfReader(BytesIO(filled_bytes))
                else:
                    full_path = str(settings.TEMPLATES_DIR / config["path"])
                    reader = PdfReader(full_path)

                for page in reader.pages:
                    writer.add_page(page)

            if "/AcroForm" in writer._root_object:
                writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = (
                    BooleanObject(True)
                )

            output = BytesIO()
            writer.write(output)
            return output.getvalue()
        except Exception:
            return None
