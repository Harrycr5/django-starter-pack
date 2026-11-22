from .utils import normalize_uppercase


class UppercaseSerializerMixin:
    def to_internal_value(self, data):
        if hasattr(data, "copy") and hasattr(data, "keys"):
            data = data.copy()
            for field in self.Meta.model.uppercase_fields:
                if field in data and field in self.fields:
                    data[field] = normalize_uppercase(data[field])
        return super().to_internal_value(data)
