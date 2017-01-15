#!/usr/bin/env python

''' P3S (Python Parallel Process Simulator)
'''

__version__ = "1.0"
__date__    = "15 Jan. 2017"
__author__  = "Shun SUGIMOTO <sugimoto.shun@gmail.com>"

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
                        trans.sync(global_cycle+(accuracy_cycle-runnable_cycle))
                        self.current_trans = trans
                        self.current_trans.rest_cycle = -1
                        break
                else: # There is no transition to be able
                    return runnable_cycle
            if self.current_trans.rest_cycle < 0:
                self.current_trans.rest_cycle = self.current_trans.get_delay()
                if self.current_trans.rest_cycle < 0:
                    return -1
            if runnable_cycle >= 0:
                if self.current_trans.rest_cycle > runnable_cycle:
                    self.current_trans.rest_cycle -= runnable_cycle
                    return 0
                else:
                    runnable_cycle -= self.current_trans.rest_cycle
                    self.current_trans.rest_cycle = 0
            self.current_trans.update()
            self.current_loc = self.current_trans.to_location
            print("@" + self.name + " C:{0} : change location to ".format(global_cycle+(accuracy_cycle-runnable_cycle)) + self.current_loc.name)
            self.current_trans = None
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

    def __init__(self, proc, sync_channel, b_send, to_location):
        '''
        Constructor of Trans class.
            [1] proc : Process class object this Trans class object belongs
            [2] sync_channel : Channel class object included in guard condition
            [3] b_send : Whether this is send (not recv) part if sync channel exists
            [4] to_location : Destination Location class object of this tansition
        '''
        self.proc = proc
        self.sync_channel = sync_channel
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
        if self.sync_channel:
            if self.b_send:
                if self.sync_channel.b_sent:
                    return False
            else:
                if not self.sync_channel.b_sent or self.sync_channel.sent_cycle > global_cycle:
                    return False
        return True

    def sync(self, global_cycle):
        '''
        Synchronous communication of this transition.
            [1] global_cycle : current_cycle
        '''
        pass

    def update(self):
        '''
        Update action of this transition.
        This action is executed after transition delay.
        '''
        pass

    def get_delay(self):
        '''
        Get delay cycle of this transition.
        '''
        return 0


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
            print("error @restart")
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
        self.priority = []
        self.current_task = None
        self.next_task = None
        self.rest_task_switch_delay = 0

    def run(self, runnable_cycle):
        '''
        Run first argument cycle.
            [1] runnable_cycle : cycle to be able to run
        '''
        rest_cycle = runnable_cycle
        running_cycle = 0
        if self.next_task:
            if rest_cycle > self.rest_task_switch_delay:
                self.current_task = self.next_task
                self.next_task = None
                self.rest_task_switch_delay = 0
                rest_cycle = self.current_task.restart((self.cycle+self.rest_task_switch_delay), rest_cycle)
                running_cycle = (runnable_cycle-rest_cycle)
                if self.current_task.b_finished:
                    self.cycle += (runnable_cycle - rest_cycle)
                    return True
                if rest_cycle == 0:
                    self.cycle += runnable_cycle
                    if self.current_task.b_finished:
                        return True
                    else:
                        return False
            else:
                self.cycle += runnable_cycle
                self.rest_task_switch_delay -= rest_cycle
                return False
        for task in self.tasks:
            if task != self.current_task:
                # Check whether this task is able to run
                b_able_to_run = True
                if task.current_trans == None:
                    b_able_to_run = False
                    for trans in task.current_loc.transitions:
                        b_able_to_run = trans.guard(self.cycle+running_cycle)
                        if b_able_to_run:
                            break
                if b_able_to_run:
                    # Task switch
                    if rest_cycle > self.task_switch_delay:
                        rest_cycle -= self.task_switch_delay
                        running_cycle += self.task_switch_delay
                        self.next_task = None
                        self.rest_task_switch_delay = 0
                        self.current_task = task
                        rest_cycle = task.restart((self.cycle+running_cycle), rest_cycle)
                    else:
                        self.next_task = task
                        self.rest_task_switch_delay = self.task_switch_delay - rest_cycle
                        self.cycle += runnable_cycle
                        return False
            else:
                rest_cycle = task.restart((self.cycle+running_cycle), rest_cycle)
            if task.b_finished:
                self.cycle += (runnable_cycle - rest_cycle)
                return True
            if rest_cycle == 0:
                self.cycle += runnable_cycle
                return False
            running_cycle = runnable_cycle - rest_cycle
        self.cycle += runnable_cycle
        return False

    def add_task(self, proc, priority):
        '''
        Add new task to this CPU.
            [1] proc : Process class object declared task
        '''
        if len(self.priority) > 0:
            for x in range(0, len(self.priority)):
                if priority > self.priority[x]:
                    self.tasks.insert(x, proc)
                    self.priority.insert(x, priority)
                    if x == 0:
                        self.current_task = proc
                    break
            else:
                self.tasks.append(proc)
                self.priority.append(priority)
        else:
            self.tasks.append(proc)
            self.priority.append(priority)
            self.current_task = proc


# N/A?
class SharedMemory():

    def __init__(self, name):
        '''
        Constructor of SharedMemory class.
            [1] name : Name of SharedMemory class object
        '''
        self.name = name
        self.data = 0

    def get_write_delay(self):
        '''
        Get delay cycle to WRITE access to this shared memory.
        '''
        return 0

    def get_read_delay(self):
        '''
        Get delay cycle to READ access to this shared memory.
        '''
        return 0


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

    # N/A?
    def add_memory(self, mem):
        '''
        Add new shared memory to this Simulation.
            [1] mem : SharedMemory class object to be added
        '''
        self.memory.append(mem)

    def simulate(self):
        '''
        Start this Simulation.
        '''
        if len(self.hw) == 0 or self.cpu == None:
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

