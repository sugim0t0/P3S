#!/usr/bin/env python

''' Define file of P3S lib
'''

from enum import Enum, IntEnum

class TaskState(Enum):
    INACTIVE = 0
    WAITING  = 1
    READY    = 2
    RUNNING  = 3

class TaskPriority(IntEnum):
    PRIORITY_IDLE     = -3
    PRIORITY_LOW      = -2
    PRIORITY_NORMAL   =  0
    PRIORITY_HIGH     =  2
    PRIORITY_REALTIME =  3 # for ISR (Interrupt Service Routine)

class TransState(Enum):
    TRANS_BEFORE_GET_DELAY = 1
    TRANS_BEFORE_UPDATE    = 2
    TRANS_AFTER_UPDATE     = 3

# Signal
SIGNAL_ID_NO_WAIT = -1
SIGNAL_INIT_PRI = -1

