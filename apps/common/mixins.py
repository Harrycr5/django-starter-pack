from .utils import normalize_uppercase


class UppercaseFieldsMixin:
    uppercase_fields = ()

    def _normalize_uppercase_fields(self):
        for field in self.uppercase_fields:
            setattr(self, field, normalize_uppercase(getattr(self, field)))

    def clean(self):
        self._normalize_uppercase_fields()
        super().clean()

    def save(self, *args, **kwargs):
        self._normalize_uppercase_fields()
        return super().save(*args, **kwargs)
