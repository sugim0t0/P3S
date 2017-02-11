#!/usr/bin/env python

''' Configuration file of P3S lib
'''

from enum import Enum, IntEnum

class TaskState(Enum):
    INACTIVE = 0
    WAITING  = 1
    READY    = 2
    RUNNING  = 3

class TaskPriority(IntEnum):
    PRIORITY_LOW    = 1
    PRIORITY_NORMAL = 2
    PRIORITY_HIGH   = 3

class TransState(Enum):
    TRANS_BEFORE_GET_DELAY = 1
    TRANS_BEFORE_UPDATE    = 2
    TRANS_AFTER_UPDATE     = 3

# Signal
SIGNAL_ID_NO_WAIT = -1
SIGNAL_INIT_PRI = -1

