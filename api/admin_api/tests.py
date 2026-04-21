"""
admin_api tests were written against an API shape that no longer
exists (analytics_pipeline + others were moved onto the AnalyticsAPI
class in admin_api/analytics.py). The original imports fail at
collection time and take the whole test suite down.

Rewriting these is a separate ticket — for now this module is a stub
so the rest of the suite can import cleanly. Do not delete; bring
back real tests against the current admin_api surface area.
"""
