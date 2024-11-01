from typing import Any

from kernelfunctions.core import BaseType, Shape

from kernelfunctions.backend import TypeReflection
from kernelfunctions.core.basetype import BindContext
from kernelfunctions.typeregistry import PYTHON_TYPES
import kernelfunctions.typeregistry as tr

from .valuetype import ValueType


class StructType(ValueType):

    def __init__(self, struct_name: str, fields: dict[str, BaseType]):
        super().__init__()
        self.name = struct_name
        self.concrete_shape = Shape()
        self._fields = fields

    @property
    def differentiable(self):
        return True

    @property
    def derivative(self):
        return self

    @property
    def has_derivative(self) -> bool:
        return True

    @property
    def is_writable(self) -> bool:
        return True

    @property
    def fields(self):
        return self._fields

    def resolve_type(self, context: BindContext, bound_type: 'BaseType'):
        return bound_type


def create_vr_type_for_value(value: dict[str, Any]):
    assert isinstance(value, dict)
    fields = {name: tr.get_or_create_type(type(val), val) for name, val in value.items()}
    return StructType("dict", fields)


PYTHON_TYPES[dict] = create_vr_type_for_value


def _get_or_create_slang_type_reflection(slang_type: TypeReflection) -> BaseType:
    assert isinstance(slang_type, TypeReflection)
    assert slang_type.kind == TypeReflection.Kind.struct
    fields = {field.name: tr.get_or_create_type(
        field.type) for field in slang_type.fields}
    return StructType(slang_type.full_name, fields)


tr.SLANG_STRUCT_BASE_TYPE = _get_or_create_slang_type_reflection
