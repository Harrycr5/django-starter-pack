from django.db import models
from django.utils import timezone

from .middleware import actor_id


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        if self.query.is_sliced or self._fields is not None or self.query.distinct_fields:
            raise TypeError("delete() requiere un QuerySet de modelos sin límites.")
        now = timezone.now()
        actor = actor_id()
        changes = {"is_active": False, "deleted_at": now, "deleted_by_id": actor}
        field_names = {field.name for field in self.model._meta.fields}
        if "updated_at" in field_names:
            changes["updated_at"] = now
        if actor is not None and "updated_by" in field_names:
            changes["updated_by_id"] = actor
        count = self.filter(is_active=True).update(**changes)
        return count, {self.model._meta.label: count} if count else {}

    delete.alters_data = True
    delete.queryset_only = True

    def hard_delete(self):
        return super().delete()

    hard_delete.alters_data = True
    hard_delete.queryset_only = True


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
