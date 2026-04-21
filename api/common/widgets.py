import json
from django import forms


class PrettyJSONWidget(forms.Textarea):
    """
    A textarea widget that displays JSON in a formatted, readable way.
    Includes syntax highlighting and auto-formatting.
    """

    def __init__(self, attrs=None):
        default_attrs = {
            "style": (
                'font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace; '
                "font-size: 13px; "
                "line-height: 1.5; "
                "padding: 12px; "
                "border-radius: 6px; "
                "background-color: #1e1e1e; "
                "color: #d4d4d4; "
                "border: 1px solid #3c3c3c; "
                "white-space: pre; "
                "overflow-x: auto; "
                "tab-size: 2; "
            ),
            "rows": 20,
            "cols": 80,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def format_value(self, value):
        """Pretty print the JSON value."""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    class Media:
        css = {"all": []}
        js = []


class PrettyJSONField(forms.CharField):
    """Form field for JSON with pretty formatting."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", PrettyJSONWidget)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value, indent=2, ensure_ascii=False)
        return value

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
