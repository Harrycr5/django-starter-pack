from types import SimpleNamespace

import pytest
from django.db import connection, models

from apps.common.middleware import AuditMiddleware
from apps.common.models import BaseModel


class Record(BaseModel):
    class Meta(BaseModel.Meta):
        app_label = "starter_tests"
        db_table = "starter_tests_record"


@pytest.fixture
def record_table(transactional_db):
    with connection.schema_editor() as schema:
        schema.create_model(Record)
    try:
        yield
    finally:
        with connection.schema_editor() as schema:
            schema.delete_model(Record)


def test_soft_delete_restore_and_audit(record_table, user):
    def exercise(request):
        record = Record.objects.create()
        assert record.pk.version == 4
        assert record.created_by_id == user.pk
        assert record.delete()[0] == 1
        assert not Record.objects.filter(pk=record.pk).exists()
        assert record.deleted_by_id == user.pk and record.deleted_at is not None

        record.restore()
        restored = Record.objects.get(pk=record.pk)
        assert restored.updated_by_id == user.pk and restored.deleted_at is None
        assert Record.objects.filter(pk=record.pk).delete()[0] == 1
        assert not Record.objects.filter(pk=record.pk).exists()
        Record.all_objects.filter(pk=record.pk).hard_delete()
        assert not Record.all_objects.filter(pk=record.pk).exists()

    AuditMiddleware(exercise)(SimpleNamespace(user=user))
