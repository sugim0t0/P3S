#!/usr/bin/env python

''' 3 tasks on mbed OS 5
'''

__version__ = "1.1"
__date__    = "8 Feb. 2017"
__author__  = "Shun SUGIMOTO <sugimoto.shun@gmail.com>"

# import p3s
from P3S import p3s

# import configuration
import mbed_conf

# Application task
class TransAppMpFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.MP_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_MPOOL_FREE)
        return True

class TransAppMemCopy(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.MP_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.MP_UNUSED -= 1
        return False
    def get_delay(self):
        return (2 + (mbed_conf.F_SIZE / 128))

class TransAppFqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_FQUEUE_GET)
        return True

class TransAppQueuePut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.FQ_UNUSED -= 1
        self.proc.rest_of_frame -= 1
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_FQUEUE_PUT)
        return True
    def get_delay(self):
        return 7

class TransAppNextFrame(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.rest_of_frame > 0:
            return True
        else:
            return False

class TransAppFinish(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.rest_of_frame == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_FINISH)
        return True

class ApplicationTask(p3s.Task):
    def __init__(self, name, priority, signal):
        super().__init__(name, priority, signal)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# Checksum calculation task
class TransCksmFqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == mbed_conf.FQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_FQUEUE_PUT)
        return True

class TransCksmCalc(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED < mbed_conf.FQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.FQ_UNUSED += 1
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_FQUEUE_GET)
        return True
    def get_delay(self):
        return (6 + 3 * (mbed_conf.F_SIZE / 128))

class TransCksmNextFrame(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.CQ_UNUSED -= 1
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_CQUEUE_PUT)
        return True
    def get_delay(self):
        return 5

class TransCksmCqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_CQUEUE_GET)
        return True

# Cleanup task
class TransClupCqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == mbed_conf.CQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.wait_signal(self.proc, mbed_conf.SignalID.SIGNAL_CQUEUE_PUT)
        return True

class TransClupCqGet(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED < mbed_conf.CQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.CQ_UNUSED += 1
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_CQUEUE_GET)
        return True
    def get_delay(self):
        return 5

class TransClupMpFree(p3s.Trans):
    def update(self, current_cycle):
        mbed_conf.MP_UNUSED += 1
        self.proc.rest_of_frame -= 1
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_MPOOL_FREE)
        return True
    def get_delay(self):
        return 4

class TransClupNextFrame(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.rest_of_frame > 0:
            return True
        else:
            return False

class TransClupFinish(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.rest_of_frame == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.signal.set_signal(mbed_conf.SignalID.SIGNAL_FINISH)
        return True

class CleanupTask(p3s.Task):
    def __init__(self, name, priority, signal):
        super().__init__(name, priority, signal)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# main
if __name__ == "__main__":
    # construct signal
    signal = p3s.Signal()

    # construct Application task model
    app_task = ApplicationTask("APP_TASK", mbed_conf.APP_TASK_PRIORITY, signal)
    app_loc1 = p3s.Location("APP_MPOOL_ALLOC", False)
    app_loc2 = p3s.Location("APP_FQ_PUT", False)
    app_loc3 = p3s.Location("APP_JUDGE_END", False)
    app_loc4 = p3s.Location("APP_END", True)
    app_tr1 = TransAppMpFull(app_task, None, False, app_loc1)
    app_tr2 = TransAppMemCopy(app_task, None, False, app_loc2)
    app_tr3 = TransAppFqFull(app_task, None, False, app_loc2)
    app_tr4 = TransAppQueuePut(app_task, None, False, app_loc3)
    app_tr5 = TransAppNextFrame(app_task, None, False, app_loc1)
    app_tr6 = TransAppFinish(app_task, None, False, app_loc4)
    app_loc1.add_trans(app_tr1)
    app_loc1.add_trans(app_tr2)
    app_loc2.add_trans(app_tr3)
    app_loc2.add_trans(app_tr4)
    app_loc3.add_trans(app_tr5)
    app_loc3.add_trans(app_tr6)
    app_task.add_location(app_loc1, True)
    app_task.add_location(app_loc2, False)
    app_task.add_location(app_loc3, False)
    app_task.add_location(app_loc4, False)

    # construct Checksum calculation task model
    cksm_task = p3s.Task("CKSM_TASK", mbed_conf.CKSM_TASK_PRIORITY, signal)
    cksm_loc1 = p3s.Location("CKSM_FQ_GET_CALC", False)
    cksm_loc2 = p3s.Location("CKSM_CQ_PUT", False)
    cksm_tr1 = TransCksmFqNoPut(cksm_task, None, False, cksm_loc1)
    cksm_tr2 = TransCksmCalc(cksm_task, None, False, cksm_loc2)
    cksm_tr3 = TransCksmNextFrame(cksm_task, None, False, cksm_loc1)
    cksm_tr4 = TransCksmCqFull(cksm_task, None, False, cksm_loc2)
    cksm_loc1.add_trans(cksm_tr1)
    cksm_loc1.add_trans(cksm_tr2)
    cksm_loc2.add_trans(cksm_tr3)
    cksm_loc2.add_trans(cksm_tr4)
    cksm_task.add_location(cksm_loc1, True)
    cksm_task.add_location(cksm_loc2, False)

    # construct Cleanup task model
    clup_task = CleanupTask("CLUP_TASK", mbed_conf.CLUP_TASK_PRIORITY, signal)
    clup_loc1 = p3s.Location("CLUP_CQ_GET", False)
    clup_loc2 = p3s.Location("CLUP_MPOOL_FREE", False)
    clup_loc3 = p3s.Location("CLUP_JUDGE_END", False)
    clup_tr1 = TransClupCqNoPut(clup_task, None, False, clup_loc1)
    clup_tr2 = TransClupCqGet(clup_task, None, False, clup_loc2)
    clup_tr3 = TransClupMpFree(clup_task, None, False, clup_loc3)
    clup_tr4 = TransClupNextFrame(clup_task, None, False, clup_loc1)
    clup_tr5 = TransClupFinish(clup_task, None, False, clup_loc1)
    clup_loc1.add_trans(clup_tr1)
    clup_loc1.add_trans(clup_tr2)
    clup_loc2.add_trans(clup_tr3)
    clup_loc3.add_trans(clup_tr4)
    clup_loc3.add_trans(clup_tr5)
    clup_task.add_location(clup_loc1, True)
    clup_task.add_location(clup_loc2, False)
    clup_task.add_location(clup_loc3, False)

    # Add tasks to signal
    signal.add_signal_task(app_task)
    signal.add_signal_task(cksm_task)
    signal.add_signal_task(clup_task)

    # construct CPU model
    cpu = p3s.CPU_Model("CPU", mbed_conf.CPU_CLOCK, mbed_conf.TASK_SWITCH_DELAY)
    cpu.add_task(app_task)
    cpu.add_task(cksm_task)
    cpu.add_task(clup_task)
    
    sim = p3s.P3S(1)
    sim.add_cpu(cpu)

    sim.simulate()

    print("Simulation End.")


