

from typing import Any, Optional
from kernelfunctions.function import Function, FunctionChainBase
from kernelfunctions.struct import Struct


class Instance:
    def __init__(self, struct: Struct, data: Optional[Any] = None):
        super().__init__()
        if data is None:
            data = {}
        self._loaded_functions: dict[str, FunctionChainBase] = {}
        self.set_data(data)
        self._struct = struct
        self._init = self._try_load_func("__init")

    def set_data(self, data: Any):
        self._data = data

    def get_this(self) -> Any:
        return self._data

    def update_this(self, value: Any) -> None:
        pass

    def construct(self, *args: Any, **kwargs: Any) -> Any:
        if self._init is not None:
            self._init(*args, **kwargs, _result=self.get_this())

    def __getattr__(self, name: str) -> Any:
        if name in self._loaded_functions:
            return self._loaded_functions[name]

        if isinstance(self._data, dict) and name in self._struct.fields:
            return self._data.get(name)

        func = self._try_load_func(name)
        if func is not None:
            return func

        raise AttributeError(
            f"Instance of '{self._struct.name}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ['_data', '_struct', '_loaded_functions', '_init']:
            return super().__setattr__(name, value)
        if isinstance(self._data, dict) and name in self._struct.fields:
            self._data[name] = value
        raise AttributeError(
            f"Instance of '{self._struct.name}' has no attribute '{name}'")

    def _try_load_func(self, name: str):
        try:
            func = getattr(self._struct, name)
            if isinstance(func, Function):
                if name != "__init":
                    func = func.instance(self)
                self._loaded_functions[name] = func
                return func
        except AttributeError as e:
            return None
