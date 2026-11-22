from datetime import datetime

from django.db import models


from apps.common.utils import DATE_INPUT_FORMATS


class BirthDateField(models.DateField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip()
            for date_format in DATE_INPUT_FORMATS:
                try:
                    return datetime.strptime(value, date_format).date()
                except ValueError:
                    continue
        return super().to_python(value)

    def formfield(self, **kwargs):
        return super().formfield(input_formats=DATE_INPUT_FORMATS, **kwargs)
