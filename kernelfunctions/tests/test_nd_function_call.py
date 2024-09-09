import pytest
from kernelfunctions.backend import DeviceType
from kernelfunctions.types import NDDifferentiableBuffer
import kernelfunctions.tests.helpers as helpers
import numpy as np


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_basic_3d_call(device_type: DeviceType):

    device = helpers.get_device(device_type)

    function = helpers.create_function_from_module(
        device,
        "add_numbers_nd",
        r"""
void add_numbers_nd(float a, float b, out float c) {
    c = a + b;
}
""",
    )

    a = NDDifferentiableBuffer(device, element_type=float, shape=(2, 2))
    b = NDDifferentiableBuffer(device, element_type=float, shape=(2, 2))
    c = NDDifferentiableBuffer(device, element_type=float, shape=(2, 2))

    # type: ignore (shape is a tuple)
    a_data = np.random.rand(*a.shape).astype(np.float32)
    # type: ignore (shape is a tuple)
    b_data = np.random.rand(*b.shape).astype(np.float32)

    a.buffer.from_numpy(a_data)
    b.buffer.from_numpy(b_data)

    function(a, b, c)

    c_expected = a_data + b_data
    c_data = c.buffer.to_numpy().view(np.float32).reshape(*c.shape)
    assert np.allclose(c_data, c_expected, atol=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
