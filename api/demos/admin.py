from django.contrib import admin

from demos.models import Demo


@admin.register(Demo)
class DemoAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "customer_email", "ae", "scheduled_for", "status")
    list_filter = ("status", "ae")
    search_fields = ("customer_name", "customer_email", "ae__name")
    ordering = ("-scheduled_for",)
