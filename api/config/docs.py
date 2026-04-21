import json
from django.shortcuts import render
from ninja.openapi.docs import DocsBase


class Scalar(DocsBase):
    template = "ninja/scalar.html"

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}

    def render_page(self, request, api, **kwargs):
        context = {
            "scalar_settings": json.dumps(self.settings),
            "openapi_json_url": self.get_openapi_url(api, kwargs),
            "api": api,
        }
        return render(request, self.template, context)
