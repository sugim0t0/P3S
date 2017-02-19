#!/usr/bin/env python

''' 3 tasks and 1 ISR on mbed OS 5
    and 1 core H/W model on another mbed OS 5
'''

__version__ = "1.0"
__date__    = "19 Feb. 2017"
__author__  = "Shun SUGIMOTO <sugimoto.shun@gmail.com>"

# import p3s
from P3S import p3s
from P3S import cfg_p3s

# import configuration
import mbed_conf

# signal update
def wait_signal_update(task, sig_id, delay):
    task.signal.wait_signal(task, sig_id)
    task.cpu.current_task = None
    task.cpu.rest_task_cycle = delay

def set_signal_update(task, dst_task, sig_id, delay):
    b_changed = task.signal.set_signal(dst_task, sig_id)
    task.task_state = cfg_p3s.TaskState.READY
    task.cpu.current_task = None
    task.cpu.rest_task_cycle = delay

def set_signal_update_from_isr(isr, dst_task, sig_id, delay):
    b_changed = isr.signal.set_signal(dst_task, sig_id)
    isr.cpu.rest_isr_cycle = mbed_conf.ISR_OVERHEAD

# Application task
class TransAppMpFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.MP_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_MPOOL_FREE, mbed_conf.WAIT_SIG_DELAY)
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
        return (mbed_conf.F_SIZE / 128)

class TransAppFqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_FQUEUE_GET, mbed_conf.WAIT_SIG_DELAY)
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
        set_signal_update(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_FQUEUE_PUT, mbed_conf.SET_SIG_DELAY)
        return True
    def get_delay(self):
        return mbed_conf.DELAY_UNIT

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
        self.proc.task_state = cfg_p3s.TaskState.INACTIVE
        self.proc.cpu.rest_task_cycle = 3 # Task switch delay
        self.proc.cpu.current_task = None
        return False

class ApplicationTask(p3s.Task):
    def __init__(self, name, priority):
        super().__init__(name, priority)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# Checksum driver task
class TransCksmFqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == mbed_conf.FQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_FQUEUE_PUT, mbed_conf.WAIT_SIG_DELAY)
        return True

class TransCksmFqGet(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED < mbed_conf.FQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.FQ_UNUSED += 1
        set_signal_update(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_FQUEUE_GET, mbed_conf.SET_SIG_DELAY)
        return True
    def get_delay(self):
        return mbed_conf.DELAY_UNIT

class TransCksmKick(p3s.Trans):
    def update(self, current_cycle):
        self.channel.send(1, current_cycle, mbed_conf.CH_SEND_DELAY) # Checksum calc. request to H/W
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_CALC_FINISHED, mbed_conf.WAIT_SIG_DELAY)
        return True

class TransCksmNextFrame(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.CQ_UNUSED -= 1
        set_signal_update(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_CQUEUE_PUT, mbed_conf.SET_SIG_DELAY)
        return True
    def get_delay(self):
        return mbed_conf.DELAY_UNIT

class TransCksmCqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_CQUEUE_GET, mbed_conf.WAIT_SIG_DELAY)
        return True

# Cleanup task
class TransClupCqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == mbed_conf.CQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        wait_signal_update(self.proc, mbed_conf.SignalID.SIGNAL_CQUEUE_PUT, mbed_conf.WAIT_SIG_DELAY)
        return True

class TransClupCqGet(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED < mbed_conf.CQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.CQ_UNUSED += 1
        set_signal_update(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_CQUEUE_GET, mbed_conf.SET_SIG_DELAY)
        return True
    def get_delay(self):
        return mbed_conf.DELAY_UNIT

class TransClupMpFree(p3s.Trans):
    def update(self, current_cycle):
        mbed_conf.MP_UNUSED += 1
        self.proc.rest_of_frame -= 1
        set_signal_update(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_MPOOL_FREE, mbed_conf.SET_SIG_DELAY)
        return True
    def get_delay(self):
        return mbed_conf.DELAY_UNIT

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

class CleanupTask(p3s.Task):
    def __init__(self, name, priority):
        super().__init__(name, priority)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# Checksum calc. ISR
class TransIsrInterrupt(p3s.Trans):
    def sync(self):
        data = self.channel.recv()
    def update(self, current_cycle):
        set_signal_update_from_isr(self.proc, self.sig_task, mbed_conf.SignalID.SIGNAL_CALC_FINISHED, mbed_conf.SET_SIG_DELAY)
        # ISR operation is finished
        self.proc.b_finished = True
        return False

# Checksum calc. H/W
class TransHwRecvReq(p3s.Trans):
    def sync(self):
        data = self.channel.recv()

class TransHwCalc(p3s.Trans):
    def get_delay(self):
        return (3 * (mbed_conf.F_SIZE / 128))
    def update(self, current_cycle):
        self.channel.send(1, current_cycle, mbed_conf.CH_SEND_DELAY)

# main
if __name__ == "__main__":

    app_task = ApplicationTask("APP_TASK", mbed_conf.APP_TASK_PRIORITY)
    cksm_task = p3s.Task("CKSM_TASK", mbed_conf.CKSM_TASK_PRIORITY)
    clup_task = CleanupTask("CLUP_TASK", mbed_conf.CLUP_TASK_PRIORITY)
    cksm_isr = p3s.ISR("CKSM_ISR", cfg_p3s.TaskPriority.PRIORITY_REALTIME)
    cksm_hw_core = p3s.Process("CKSM_HW")

    # channel
    ch_start_cksm = p3s.Channel("CH_START_CKSM")
    ch_finish_cksm = p3s.Channel("CH_FINISH_CKSM")

    # construct Application task model
    app_loc1 = p3s.Location("APP_MPOOL_ALLOC", False)
    app_loc2 = p3s.Location("APP_FQ_PUT", False)
    app_loc3 = p3s.Location("APP_JUDGE_END", False)
    app_loc4 = p3s.Location("APP_END", False)
    app_tr1 = TransAppMpFull(app_task, None, False, app_loc1, None)
    app_tr2 = TransAppMemCopy(app_task, None, False, app_loc2, None)
    app_tr3 = TransAppFqFull(app_task, None, False, app_loc2, None)
    app_tr4 = TransAppQueuePut(app_task, None, False, app_loc3, cksm_task)
    app_tr5 = TransAppNextFrame(app_task, None, False, app_loc1, None)
    app_tr6 = TransAppFinish(app_task, None, False, app_loc4, None)
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
    cksm_loc1 = p3s.Location("CKSM_FQ_GET", False)
    cksm_loc2 = p3s.Location("CKSM_CALC", False)
    cksm_loc3 = p3s.Location("CKSM_CQ_PUT", False)
    cksm_tr1 = TransCksmFqNoPut(cksm_task, None, False, cksm_loc1, None)
    cksm_tr2 = TransCksmFqGet(cksm_task, None, False, cksm_loc2, app_task)
    cksm_tr3 = TransCksmKick(cksm_task, ch_start_cksm, True, cksm_loc3, cksm_isr)
    cksm_tr4 = TransCksmNextFrame(cksm_task, None, False, cksm_loc1, clup_task)
    cksm_tr5 = TransCksmCqFull(cksm_task, None, False, cksm_loc3, None)
    cksm_loc1.add_trans(cksm_tr1)
    cksm_loc1.add_trans(cksm_tr2)
    cksm_loc2.add_trans(cksm_tr3)
    cksm_loc3.add_trans(cksm_tr4)
    cksm_loc3.add_trans(cksm_tr5)
    cksm_task.add_location(cksm_loc1, True)
    cksm_task.add_location(cksm_loc2, False)
    cksm_task.add_location(cksm_loc3, False)

    # construct Cleanup task model
    clup_loc1 = p3s.Location("CLUP_CQ_GET", False)
    clup_loc2 = p3s.Location("CLUP_MPOOL_FREE", False)
    clup_loc3 = p3s.Location("CLUP_JUDGE_END", False)
    clup_loc4 = p3s.Location("CLUP_END", True)
    clup_tr1 = TransClupCqNoPut(clup_task, None, False, clup_loc1, None)
    clup_tr2 = TransClupCqGet(clup_task, None, False, clup_loc2, cksm_task)
    clup_tr3 = TransClupMpFree(clup_task, None, False, clup_loc3, app_task)
    clup_tr4 = TransClupNextFrame(clup_task, None, False, clup_loc1, None)
    clup_tr5 = TransClupFinish(clup_task, None, False, clup_loc4, None)
    clup_loc1.add_trans(clup_tr1)
    clup_loc1.add_trans(clup_tr2)
    clup_loc2.add_trans(clup_tr3)
    clup_loc3.add_trans(clup_tr4)
    clup_loc3.add_trans(clup_tr5)
    clup_task.add_location(clup_loc1, True)
    clup_task.add_location(clup_loc2, False)
    clup_task.add_location(clup_loc3, False)
    clup_task.add_location(clup_loc4, False)

    # construct checksum ISR model
    isr_loc1 = p3s.Location("ISR_INIT", False)
    isr_tr1 = TransIsrInterrupt(cksm_isr, ch_finish_cksm, False, isr_loc1, cksm_task)
    isr_loc1.add_trans(isr_tr1)
    cksm_isr.add_location(isr_loc1, True)

    # construct CPU model
    cpu = p3s.CPU_Model("CPU", mbed_conf.CPU_CLOCK)
    cpu.add_task(app_task)
    cpu.add_task(cksm_task)
    cpu.add_task(clup_task)
    cpu.add_isr(cksm_isr)

    # construct checksum H/W model
    cksm_hw_loc1 = p3s.Location("CKSM_HW_WAIT_REQ", False)
    cksm_hw_loc2 = p3s.Location("CKSM_HW_CALC", False)
    cksm_hw_tr1 = TransHwRecvReq(cksm_hw_core, ch_start_cksm, False, cksm_hw_loc2, None)
    cksm_hw_tr2 = TransHwCalc(cksm_hw_core, ch_finish_cksm, True, cksm_hw_loc1, None)
    cksm_hw_loc1.add_trans(cksm_hw_tr1)
    cksm_hw_loc2.add_trans(cksm_hw_tr2)
    cksm_hw_core.add_location(cksm_hw_loc1, True)
    cksm_hw_core.add_location(cksm_hw_loc2, False)
    cksm_hw = p3s.HW_Model("CKSM_HW", mbed_conf.CPU_CLOCK, cksm_hw_core) 
    
    sim = p3s.P3S(1)
    sim.add_cpu(cpu)
    sim.add_hw(cksm_hw)

    sim.simulate()

    print("Simulation End.")


