from typing import list
from dialoguekit.plugins.hooks import SchemaProvider


class EcommerceSchemaProvider(SchemaProvider):
    def get_object_types(self) -> list[str]:
        return ["order", "product"]