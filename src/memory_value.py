#!/usr/bin/env python

import lldb
import sys
from utils import *

class MemoryValue:
    def __init__(self, section, address, size, value, label, type_name):
        self.section = section
        self.address = address
        self.size = size
        self.value = value
        self.label = label
        self.type_name = type_name

    def get_addr_as_str(self):
        return "0x%0.16x" % self.address

    def get_value_as_str(self):
        return "(unknown)" if self.value is None else str(self.value) 

    def get_label_as_str(self):
        return "(none)" if self.label is None else str(self.label)

    def __str__(self):
        out = list()
        out.append(self.section)
        out.append(self.get_addr_as_str())
        out.append(str(self.size))
        out.append("(unknown)" if self.value is None else str(self.value))
        out.append("(none)" if self.label is None else str(self.label))
        out.append("(none)" if self.type_name is None else str(self.type_name))
        return "\t".join(out)

class ProgramState:
    def __init__(self, program_name):

        # initialize debugger, load the target
        self.debugger = lldb.SBDebugger.Create()
        self.debugger.SetAsync(False)
        self.command_interpreter = self.debugger.GetCommandInterpreter()
        self.target = self.debugger.CreateTarget(program_name)
        # put a breakpoint on main before we launch so our initial state is there
        self.target.BreakpointCreateByName("main")
    
        # launch the process, it will run until the breakpoint is hit
        launch_info = lldb.SBLaunchInfo(None)
        error = lldb.SBError()
        self.process = self.target.Launch(launch_info, error)
        run_commands(self.command_interpreter, ['settings set target.process.thread.step-in-avoid-nodebug false'])

        # put breakpoints on malloc and free
        #https://github.com/llvm/llvm-project/blob/main/lldb/examples/python/process_events.py
        self.debugger.HandleCommand("_regexp-break malloc")
        self.debugger.HandleCommand("_regexp-break free")

        sf = self.process.GetSelectedThread().GetSelectedFrame()
        self.line_entry = sf.GetLineEntry()
        self.function_name = sf.GetFunctionName()
        self.code = dict()
        self.stdout = list()

    def get_code(self):
        d = self.line_entry.GetFileSpec().GetDirectory()
        f = self.line_entry.GetFileSpec().GetFilename()
        
        if d is None or f is None:
            return []

        p = d + "/" + f

        if p not in self.code:
            lines = list()
            with open(p) as fh:
                for (ln, s) in enumerate(fh):
                    lines.append("%3d %s" % (ln + 1, s.rstrip()))
            self.code[p] = lines
        return self.code[p]    

    def get_line_number(self):
        return self.line_entry.GetLine()

    def step(self, memory_model, n_steps=1):
        if not self.process.IsValid():
            return

        for _ in range(0, n_steps):
            for thread in self.process:

                thread.StepInto()
                self.function_name = thread.GetSelectedFrame().GetFunctionName()

                if self.function_name == "malloc":
                    handle_malloc(memory_model, thread)
                elif self.function_name == "free":
                    handle_free(memory_model, thread)

                # Lazy way of detecting when we're in non-user functions
                while thread.GetSelectedFrame().GetLineEntry().GetFileSpec().GetFilename() is None: 
                    thread.StepOut()
                
                # the handle functions can advance the state so these must be set again 
                self.function_name = thread.GetSelectedFrame().GetFunctionName()
                self.line_entry = thread.GetSelectedFrame().GetLineEntry()
            
            # Update stack
            for frame in thread.frames:
                sf_name = "stack" + "-" + frame.GetDisplayFunctionName()
                for v in frame.variables:
                    memory_model.add_from_stack(self.process, sf_name, v)

            # Update stdout
            max_chars = 120
            s = self.process.GetSTDOUT(max_chars)
            if len(s) > 0:
                self.stdout.append(s.rstrip())
            
class MemoryModel:
    def __init__(self):

        self.memory = dict()
        self.heap_alloc_sizes = dict()

    def add(self, value):
        self.memory[value.address] = value

    def add_heap_alloc(self, address, size):
        self.heap_alloc_sizes[address] = size
    
    def add_from_stack(self, process, section_name, v):

        # global variables show up on the stack frame, do not add them to the memory model
        if v.GetAddress().GetSection().GetName() == "__data":
            return

        # Store POD stack variables and pointers to the memory model
        # More complicated stack variables (structs, arrays) are handled below
        if v.num_children == 0 or v.TypeIsPointerType():
            mv = MemoryValue(section_name, int(v.location, 16), v.GetByteSize(), str(v.GetValue()), v.GetName(), str(v.GetType()))
            self.add(mv)

        # If POD stack variable return now, nothing else to do
        if v.num_children == 0 and not v.TypeIsPointerType():
            return

        # If this is a pointer we need to figure out whether it points to the stack or heap
        # if its on the heap we recurse to parse the heap data
        if v.TypeIsPointerType():
            d = v.Dereference()

            # very hacky way to determine whether on stack or heap
            diff = d.GetLoadAddress() - v.GetLoadAddress()
            if diff > 100000:
                section_name = "heap"
            else:
                # this is a pointer to non-heap data, nothing else to do
                return

            # get the size of this heap allocation, we need this to work out 
            # how many items it points to
            if d.location is not None and d.location != '':
                heap_addr = int(d.location, 16)
                if heap_addr in self.heap_alloc_sizes:
                    heap_alloc_size = self.heap_alloc_sizes[heap_addr]
                    element_size = d.GetByteSize()
                    base_address = d.GetLoadAddress()
                    num_elems = int(heap_alloc_size / element_size)
                    for i in range(0, num_elems):
                        elem = d.CreateValueFromAddress("(none)", base_address, d.GetType())
                        #print(i, num_elems, base_address, elem)
                        self.add_from_stack(process, section_name, elem)
                        base_address += element_size
        else:
            # this is an array or struct
            name = v.GetName()
            for i in range(0, v.num_children):
                child = v.GetChildAtIndex(i)

                # pretty print the name
                child_name = child.GetName()
                if child_name[0] == '[' and child_name[-1] == ']':
                    # array
                    name = v.GetName() + child.GetName()
                else:
                    # assume struct
                    name = v.GetName() + "." +child.GetName()

                mv = MemoryValue(section_name, int(child.location, 16), child.GetByteSize(), str(child.GetValue()), name, str(child.GetType()))
                self.add(mv)

    def get_ordered(self):
        for addr in sorted(self.memory.keys()):
            yield self.memory[addr]

    def write_tsv(self):
        # header
        print("\t".join( [ "section", "address", "size", "value", "label", "type" ] ))

        for addr in sorted(self.memory.keys()):
            print(self.memory[addr])
