"""
Add brokered-variant fields to ProductConfiguration.

Part of Trello 1.1 — Create BROKERED Stripe Product Variants.

Adds:
  - is_brokered_variant: marks a ProductConfiguration as the BROKERED sibling
    of a direct product (used for >$5M routing and other brokered flows).
  - parent_variant: self-FK from a brokered variant back to its direct twin.

This migration is schema-only. The actual brokered siblings are created by
the idempotent ``create_brokered_variants`` management command, which also
mirrors the products into Stripe with ``brokered: true`` metadata.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0003_add_fidelity_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="productconfiguration",
            name="is_brokered_variant",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text=(
                    "True if this ProductConfiguration is the BROKERED sibling of a "
                    "direct product (used when limit > $5M or other >5M brokered routing)."
                ),
                verbose_name="Is Brokered Variant",
            ),
        ),
        migrations.AddField(
            model_name="productconfiguration",
            name="parent_variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="brokered_children",
                to="products.productconfiguration",
                help_text=(
                    "Link from a brokered variant back to its direct (non-brokered) twin. "
                    "Null on the direct product itself."
                ),
                verbose_name="Parent Variant",
            ),
        ),
    ]
