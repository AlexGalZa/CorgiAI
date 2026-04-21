from django.db import migrations


# All step IDs that come after coverage-intro in the flow
STEPS_AFTER_COVERAGE_INTRO = {
    "directors-and-officers",
    "technology-errors-omissions",
    "commercial-general-liability",
    "cyber-liability",
    "fiduciary-liability",
    "hired-non-owned-auto",
    "media-liability",
    "employment-practices-liability",
    "loss-history",
    "insurance-history",
    "notices-signatures",
    "representations-warranties",
    "summary",
}


def backfill_coverage_intro(apps, schema_editor):
    """
    Add 'coverage-intro' to completed_steps for existing quotes that have
    already progressed past that point in the flow.

    If a quote has any step after coverage-intro completed, it means the user
    already passed through that section — so we mark coverage-intro as completed.
    We insert it right after 'structure-operations' to maintain correct ordering.
    """
    Quote = apps.get_model("quotes", "Quote")

    quotes = Quote.objects.exclude(completed_steps=[]).exclude(
        completed_steps__contains="coverage-intro"
    )

    count = 0
    for quote in quotes:
        steps = quote.completed_steps or []

        # Only backfill if the user has reached or passed the coverage section
        if not any(s in STEPS_AFTER_COVERAGE_INTRO for s in steps):
            continue

        # Insert coverage-intro after structure-operations if present,
        # otherwise append before the first coverage/post-coverage step
        if "structure-operations" in steps:
            idx = steps.index("structure-operations") + 1
            steps.insert(idx, "coverage-intro")
        else:
            steps.insert(0, "coverage-intro")

        quote.completed_steps = steps
        quote.save(update_fields=["completed_steps"])
        count += 1

    print(f"Backfilled coverage-intro for {count} quotes")


def reverse_backfill(apps, schema_editor):
    """Remove 'coverage-intro' from all completed_steps."""
    Quote = apps.get_model("quotes", "Quote")

    quotes = Quote.objects.filter(completed_steps__contains="coverage-intro")

    for quote in quotes:
        quote.completed_steps = [
            s for s in quote.completed_steps if s != "coverage-intro"
        ]
        quote.save(update_fields=["completed_steps"])


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0035_add_business_start_payroll_employees_to_company"),
    ]

    operations = [
        migrations.RunPython(backfill_coverage_intro, reverse_backfill),
    ]
