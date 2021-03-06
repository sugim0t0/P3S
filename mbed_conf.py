#!/usr/bin/env python

''' configuration of mbed_test.py
'''

from P3S import define_p3s
from enum import IntEnum

# Constant parameters
NUM_OF_FRAME = 10
F_SIZE = 512 # Frame data size (bytes)
MP_MAX = 3
FQ_MAX = 3
CQ_MAX = 3

CPU_CLOCK = 96 # mbed LPC1758: 96MHz
WAIT_SIG_DELAY = 3 # Task switch delay by wait_signal
SET_SIG_DELAY  = 3 # delay by set_signal
CH_SEND_DELAY  = 5 # delay by send channel
ISR_OVERHEAD   = 7
DELAY_UNIT     = 3

APP_TASK_PRIORITY  = define_p3s.TaskPriority.PRIORITY_LOW
CKSM_TASK_PRIORITY = define_p3s.TaskPriority.PRIORITY_NORMAL
CLUP_TASK_PRIORITY = define_p3s.TaskPriority.PRIORITY_HIGH

class SignalID(IntEnum):
    SIGNAL_MPOOL_FREE    = 1
    SIGNAL_FQUEUE_GET    = 2
    SIGNAL_FQUEUE_PUT    = 3
    SIGNAL_CQUEUE_GET    = 4
    SIGNAL_CQUEUE_PUT    = 5
    SIGNAL_CALC_FINISHED = 6
    SIGNAL_FINISH        = 7

# GLOBAL vars
MP_UNUSED = MP_MAX # Free size of Memory Pool
FQ_UNUSED = FQ_MAX # Free size of Frame Queue
CQ_UNUSED = CQ_MAX # Free size of Cleanup Queue

