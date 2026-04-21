# Corgi API Setup

## Migration Squashing

If fresh deploys are slow due to many migrations:

```bash
python manage.py squashmigrations quotes 0001 0054
python manage.py squashmigrations policies 0001 0028
```

Then delete the old migration files and commit.

**Warning:** Only squash migrations when all environments are fully migrated to the latest state. Squashing while some environments are behind can cause migration conflicts.
