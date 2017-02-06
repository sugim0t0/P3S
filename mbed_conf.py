#!/usr/bin/env python

''' configuration of mbed_test.py
'''

# Constant parameters
NUM_OF_FRAME = 10
F_SIZE = 512 # Frame data size (bytes)
MP_MAX = 5
FQ_MAX = 5
CQ_MAX = 5

TASK_SWITCH_DELAY = 2
CPU_CLOCK = 96 # mbed LPC1758: 96MHz

# Task priorities
TP_LOW    = 1
TP_NORMAL = 2
TP_HIGH   = 3

APP_TASK_PRIORITY = TP_HIGH
CKSM_TASK_PRIORITY = TP_NORMAL
CLUP_TASK_PRIORITY = TP_LOW

# GLOVAL vars
MP_UNUSED = MP_MAX # Free size of Memory Pool
FQ_UNUSED = FQ_MAX # Free size of Frame Queue
CQ_UNUSED = CQ_MAX # Free size of Cleanup Queue

