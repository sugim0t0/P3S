
#import p3s
from P3S import p3s

# Global variable
sram_unused = 4 

# DMAC model
class TransRecvDmacStart(p3s.Trans):
    def sync(self):
        self.proc.s = self.channel.recv()
    def get_delay(self):
        return 10 + self.proc.s * 10

class TransSendDmacEnd(p3s.Trans):
    def update(self, current_cycle):
        self.channel.send(self.proc.s, current_cycle)

# INTC model
class TransRecvDmacEnd(p3s.Trans):
    def sync(self):
        self.proc.s = self.channel.recv()
    def update(self, current_cycle):
        self.proc.p += 1
        self.proc.e += 1

class TransSendIDmacEnd(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.e > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.e -= 1
        self.channel.send(1, current_cycle)

class TransSendIDataPrepared(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.p > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        self.proc.p -= 1
        self.channel.send(self.proc.s, current_cycle)
        self.proc.s = 0

class IntcProc(p3s.Process):
    def __init__(self, name):
        super().__init__(name)
        self.p = 0
        self.e = 0
        self.s = 0

# Data Transfer Task
class TransPrepareMalloc(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.d > 0:
            return True
        else:
            return False

class TransMalloc(p3s.Trans):
    def guard(self, current_cycle):
        global sram_unused
        if sram_unused > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        global sram_unused
        if sram_unused < self.proc.d:
            self.proc.s = sram_unused
        else:
            self.proc.s = self.proc.d
        sram_unused -= self.proc.s
    def get_delay(self):
        global sram_unused
        s = 0
        if sram_unused < self.proc.d:
            s = sram_unused
        else:
            s = self.proc.d
        return 10 + s * 5

class TransSendDmacStart(p3s.Trans):
    def update(self, current_cycle):
        self.channel.send(self.proc.s, current_cycle)

class TransRecvIDmacEnd(p3s.Trans):
    def sync(self):
        self.channel.recv()
    def update(self, current_cycle):
        self.proc.d -= self.proc.s

class DataTransferTask(p3s.Process):
    def __init__(self, name):
        super().__init__(name)
        self.d = 8
        self.s = 0

# Data Free Task
class TransRecvIDataPrepared(p3s.Trans):
    def guard(self, current_cycle):
        if super().guard(current_cycle) and self.proc.d > 0:
            return True
        else:
            return False
    def sync(self):
        self.proc.s = self.channel.recv()


class TransDataRead(p3s.Trans):
    def update(self, current_cycle):
        self.proc.d -= self.proc.s
    def get_delay(self):
        return 10 + self.proc.s * 5

class TransDataFree(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.s > 0:
            return True
        else:
            return False
    def update(self, current_cycle):
        global sram_unused
        sram_unused += 1
        self.proc.s -= 1
    def get_delay(self):
        return 5

class TransDataFreeEnd(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.s == 0:
            return True
        else:
            return False

class TransEndPoint(p3s.Trans):
    def guard(self, current_cycle):
        if self.proc.d == 0:
            return True
        else:
            return False

class DataFreeTask(p3s.Process):
    def __init__(self, name):
        super().__init__(name)
        self.d = 8
        self.s = 0

# main
if __name__ == "__main__":
    # construct Sync channel
    ch_dmac_start = p3s.Channel("CH_DMAC_START")
    ch_dmac_end = p3s.Channel("CH_DMAC_END")
    ch_i_dmac_end = p3s.Channel("CH_I_DMAC_END")
    ch_i_data_prepared = p3s.Channel("CH_I_DATA_PREPARED")

    # construct DMAC core model
    dmac_core = p3s.Process("DMAC_CORE")
    dmac_loc1 = p3s.Location("DMAC_WAIT", False)
    dmac_loc2 = p3s.Location("DMAC_TRANSFER", False)
    dmac_tr1 = TransRecvDmacStart(dmac_core, ch_dmac_start, False, dmac_loc2)
    dmac_tr2 = TransSendDmacEnd(dmac_core, ch_dmac_end, True, dmac_loc1)
    dmac_loc1.add_trans(dmac_tr1)
    dmac_loc2.add_trans(dmac_tr2)
    dmac_core.add_location(dmac_loc1, True)
    dmac_core.add_location(dmac_loc2, False)

    # construct INTC core model
    intc_core = IntcProc("INTC_CORE")
    intc_loc = p3s.Location("INTC_WAIT", False)
    intc_tr1 = TransRecvDmacEnd(intc_core, ch_dmac_end, False, intc_loc)
    intc_tr2 = TransSendIDmacEnd(intc_core, ch_i_dmac_end, True, intc_loc)
    intc_tr3 = TransSendIDataPrepared(intc_core, ch_i_data_prepared, True, intc_loc)
    intc_loc.add_trans(intc_tr1)
    intc_loc.add_trans(intc_tr2)
    intc_loc.add_trans(intc_tr3)
    intc_core.add_location(intc_loc, True)

    # construct Data Transfer Task model
    dtt_task = DataTransferTask("DTT")
    dtt_task_loc1 = p3s.Location("DTT_WAIT", False)
    dtt_task_loc2 = p3s.Location("DTT_MALLOC", False)
    dtt_task_loc3 = p3s.Location("DTT_START_DMA", False)
    dtt_task_loc4 = p3s.Location("DTT_WAIT_DMA_END", False)
    dtt_tr1 = TransPrepareMalloc(dtt_task, None, False, dtt_task_loc2)
    dtt_tr2 = TransMalloc(dtt_task, None, False, dtt_task_loc3)
    dtt_tr3 = TransSendDmacStart(dtt_task, ch_dmac_start, True, dtt_task_loc4)
    dtt_tr4 = TransRecvIDmacEnd(dtt_task, ch_i_dmac_end, False, dtt_task_loc1)
    dtt_task_loc1.add_trans(dtt_tr1)
    dtt_task_loc2.add_trans(dtt_tr2)
    dtt_task_loc3.add_trans(dtt_tr3)
    dtt_task_loc4.add_trans(dtt_tr4)
    dtt_task.add_location(dtt_task_loc1, True)
    dtt_task.add_location(dtt_task_loc2, False)
    dtt_task.add_location(dtt_task_loc3, False)
    dtt_task.add_location(dtt_task_loc4, False)

    # construct Data Free Task model
    dft_task = DataFreeTask("DFT")
    dft_task_loc1 = p3s.Location("DFT_WAIT", False)
    dft_task_loc2 = p3s.Location("DFT_READ_DATA", False)
    dft_task_loc3 = p3s.Location("DFT_FREE_DATA", False)
    dft_task_loc4 = p3s.Location("DFT_END_POINT", True)
    dft_tr1 = TransRecvIDataPrepared(dft_task, ch_i_data_prepared, False, dft_task_loc2)
    dft_tr2 = TransDataRead(dft_task, None, False, dft_task_loc3)
    dft_tr3 = TransDataFree(dft_task, None, False, dft_task_loc3)
    dft_tr4 = TransDataFreeEnd(dft_task, None, False, dft_task_loc1)
    dft_tr5 = TransEndPoint(dft_task, None, False, dft_task_loc4)
    dft_task_loc1.add_trans(dft_tr1)
    dft_task_loc1.add_trans(dft_tr5)
    dft_task_loc2.add_trans(dft_tr2)
    dft_task_loc3.add_trans(dft_tr3)
    dft_task_loc3.add_trans(dft_tr4)
    dft_task.add_location(dft_task_loc1, True)
    dft_task.add_location(dft_task_loc2, False)
    dft_task.add_location(dft_task_loc3, False)
    dft_task.add_location(dft_task_loc4, False)

    # construct DMAC HW model
    dmac = p3s.HW_Model("DMAC", 200, dmac_core)
    # construct INTC HW model
    intc = p3s.HW_Model("INTC", 200, intc_core)
    # construct CPU model
    cpu = p3s.CPU_Model("CPU", 200, 3)
    cpu.add_task(dtt_task, 3)
    cpu.add_task(dft_task, 2)
    
    sim = p3s.P3S(1)
    sim.add_cpu(cpu)
    sim.add_hw(dmac)
    sim.add_hw(intc)

    sim.simulate()

    print("Simulation End.")


