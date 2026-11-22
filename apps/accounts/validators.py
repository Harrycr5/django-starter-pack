from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_birth_date(value):
    today = timezone.localdate()
    if value > today:
        raise ValidationError("La fecha de nacimiento no puede ser futura.")
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < settings.MINIMUM_AGE:
        raise ValidationError(f"La edad mínima es {settings.MINIMUM_AGE} años.")
