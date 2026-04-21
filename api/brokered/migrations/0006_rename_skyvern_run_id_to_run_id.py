from django.db import migrations


class Migration(migrations.Migration):
    """
    Renames skyvern_run_id -> run_id in local DBs where 0005 created skyvern_run_id.
    Production already has run_id from the corrected 0005, so this is a safe no-op there.
    """

    dependencies = [
        ("brokered", "0005_add_skyvern_run_id_remove_error_log"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'brokered_quote_requests'
                        AND column_name = 'skyvern_run_id'
                    ) THEN
                        ALTER TABLE brokered_quote_requests RENAME COLUMN skyvern_run_id TO run_id;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
