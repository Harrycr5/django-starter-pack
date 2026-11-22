from uuid import uuid4

from django.conf import settings
from django.db import models

from .managers import ActiveManager, SoftDeleteQuerySet
from .middleware import actor_id
from .mixins import UppercaseFieldsMixin


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if not update_fields:
                return
            update_fields.add("updated_at")
        actor = actor_id()
        if actor is not None:
            if self._state.adding and self.created_by_id is None:
                self.created_by_id = actor
            self.updated_by_id = actor
            if update_fields is not None:
                update_fields.add("updated_by")
        if update_fields is not None:
            kwargs["update_fields"] = update_fields
        return super().save(*args, **kwargs)


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    objects = ActiveManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"
        default_manager_name = "objects"

    def delete(self, using=None, keep_parents=False):
        if self._state.adding or self.pk is None:
            raise ValueError("Guarda la instancia antes de borrarla.")
        queryset = type(self).all_objects
        if using is not None or self._state.db is not None:
            queryset = queryset.using(using or self._state.db)
        result = queryset.filter(pk=self.pk).delete()
        self.refresh_from_db(using=using)
        return result

    def restore(self, using=None):
        if self._state.adding or self.pk is None:
            raise ValueError("Guarda la instancia antes de restaurarla.")
        self.is_active = True
        self.deleted_at = None
        self.deleted_by_id = None
        self.save(using=using, update_fields=["is_active", "deleted_at", "deleted_by"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(UppercaseFieldsMixin, AuditModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta(SoftDeleteModel.Meta):
        abstract = True
