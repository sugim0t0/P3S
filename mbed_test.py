#!/usr/bin/env python

''' 3 tasks on mbed OS 5
'''

__version__ = "1.0"
__date__    = "4 Feb. 2017"
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

class TransAppMpFree(p3s.Trans):
    def sync(self):
        self.channel.recv() # ?mpool_free

class TransAppMemCopy(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.MP_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.MP_UNUSED -= 1
    def get_delay(self):
        return (2 + (mbed_conf.F_SIZE / 128))

class TransAppFqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == 0:
            return True
        else:
            return False

class TransAppFqFree(p3s.Trans):
    def sync(self):
        self.channel.recv() # ?fqueue_get

class TransAppQueuePut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.FQ_UNUSED -= 1
        self.proc.rest_of_frame -= 1
        self.channel.send(1, current_cycle) # !fqueue_put
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
        if super().guard(current_cycle) and self.proc.rest_of_frame == 0:
            return True
        else:
            return False
    def sync(self):
        self.channel.recv() # ?finish

class ApplicationTask(p3s.Process):
    def __init__(self, name):
        super().__init__(name)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# Checksum calculation task
class TransCksmFqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED == mbed_conf.FQ_MAX:
            return True
        else:
            return False

class TransCksmFqPut(p3s.Trans):
    def sync(self):
        self.channel.recv() # ?fqueue_put

class TransCksmCalc(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.FQ_UNUSED < mbed_conf.FQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.FQ_UNUSED += 1
        self.channel.send(1, current_cycle) # !fqueue_get
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
        self.channel.send(1, current_cycle) # !cqueue_put
    def get_delay(self):
        return 5

class TransCksmCqFull(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == 0:
            return True
        else:
            return False

class TransCksmCqFree(p3s.Trans):
    def sync(self):
        self.channel.recv() # ?cqueue_get

# Cleanup task
class TransClupCqNoPut(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED == mbed_conf.CQ_MAX:
            return True
        else:
            return False

class TransClupCqPut(p3s.Trans):
    def sync(self):
        self.channel.recv() # ?cqueue_put

class TransClupCqGet(p3s.Trans):
    def guard(self, current_cycle):
        if mbed_conf.CQ_UNUSED < mbed_conf.CQ_MAX:
            return True
        else:
            return False
    def update(self, current_cycle):
        mbed_conf.CQ_UNUSED += 1
        self.channel.send(1, current_cycle) # !cqueue_get
    def get_delay(self):
        return 5

class TransClupMpFree(p3s.Trans):
    def update(self, current_cycle):
        mbed_conf.MP_UNUSED += 1
        self.proc.rest_of_frame -= 1
        self.channel.send(1, current_cycle) # !mpool_free
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
        self.channel.send(1, current_cycle) # !finish

class CleanupTask(p3s.Process):
    def __init__(self, name):
        super().__init__(name)
        self.rest_of_frame = mbed_conf.NUM_OF_FRAME

# main
if __name__ == "__main__":
    # construct Sync channel
    ch_mpool_free = p3s.Channel("CH_MPOOL_FREE")
    ch_fqueue_get = p3s.Channel("CH_FQUEUE_GET")
    ch_fqueue_put = p3s.Channel("CH_FQUEUE_PUT")
    ch_cqueue_get = p3s.Channel("CH_CQUEUE_GET")
    ch_cqueue_put = p3s.Channel("CH_CQUEUE_PUT")
    ch_finish = p3s.Channel("CH_FINISH")

    # construct Application task model
    app_task = ApplicationTask("APP_TASK")
    app_loc1 = p3s.Location("APP_MPOOL_ALLOC", False)
    app_loc2 = p3s.Location("APP_WAIT_MPOOL_FREE", False)
    app_loc3 = p3s.Location("APP_FQ_PUT", False)
    app_loc4 = p3s.Location("APP_WAIT_FQ_GET", False)
    app_loc5 = p3s.Location("APP_JUDGE_END", False)
    app_loc6 = p3s.Location("APP_END", True)
    app_tr1 = TransAppMpFull(app_task, None, False, app_loc2)
    app_tr2 = TransAppMpFree(app_task, ch_mpool_free, False, app_loc1)
    app_tr3 = TransAppMemCopy(app_task, None, False, app_loc3)
    app_tr4 = TransAppFqFull(app_task, None, False, app_loc4)
    app_tr5 = TransAppFqFree(app_task, ch_fqueue_get, False, app_loc3)
    app_tr6 = TransAppQueuePut(app_task, ch_fqueue_put, True, app_loc5)
    app_tr7 = TransAppNextFrame(app_task, None, False, app_loc1)
    app_tr8 = TransAppFinish(app_task, ch_finish, False, app_loc6)
    app_loc1.add_trans(app_tr1)
    app_loc1.add_trans(app_tr3)
    app_loc2.add_trans(app_tr2)
    app_loc3.add_trans(app_tr4)
    app_loc3.add_trans(app_tr6)
    app_loc4.add_trans(app_tr5)
    app_loc5.add_trans(app_tr7)
    app_loc5.add_trans(app_tr8)
    app_task.add_location(app_loc1, True)
    app_task.add_location(app_loc2, False)
    app_task.add_location(app_loc3, False)
    app_task.add_location(app_loc4, False)
    app_task.add_location(app_loc5, False)
    app_task.add_location(app_loc6, False)

    # construct Checksum calculation task model
    cksm_task = p3s.Process("CKSM_TASK")
    cksm_loc1 = p3s.Location("CKSM_FQ_GET_CALC", False)
    cksm_loc2 = p3s.Location("CKSM_WAIT_FQ_PUT", False)
    cksm_loc3 = p3s.Location("CKSM_CQ_PUT", False)
    cksm_loc4 = p3s.Location("CKSM_WAIT_CQ_GET", False)
    cksm_tr1 = TransCksmFqNoPut(cksm_task, None, False, cksm_loc2)
    cksm_tr2 = TransCksmFqPut(cksm_task, ch_fqueue_put, False, cksm_loc1)
    cksm_tr3 = TransCksmCalc(cksm_task, ch_fqueue_get, True, cksm_loc3)
    cksm_tr4 = TransCksmNextFrame(cksm_task, ch_cqueue_put, True, cksm_loc1)
    cksm_tr5 = TransCksmCqFull(cksm_task, None, False, cksm_loc4)
    cksm_tr6 = TransCksmCqFree(cksm_task, ch_cqueue_get, False, cksm_loc3)
    cksm_loc1.add_trans(cksm_tr1)
    cksm_loc1.add_trans(cksm_tr3)
    cksm_loc2.add_trans(cksm_tr2)
    cksm_loc3.add_trans(cksm_tr4)
    cksm_loc3.add_trans(cksm_tr5)
    cksm_loc4.add_trans(cksm_tr6)
    cksm_task.add_location(cksm_loc1, True)
    cksm_task.add_location(cksm_loc2, False)
    cksm_task.add_location(cksm_loc3, False)
    cksm_task.add_location(cksm_loc4, False)

    # construct Cleanup task model
    clup_task = CleanupTask("CLUP_TASK")
    clup_loc1 = p3s.Location("CLUP_CQ_GET", False)
    clup_loc2 = p3s.Location("CLUP_WAIT_CQ_PUT", False)
    clup_loc3 = p3s.Location("CLUP_MPOOL_FREE", False)
    clup_loc4 = p3s.Location("CLUP_JUDGE_END", False)
    clup_loc5 = p3s.Location("CLUP_END", False)
    clup_tr1 = TransClupCqNoPut(clup_task, None, False, clup_loc2)
    clup_tr2 = TransClupCqPut(clup_task, ch_cqueue_put, False, clup_loc1)
    clup_tr3 = TransClupCqGet(clup_task, ch_cqueue_get, True, clup_loc3)
    clup_tr4 = TransClupMpFree(clup_task, ch_mpool_free, True, clup_loc4)
    clup_tr5 = TransClupNextFrame(clup_task, None, False, clup_loc1)
    clup_tr6 = TransClupFinish(clup_task, ch_finish, True, clup_loc5)
    clup_loc1.add_trans(clup_tr1)
    clup_loc1.add_trans(clup_tr3)
    clup_loc2.add_trans(clup_tr2)
    clup_loc3.add_trans(clup_tr4)
    clup_loc4.add_trans(clup_tr5)
    clup_loc4.add_trans(clup_tr6)
    clup_task.add_location(clup_loc1, True)
    clup_task.add_location(clup_loc2, False)
    clup_task.add_location(clup_loc3, False)
    clup_task.add_location(clup_loc4, False)
    clup_task.add_location(clup_loc5, False)

    # construct CPU model
    cpu = p3s.CPU_Model("CPU", mbed_conf.CPU_CLOCK, mbed_conf.TASK_SWITCH_DELAY)
    cpu.add_task(app_task, mbed_conf.APP_TASK_PRIORITY)
    cpu.add_task(cksm_task, mbed_conf.CKSM_TASK_PRIORITY)
    cpu.add_task(clup_task, mbed_conf.CLUP_TASK_PRIORITY)
    
    sim = p3s.P3S(1)
    sim.add_cpu(cpu)

    sim.simulate()

    print("Simulation End.")


