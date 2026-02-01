from enum import Enum

class Pattern(Enum):
    """
    Common workflow patterns.
    """
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MAP_REDUCE = "map_reduce"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    CONDITIONAL = "conditional"
