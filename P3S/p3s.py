#!/usr/bin/env python

''' P3S (Python Parallel Process Simulator)

 Modification History:
 ===========================================================
 Date           Version   Description
 ===========================================================
  9 Feb. 2017   1.2       Add Signal class
  6 Feb. 2017   1.1       Change send channel time from sync to update
 15 Jan. 2017   1.0       Creation
 -----------------------------------------------------------
'''

__version__ = "1.2"
__date__    = "9 Feb. 2017"
__author__  = "Shun SUGIMOTO <sugimoto.shun@gmail.com>"

from P3S import cfg_p3s

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
                        self.trans_state = cfg_p3s.TransState.TRANS_BEFORE_GET_DELAY
                        break
                else: # There is no transition to be able
                    return runnable_cycle
            if self.trans_state == cfg_p3s.TransState.TRANS_BEFORE_GET_DELAY:
                self.current_trans.rest_cycle = self.current_trans.get_delay()
                self.trans_state = cfg_p3s.TransState.TRANS_BEFORE_UPDATE
                if self.current_trans.rest_cycle < 0:
                    return -1
            if runnable_cycle >= 0:
                if self.current_trans.rest_cycle > runnable_cycle:
                    self.current_trans.rest_cycle -= runnable_cycle
                    return 0
                else:
                    runnable_cycle -= self.current_trans.rest_cycle
                    self.current_trans.rest_cycle = 0
            if self.trans_state == cfg_p3s.TransState.TRANS_BEFORE_UPDATE:
                self.current_trans.update(global_cycle+(accuracy_cycle-runnable_cycle))
                self.trans_state = cfg_p3s.TransState.TRANS_AFTER_UPDATE
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

    def __init__(self, proc, channel, b_send, to_location):
        '''
        Constructor of Trans class.
            [1] proc : Process class object this Trans class object belongs
            [2] channel : Channel class object
            [3] b_send : Whether this is send (not recv) part if channel exists
            [4] to_location : Destination Location class object of this tansition
        '''
        self.proc = proc
        self.channel = channel
        self.b_send = b_send
        self.to_location = to_location
        self.rest_cycle = 0

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


class Task(Process):

    def __init__(self, name, priority, signal):
        '''
        Constructor of Task class.
            [1] name : name of Task class object
            [2] priority : task priority
        '''
        super().__init__(name)
        self.priority = priority
        self.task_state = cfg_p3s.TaskState.READY
        self.signal = signal
        self.wait_sig_id = None

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
                        self.trans_state = cfg_p3s.TransState.TRANS_BEFORE_GET_DELAY
                        break
                else: # There is no transition to be able
                    return runnable_cycle
            if self.trans_state == cfg_p3s.TransState.TRANS_BEFORE_GET_DELAY:
                self.current_trans.rest_cycle = self.current_trans.get_delay()
                self.trans_state = cfg_p3s.TransState.TRANS_BEFORE_UPDATE
                if self.current_trans.rest_cycle < 0:
                    return -1
            if runnable_cycle >= 0:
                if self.current_trans.rest_cycle > runnable_cycle:
                    self.current_trans.rest_cycle -= runnable_cycle
                    return 0
                else:
                    runnable_cycle -= self.current_trans.rest_cycle
                    self.current_trans.rest_cycle = 0
            if self.trans_state == cfg_p3s.TransState.TRANS_BEFORE_UPDATE:
                b_event = self.current_trans.update(global_cycle+(accuracy_cycle-runnable_cycle))
                self.trans_state = cfg_p3s.TransState.TRANS_AFTER_UPDATE
                if b_event:
                    return runnable_cycle
            self.current_loc = self.current_trans.to_location
            print("@" + self.name + " C:{0} : change location to ".format(global_cycle+(accuracy_cycle-runnable_cycle)) + self.current_loc.name)
            self.current_trans = None
            self.trans_state = None
            if self.current_loc.b_end:
                self.b_finished = True
                return runnable_cycle


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

    def __init__(self, name, clock, task_switch_delay):
        '''
        Constructor of CPU_Model class.
            [1] name  : Name of CPU_Model class object
            [2] clock : clock (MHz) of this model
            [3] task_switch_delay : Delay (cycle) of task switch
        '''
        super().__init__(name, clock)
        self.task_switch_delay = task_switch_delay
        self.tasks = []
        self.current_task = None
        self.next_task = None
        self.rest_task_switch_delay = 0
        self.num_of_task_switch = 0

    def run(self, runnable_cycle):
        '''
        Run task for first argument cycle.
            [1] runnable_cycle : cycle to be able to run
        '''
        rest_cycle = runnable_cycle
        running_cycle = 0
        # ISR (Interrupt Service Routines)
        # To Be Modified!
        # Tasks
        while True:
            if self.current_task == None:
                if self.rest_task_switch_delay > 0:
                    # During task switching
                    if rest_cycle > self.rest_task_switch_delay:
                        self.rest_task_switch_delay = 0
                        rest_cycle -= self.rest_task_switch_delay
                        running_cycle += self.rest_task_switch_delay
                    else:
                        self.cycle += runnable_cycle
                        self.rest_task_switch_delay -= rest_cycle
                        return False
                for task in self.tasks:
                    if task.task_state == cfg_p3s.TaskState.READY:
                        self.current_task = task
                        self.current_task.task_state = cfg_p3s.TaskState.RUNNING
                        break
                else: # All tasks are WAITING
                    self.cycle += runnable_cycle
                    return False
            # task restart
            rest_cycle = self.current_task.restart((self.cycle + running_cycle), rest_cycle)
            if self.current_task.b_finished:
                self.cycle += (runnable_cycle - rest_cycle)
                return True
            else:
                # Find the highest priority task (one's task_state is READY or RUNNING)
                for task in self.tasks:
                    if task.task_state == cfg_p3s.TaskState.RUNNING:
                        # No task switch
                        break;
                    elif task.task_state == cfg_p3s.TaskState.READY:
                        # Task switch
                        self.rest_task_switch_delay = self.task_switch_delay
                        if self.current_task.task_state == cfg_p3s.TaskState.RUNNING:
                            self.current_task.task_state = cfg_p3s.TaskState.READY
                        self.current_task = None
                        self.num_of_task_switch += 1
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
        if len(self.tasks) > 0:
            for x in range(0, len(self.tasks)):
                if task.priority > self.tasks[x].priority:
                    self.tasks.insert(x, task)
                    break
            else:
                self.tasks.append(task)
        else:
            self.tasks.append(task)


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

    def send(self, data, global_cycle):
        '''
        Send data to this channel.
            [1] data : send data
            [2] global_cycle : current cycle
        '''
        self.data = data
        self.b_sent = True
        self.sent_cycle = global_cycle

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
        self.wait_tasks = []

    def add_signal_task(self, task):
        '''
        Add task to use this signal.
            [1] task : Task class object to use this signal
        '''
        self.wait_tasks.append(task)

    def set_signal(self, sig_id):
        '''
        Set OS signal.
            [1] sig_id : signal ID
        '''
        for x in range(0, len(self.wait_tasks)):
            if self.wait_tasks[x].task_state == cfg_p3s.TaskState.WAITING and self.wait_tasks[x].wait_sig_id == sig_id:
                self.wait_tasks[x].task_state = cfg_p3s.TaskState.READY
                self.wait_tasks[x].wait_sig_id = -1

    def wait_signal(self, task, sig_id):
        '''
        Wait for OS signal.
            [1] task : Task class object to wait this signal
            [2] sig_id : signal ID
        '''
        task.wait_sig_id = sig_id
        task.task_state = cfg_p3s.TaskState.WAITING


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
                print("Task switch : %d times" % self.cpu.num_of_task_switch)
                return

