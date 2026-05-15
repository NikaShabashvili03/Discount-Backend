"""
Standalone fix script. Creates the two missing review tables using Django's
own schema editor, so column types/constraints exactly match what Django expects.

Usage on the server:
    cd /var/www/base
    source venv/bin/activate
    python fix_review_tables.py
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.db import connection
from services.models import EventReview, EventReviewHelpful


def table_exists(name):
    return name in connection.introspection.table_names()


def main():
    created = []
    skipped = []
    with connection.schema_editor() as se:
        for model in (EventReview, EventReviewHelpful):
            tbl = model._meta.db_table
            if table_exists(tbl):
                skipped.append(tbl)
                continue
            se.create_model(model)
            created.append(tbl)

    if created:
        print("Created:", ", ".join(created))
    if skipped:
        print("Already existed (skipped):", ", ".join(skipped))
    if not created and not skipped:
        print("Nothing to do.")


if __name__ == "__main__":
    main()
