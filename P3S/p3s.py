#!/usr/bin/env python

''' P3S (Parallel Process Performance Simulator)

 Modification History:
 ===========================================================
 Date           Version   Description
 ===========================================================
 19 Feb. 2017   1.4       Add ISR class
 11 Feb. 2017   1.3       Signal belonged to Task
  9 Feb. 2017   1.2       Add Signal class
  6 Feb. 2017   1.1       Change send channel time from sync to update
 15 Jan. 2017   1.0       Creation
 -----------------------------------------------------------
'''

__version__ = "1.4"
__date__    = "19 Feb. 2017"
__author__  = "Shun SUGIMOTO <sugimoto.shun@gmail.com>"

from P3S import define_p3s

class Process():

    def __init__(self, name):
        '''
        Constructor of Process class.
            [1] name : Name of Process class object
        '''
        self.name = name
        self.locations = []
        self.current_loc = None
        self.current_trans = None
        self.trans_state = None
        self.b_finished = False

    def add_location(self, loc, b_init):
        '''
        Add new location to this Process.
            [1] loc    : Location class object
            [2] b_init : Whether this location is initial location
        '''
        self.locations.append(loc)
        if b_init:
            self.current_loc = loc

    def restart(self, global_cycle, accuracy_cycle):
        '''
        Restart this Process.
        Return value is rest of runnable cycle
            [1] global_cycle   : Current cycle
            [2] accuracy_cycle : Accuracy cycle (runnable cycle)
        '''
        runnable_cycle = accuracy_cycle
        if self.current_loc == None:
            return -1
        # State transition loop
        while True:
            if self.current_trans == None:
                for trans in self.current_loc.transitions:
                    if trans.guard(global_cycle+(accuracy_cycle-runnable_cycle)):
                        trans.sync()
                        self.current_trans = trans
                        self.trans_state = define_p3s.TransState.TRANS_BEFORE_GET_DELAY
                        break
                else: # There is no transition to be able
                    return runnable_cycle
            if self.trans_state == define_p3s.TransState.TRANS_BEFORE_GET_DELAY:
                self.current_trans.rest_cycle = self.current_trans.get_delay()
                self.trans_state = define_p3s.TransState.TRANS_BEFORE_UPDATE
                if self.current_trans.rest_cycle < 0:
                    return -1
            if runnable_cycle >= 0:
                if self.current_trans.rest_cycle > runnable_cycle:
                    self.current_trans.rest_cycle -= runnable_cycle
                    return 0
                else:
                    runnable_cycle -= self.current_trans.rest_cycle
                    self.current_trans.rest_cycle = 0
            if self.trans_state == define_p3s.TransState.TRANS_BEFORE_UPDATE:
                self.current_trans.update(global_cycle+(accuracy_cycle-runnable_cycle))
                self.trans_state = define_p3s.TransState.TRANS_AFTER_UPDATE
            self.current_loc = self.current_trans.to_location
            print("@" + self.name + " C:{0} : change location to ".format(global_cycle+(accuracy_cycle-runnable_cycle)) + self.current_loc.name)
            self.current_trans = None
            self.trans_state = None
            if self.current_loc.b_end:
                self.b_finished = True
                return runnable_cycle


class Location():

    def __init__(self, name, b_end):
        '''
        Constructor of Location class.
            [1] name  : Name of Location class object
            [2] b_end : Whether this location is end point of simulation
        '''
        self.name = name
        self.transitions = []
        self.b_end = b_end

    def add_trans(self, trans):
        '''
        Add new trans to this Location.
            [1] trans : Trans class object
        '''
        self.transitions.append(trans)


class Trans():

    def __init__(self, proc, channel, b_send, to_location, sig_task):
        '''
        Constructor of Trans class.
            [1] proc : Process class object this Trans class object belongs
            [2] channel : Channel class object
            [3] b_send : Whether this is send (not recv) part if channel exists
            [4] to_location : Destination Location class object of this tansition
            [5] sig_task: signal destination task
        '''
        self.proc = proc
        self.channel = channel
        self.b_send = b_send
        self.to_location = to_location
        self.rest_cycle = 0
        self.sig_task = sig_task

    def guard(self, global_cycle):
        '''
        Guard condition of this transition.
        Return value:
          True  > Be able to transit
          False > Not be able to transit
            [1] global_cycle : Current cycle
        '''
        if self.channel:
            if not self.b_send:
                if not self.channel.b_sent or self.channel.sent_cycle > global_cycle:
                    return False
        return True

    def sync(self):
        '''
        Synchronous communication of this transition.
        '''
        pass

    def update(self, global_cycle):
        '''
        Update action of this transition.
        Return value:
          True  > An event occured (ex: set/wait signal)
          False > No event occurs
        This action is executed after transition delay.
            [1] global_cycle : current_cycle
        '''
        return False

    def get_delay(self):
        '''
        Get delay cycle of this transition.
        '''
        return 0

    def add_sig_task(self, sig_task):
        self.sig_task = sig_task


class Task(Process):

    def __init__(self, name, priority):
        '''
        Constructor of Task class.
            [1] name : name of Task class object
            [2] priority : task priority
        '''
        super().__init__(name)
        self.priority = priority
        self.task_state = define_p3s.TaskState.READY
        self.signal = Signal()
        self.wait_sig_id = None
        self.cpu = None

    def restart(self, global_cycle, accuracy_cycle):
        '''
        Restart this Process.
        Return value is rest of runnable cycle
            [1] global_cycle   : Current cycle
            [2] accuracy_cycle : Accuracy cycle (runnable cycle)
        '''
        runnable_cycle = accuracy_cycle
        if self.current_loc == None:
            return -1
        # State transition loop
        while True:
            if self.current_trans == None:
                for trans in self.current_loc.transitions:
                    if trans.guard(global_cycle+(accuracy_cycle-runnable_cycle)):
                        trans.sync()
                        self.current_trans = trans
                        self.trans_state = define_p3s.TransState.TRANS_BEFORE_GET_DELAY
                        break
                else: # There is no transition to be able
                    return runnable_cycle
            if self.trans_state == define_p3s.TransState.TRANS_BEFORE_GET_DELAY:
                self.current_trans.rest_cycle = self.current_trans.get_delay()
                self.trans_state = define_p3s.TransState.TRANS_BEFORE_UPDATE
                if self.current_trans.rest_cycle < 0:
                    return -1
            if runnable_cycle >= 0:
                if self.current_trans.rest_cycle > runnable_cycle:
                    self.current_trans.rest_cycle -= runnable_cycle
                    return 0
                else:
                    runnable_cycle -= self.current_trans.rest_cycle
                    self.current_trans.rest_cycle = 0
            if self.trans_state == define_p3s.TransState.TRANS_BEFORE_UPDATE:
                b_event = self.current_trans.update(global_cycle+(accuracy_cycle-runnable_cycle))
                self.trans_state = define_p3s.TransState.TRANS_AFTER_UPDATE
                if b_event:
                    return runnable_cycle
            self.current_loc = self.current_trans.to_location
            print("@" + self.name + " C:{0} : change location to ".format(global_cycle+(accuracy_cycle-runnable_cycle)) + self.current_loc.name)
            self.current_trans = None
            self.trans_state = None
            if self.current_loc.b_end:
                self.b_finished = True
                return runnable_cycle


class ISR(Task):

    def __init__(self, name, priority):
        '''
        Constructor of ISR class.
            [1] name : name of Task class object
            [2] priority : task priority
        '''
        super().__init__(name, priority)
        self.task_state = define_p3s.TaskState.WAITING
        self.init_loc = None

    def interrupt(self, current_cycle):
        '''
        Interrupt trigger.
        '''
        if not self.current_loc == self.init_loc:
            return False
        for trans in self.init_loc.transitions:
            if trans.guard(current_cycle):
                return True
        else:
            return False

    def add_location(self, loc, b_init):
        '''
        Add new location to this Process.
            [1] loc    : Location class object
            [2] b_init : Whether this location is initial location
        '''
        super().add_location(loc, b_init)
        if b_init:
            self.init_loc = loc

class Model():

    def __init__(self, name, clock):
        '''
        Constructor of Model class.
            [1] name  : Name of Model class object
            [2] clock : clock (MHz) of this model
        '''
        self.name = name
        self.clock = clock
        self.cycle = 0

    def run(self, runnable_cycle):
        '''
        Run first argument cycle.
        This function is used as abstract function.
        (MUST be overrided)
            [1] runnable_cycle : cycle to be able to run
        '''
        pass


class HW_Model(Model):

    def __init__(self, name, clock, proc):
        '''
        Constructor of HW_Model class.
            [1] name  : Name of HW_Model class object
            [2] clock : clock (MHz) of this model
            [3] proc  : Process class object of this HW model core
        '''
        super().__init__(name, clock)
        self.core = proc

    def run(self, runnable_cycle):
        '''
        Run first argument cycle.
            [1] runnable_cycle : cycle to be able to run
        '''
        rest_cycle = self.core.restart(self.cycle, runnable_cycle)
        if rest_cycle >= 0:
            self.cycle += runnable_cycle
        else:
            print("[Error] Failed in restart().")
        if self.core.b_finished:
            return True
        else:
            return False


class CPU_Model(Model):

    def __init__(self, name, clock):
        '''
        Constructor of CPU_Model class.
            [1] name  : Name of CPU_Model class object
            [2] clock : clock (MHz) of this model
        '''
        super().__init__(name, clock)
        self.tasks = []
        self.current_task = None
        self.rest_task_cycle = 0
        self.isrs = []
        self.current_isr = None
        self.rest_isr_cycle = 0

    def run(self, runnable_cycle):
        '''
        Run task for first argument cycle.
            [1] runnable_cycle : cycle to be able to run
        '''
        rest_cycle = runnable_cycle
        running_cycle = 0
        # ISRs (Interrupt Service Routines)
        if self.current_isr == None and self.rest_isr_cycle > 0:
            if rest_cycle > self.rest_isr_cycle:
                running_cycle += self.rest_isr_cycle
                rest_cycle -= self.rest_isr_cycle
                self.rest_isr_cycle = 0
            else:
                self.cycle += runnable_cycle
                self.rest_isr_cycle -= rest_cycle
                return False
        for isr in self.isrs:
            if isr.task_state == define_p3s.TaskState.RUNNING:
                rest_cycle = self.current_isr.restart((self.cycle + running_cycle), rest_cycle)
            elif isr.task_state == define_p3s.TaskState.READY:
                self.current_isr = isr
                self.current_isr.task_state = define_p3s.TaskState.RUNNING
                rest_cycle = self.current_isr.restart((self.cycle + running_cycle), rest_cycle)
            elif isr.task_state == define_p3s.TaskState.WAITING:
                if isr.interrupt(self.cycle + running_cycle):
                    # Interrupted!
                    if not self.current_isr == None:
                        self.current_isr.task_state = define_p3s.TaskState.READY
                    if not self.current_task == None:
                        self.current_task.task_state = define_p3s.TaskState.READY
                        self.current_task = None
                    self.current_isr = isr
                    self.current_isr.task_state = define_p3s.TaskState.RUNNING
                    rest_cycle = self.current_isr.restart((self.cycle + running_cycle), rest_cycle)
                else:
                    continue
            else:
                continue
            # After restart()
            if self.current_isr and self.current_isr.b_finished:
                self.current_isr.current_loc = self.current_isr.init_loc
                self.current_isr.task_state = define_p3s.TaskState.WAITING
                self.current_isr = None
            if rest_cycle == 0:
                self.cycle += runnable_cycle
                return False
            elif self.rest_isr_cycle > 0:
                if rest_cycle > self.rest_isr_cycle:
                    rest_cycle -= self.rest_isr_cycle
                    self.rest_isr_cycle = 0
                else:
                    self.rest_isr_cycle -= rest_cycle
                    self.cycle += runnable_cycle
                    return False
        # Tasks
        while True:
            if self.current_task == None:
                if self.rest_task_cycle > 0:
                    # During task switching
                    if rest_cycle > self.rest_task_cycle:
                        running_cycle += self.rest_task_cycle
                        rest_cycle -= self.rest_task_cycle
                        self.rest_task_cycle = 0
                    else:
                        self.cycle += runnable_cycle
                        self.rest_task_cycle -= rest_cycle
                        return False
                for task in self.tasks:
                    if task.task_state == define_p3s.TaskState.READY:
                        self.current_task = task
                        self.current_task.task_state = define_p3s.TaskState.RUNNING
                        break
                else: # All tasks are WAITING
                    self.cycle += runnable_cycle
                    return False
            # task restart
            rest_cycle = self.current_task.restart((self.cycle + running_cycle), rest_cycle)
            if self.current_task and self.current_task.b_finished:
                self.cycle += (runnable_cycle - rest_cycle)
                return True
            elif self.rest_task_cycle > 0:
                if rest_cycle > self.rest_task_cycle:
                    rest_cycle -= self.rest_task_cycle
                    running_cycle += self.rest_task_cycle
                    self.rest_task_cycle = 0
                else:
                    self.cycle += runnable_cycle
                    self.rest_task_cycle -= rest_cycle
                    return False
            else:
                # Find the highest priority task (one's task_state is READY or RUNNING)
                for task in self.tasks:
                    if task.task_state == define_p3s.TaskState.RUNNING:
                        # No task switch
                        break;
                    elif task.task_state == define_p3s.TaskState.READY:
                        # Task switch
                        if not self.current_task == None and self.current_task.task_state == define_p3s.TaskState.RUNNING:
                            self.current_task.task_state = define_p3s.TaskState.READY
                        self.current_task = None
                        break;
                else: # All tasks are WAITING
                    self.cycle += runnable_cycle
                    return False
            if rest_cycle == 0:
                self.cycle += runnable_cycle
                return False
            running_cycle = runnable_cycle - rest_cycle

    def add_task(self, task):
        '''
        Add new task to this CPU.
        and sort tasks in ascending order of task priority.
            [1] task : Task class object
        '''
        task.cpu = self
        if len(self.tasks) > 0:
            for x in range(0, len(self.tasks)):
                if task.priority > self.tasks[x].priority:
                    self.tasks.insert(x, task)
                    break
            else:
                self.tasks.append(task)
        else:
            self.tasks.append(task)

    def add_isr(self, isr):
        '''
        Add new ISR to this CPU.
        and sort tasks in ascending order of ISR priority.
            [1] isr : ISR class object
        '''
        isr.cpu = self
        if len(self.isrs) > 0:
            for x in range(0, len(self.isrs)):
                if isr.priority > self.isrs[x].priority:
                    self.isrs.insert(x, isr)
                    break
            else:
                self.isrs.append(isr)
        else:
            self.isrs.append(isr)


class Channel():

    def __init__(self, name):
        '''
        Constructor of Channel class.
            [1] name : Name of Channel class object
        '''
        self.name = name
        self.b_sent = False
        self.sent_cycle = 0
        self.data = 0

    def send(self, data, global_cycle, delay):
        '''
        Send data to this channel.
            [1] data : send data
            [2] global_cycle : current cycle
            [3] delay : network delay
        '''
        self.data = data
        self.b_sent = True
        self.sent_cycle = global_cycle + delay

    def recv(self):
        '''
        Receive data from this channel.
        Return value is received data.
        '''
        self.b_sent = False
        self.current_cycle = 0
        return self.data


class Signal():

    def __init__(self):
        '''
        Constructor of Signal class.
        '''
        self.wait_id = define_p3s.SIGNAL_ID_NO_WAIT
        self.tsk_pri = define_p3s.SIGNAL_INIT_PRI

    def set_signal(self, dst_task, sig_id):
        '''
        Set OS signal.
        Return value
          True  > dst Task state is changed
          False > dst Task state is NOT changed
            [1] dst_task : Task class object to be notified
            [2] sig_id : signal ID
        '''
        if dst_task.task_state == define_p3s.TaskState.WAITING and dst_task.signal.wait_id == sig_id:
            dst_task.task_state = define_p3s.TaskState.READY
            self.wait_id = define_p3s.SIGNAL_ID_NO_WAIT
            self.tsk_pri = define_p3s.SIGNAL_INIT_PRI
            return True
        else:
            return False

    def wait_signal(self, src_task, sig_id):
        '''
        Wait for OS signal.
            [1] src_task : Task class object to wait
            [2] sig_id : signal ID
        '''
        self.wait_id = sig_id
        self.tsk_pri = src_task.priority
        src_task.task_state = define_p3s.TaskState.WAITING


class P3S():

    def __init__(self, accuracy_cycle):
        '''
        Constructor of P3S class.
            [1] accuracy_cycle : Accuracy cycle 
        '''
        self.cpu = None
        self.hw = []
        self.memory = []
        self.channel = []
        self.accuracy_cycle = accuracy_cycle

    def add_cpu(self, cpu):
        '''
        Add new CPU model to this Simulation.
            [1] cpu : CPU_Model class object to be added
        '''
        self.cpu = cpu

    def add_hw(self, hw):
        '''
        Add new HW model to this Simulation.
            [1] hw : HW_Model class object to be added
        '''
        self.hw.append(hw)

    def simulate(self):
        '''
        Start this Simulation.
        '''
        if len(self.hw) == 0 and self.cpu == None:
            return False
        while True:
            # run HW models
            for hw in self.hw:
                ret = hw.run(self.accuracy_cycle)
                if ret:
                    # Simulation finished
                    print("Finished cycle: %d" % hw.cycle)
                    return
            # run CPU model
            ret = self.cpu.run(self.accuracy_cycle)
            if ret:
                # Simulation finished
                print("Finished cycle: %d" % self.cpu.cycle)
                return

