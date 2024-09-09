from kernelfunctions.backend import BACKEND

if BACKEND == "SGL":
    from .sglmath import *

from .builtin import *
from .buffer import *
from .threadidarg import *
from .wanghasharg import *
from .randfloatarg import *
