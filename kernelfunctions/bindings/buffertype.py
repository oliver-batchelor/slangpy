

from typing import Any, Optional, Sequence

from kernelfunctions.bindings.diffpairtype import generate_differential_pair
from kernelfunctions.core import CodeGenBlock, BaseType, BaseTypeImpl, BaseVariable, AccessType, PrimType

from kernelfunctions.types import NDBuffer, NDDifferentiableBuffer

from kernelfunctions.backend import Device, ResourceUsage
from kernelfunctions.typeregistry import PYTHON_TYPES, get_or_create_type


class NDBufferType(BaseTypeImpl):

    def __init__(self, element_type: BaseType):
        super().__init__()
        self.el_type = element_type

    # Values don't store a derivative - they're just a value
    def has_derivative(self, value: Any = None) -> bool:
        return False

    # Refs can be written to!
    def is_writable(self, value: Optional[NDBuffer] = None) -> bool:
        if value is not None:
            return (value.usage & ResourceUsage.unordered_access) != 0
        else:
            return True  # to be allocated later for write!

    # Call data can only be read access to primal, and simply declares it as a variable
    def gen_calldata(self, cgb: CodeGenBlock, input_value: 'BaseVariable', name: str, transform: list[Optional[int]], access: tuple[AccessType, AccessType]):
        assert access[0] != AccessType.none
        assert access[1] == AccessType.none
        if access[0] == AccessType.read:
            cgb.type_alias(
                f"_{name}", f"NDBuffer<{input_value.primal_element_name},{len(transform)}>")
        else:
            cgb.type_alias(
                f"_{name}", f"RWTensorBuffer<{input_value.primal_element_name},{len(transform)}>")

    # Call data just returns the primal

    def create_calldata(self, device: Device, input_value: 'BaseVariable', access: tuple[AccessType, AccessType], data: NDBuffer) -> Any:
        assert access[0] != AccessType.none
        assert access[1] == AccessType.none
        return {
            'buffer': data.buffer,
            'strides': list(data.strides),
            'transform': input_value.binding.loadstore_transform
        }

    # Read back from call data does nothing
    def read_calldata(self, device: Device, input_value: 'BaseVariable', access: tuple[AccessType, AccessType], data: NDBuffer, result: Any) -> None:
        pass

    def name(self, value: Any = None) -> str:
        if value is not None:
            if self.is_writable(value):
                return f"NDBuffer<{self.el_type.name()}>"
            else:
                return f"RWTensorBuffer<{self.el_type.name()}>"
        else:
            return "UnknownBufferName"

    def element_type(self, value: Optional[NDBuffer] = None):
        return self.el_type

    def container_shape(self, value: Optional[NDBuffer] = None):
        if value is not None:
            return value.shape
        else:
            return None

    def shape(self, value: Any = None):
        if value is not None:
            return super().shape(value)
        else:
            return None

    def differentiable(self, value: Optional[NDBuffer] = None):
        return self.el_type.differentiable()

    def differentiate(self, value: Optional[NDBuffer] = None):
        et = self.el_type.differentiate()
        if et is not None:
            return NDBufferType(et)
        else:
            return None

    def create_output(self, device: Device, call_shape: Sequence[int]) -> Any:
        return NDBuffer(device, self.el_type.python_return_value_type(), shape=tuple(call_shape), usage=ResourceUsage.shader_resource | ResourceUsage.unordered_access)

    def read_output(self, device: Device, data: NDDifferentiableBuffer) -> Any:
        return data


def create_vr_type_for_value(value: Any):
    assert isinstance(value, NDBuffer)
    return NDBufferType(get_or_create_type(value.element_type))


PYTHON_TYPES[NDBuffer] = create_vr_type_for_value


class NDDifferentiableBufferType(BaseTypeImpl):

    def __init__(self, element_type: BaseType):
        super().__init__()
        self.el_type = element_type

    # Values don't store a derivative - they're just a value
    def has_derivative(self, value: Any = None) -> bool:
        return True

    # Refs can be written to!
    def is_writable(self, value: Any = None) -> bool:
        if value is not None:
            return (value.usage & ResourceUsage.unordered_access) != 0
        else:
            return True  # to be allocated later for write!

    # Call data can only be read access to primal, and simply declares it as a variable
    def gen_calldata(self, cgb: CodeGenBlock, input_value: 'BaseVariable', name: str, transform: list[Optional[int]], access: tuple[AccessType, AccessType]):
        prim_el = input_value.primal_element_name
        deriv_el = input_value.derivative_element_name
        if deriv_el is None:
            deriv_el = prim_el
        dim = len(transform)

        binding = input_value.binding

        if access[0] == AccessType.none:
            primal_storage = f'NoneType'
        elif access[0] == AccessType.read:
            primal_storage = f"NDBuffer<{prim_el},{dim}>"
        else:
            primal_storage = f"RWTensorBuffer<{prim_el},{dim}>"

        if access[1] == AccessType.none:
            deriv_storage = f'NoneType'
        elif access[1] == AccessType.read:
            deriv_storage = f"NDBuffer<{deriv_el},{dim}>"
        else:
            deriv_storage = f"RWTensorBuffer<{deriv_el},{dim}>"

        primal_target = binding.slang.primal_type_name
        deriv_target = binding.slang.derivative_type_name

        cgb.append_code(generate_differential_pair(name, primal_storage,
                        deriv_storage, primal_target, deriv_target))

    # Call data just returns the primal

    def create_calldata(self, device: Device, input_value: 'BaseVariable', access: tuple[AccessType, AccessType], data: NDDifferentiableBuffer) -> Any:
        res = {}
        for prim in PrimType:
            prim_name = prim.name
            prim_access = access[prim.value]
            if prim_access != AccessType.none:
                ndbuffer = data if prim == PrimType.primal else data.grad
                assert ndbuffer is not None
                value = ndbuffer.buffer if prim == PrimType.primal else ndbuffer.buffer
                res[prim_name] = {
                    'buffer': value,
                    'strides': list(data.strides),
                    'transform': input_value.binding.loadstore_transform
                }
        return res

    # Read back from call data does nothing
    def read_calldata(self, device: Device, input_value: 'BaseVariable', access: tuple[AccessType, AccessType], data: NDDifferentiableBuffer, result: Any) -> None:
        pass

    def name(self, value: Optional[NDDifferentiableBuffer] = None) -> str:
        if value is not None:
            if self.is_writable(value):
                return f"NDBuffer<{self.el_type.name()}>"
            else:
                return f"RWTensorBuffer<{self.el_type.name()}>"
        else:
            return "UnknownBufferName"

    def element_type(self, value: Optional[NDDifferentiableBuffer] = None):
        return self.el_type

    def container_shape(self, value: Optional[NDDifferentiableBuffer] = None):
        if value is not None:
            return value.shape
        else:
            return None

    def shape(self, value: Any = None):
        if value is not None:
            return super().shape(value)
        else:
            return None

    def differentiable(self, value: Optional[NDBuffer] = None):
        return self.el_type.differentiable()

    def differentiate(self, value: Optional[NDBuffer] = None):
        et = self.el_type.differentiate()
        if et is not None:
            return NDDifferentiableBufferType(et)
        else:
            return None

    def create_output(self, device: Device, call_shape: Sequence[int]) -> Any:
        return NDDifferentiableBuffer(device, self.el_type.python_return_value_type(),
                                      shape=tuple(call_shape),
                                      requires_grad=True,
                                      usage=ResourceUsage.shader_resource | ResourceUsage.unordered_access)

    def read_output(self, device: Device, data: NDDifferentiableBuffer) -> Any:
        return data


def create_gradvr_type_for_value(value: Any):
    assert isinstance(value, NDDifferentiableBuffer)
    return NDDifferentiableBufferType(get_or_create_type(value.element_type))


PYTHON_TYPES[NDDifferentiableBuffer] = create_gradvr_type_for_value
