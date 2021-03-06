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
        out.append(self.section.replace(" ", "-"))
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
        
        self.arch = self.target.triple.split("-")[0]

        # launch the process, it will run until the breakpoint is hit
        launch_info = lldb.SBLaunchInfo(None)
        error = lldb.SBError()
        self.process = self.target.Launch(launch_info, error)
        if not error.Success():
            print(error)
            sys.exit(1)
        
        run_commands(self.command_interpreter, ['settings set target.process.thread.step-in-avoid-nodebug false'])
        # put breakpoints on malloc and free
        self.target.BreakpointCreateByName("malloc")
        self.target.BreakpointCreateByName("free")

        sf = self.process.GetSelectedThread().GetSelectedFrame()
        self.line_entry = sf.GetLineEntry()
        self.function_name = sf.GetFunctionName()
        self.main_filename = sf.GetLineEntry().GetFileSpec().GetFilename()
        self.code = dict()
        self.stdout = list()
        self.memory_model = MemoryModel()
        
        # get the text section
        self.memory_model.read_text_section(self.target)

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

    def get_stack_frame_name(self, frame):
        fn = frame.GetDisplayFunctionName()
        if fn == None:
            fn = "(none)"
        return "stack" + " " + fn

    def get_active_stack_frames(self):
        thread = self.process.GetSelectedThread()
        out = list()
        for f in thread.frames:
            out.append(self.get_stack_frame_name(f))
        return out

    def step(self, n_steps=1):
        for _ in range(0, n_steps):

            # advance the program exactly one execution step
            self.advance()

            # update state variables
            thread = self.process.GetSelectedThread()
            self.function_name = thread.GetSelectedFrame().GetFunctionName()
            self.line_entry = thread.GetSelectedFrame().GetLineEntry()
            
            if self.process.state != lldb.eStateExited:
                for frame in thread.frames:
                    # in x86-64 the first stack frame is start before handing to main, skip it
                    sf_name = self.get_stack_frame_name(frame)
                    if "__libc_start" in sf_name:
                        continue
                    for v in frame.variables:
                        self.memory_model.add_from_stack(self.process, sf_name, v)
            
            # Update stdout
            max_chars = 120
            s = self.process.GetSTDOUT(max_chars)
            if len(s) > 0:
                self.stdout.append(s.rstrip())
    
    # advance the program by a single step, taking care
    # of various corner cases (handling malloc, etc)
    def advance(self):
        
        thread = self.process.GetSelectedThread()

        begin_file = self.get_filename_of_current_line(thread)
        begin_line_num = thread.GetSelectedFrame().GetLineEntry().GetLine()

        # perform the step in LLDB
        thread.StepInto()
        
        curr_fn = thread.GetSelectedFrame().GetFunctionName()
        # glibc malloc has mangled function names
        if curr_fn.endswith("malloc"):
            handle_malloc(self.memory_model, thread, self.arch)
        elif curr_fn.endswith("free"):
            handle_free(self.memory_model, thread, self.arch)

        # lazy way of detecting when we're in non-user functions
        # this won't handle programs with code in multiple files
        while not self.has_exited() and self.get_filename_of_current_line(thread) != self.main_filename: 
            thread.StepOut()

        # for reasons I don't yet understand step-into can sometimes do an instruction-level step?
        # detect this by checking whether we changed line numbers, if not recurse
        if self.get_filename_of_current_line(thread) == begin_file and \
            thread.GetSelectedFrame().GetLineEntry().GetLine() == begin_line_num:
            return self.advance()

    def get_filename_of_current_line(self, thread):
        return thread.GetSelectedFrame().GetLineEntry().GetFileSpec().GetFilename()

    def has_exited(self):
        return self.process.state == lldb.eStateExited

class MemoryModel:
    def __init__(self):

        self.memory = dict()
        self.heap_alloc_sizes = dict()
    
    def clear(self):
        self.memory.clear()

    def add(self, value):
        self.memory[value.address] = value

    def add_heap_alloc(self, address, size):
        self.heap_alloc_sizes[address] = size
    
    def add_from_stack(self, process, section_name, v):
        #print(v.GetName(), v.GetAddress().GetSection().GetName(), v.location)
        # global variables show up on the stack frame, do not add them to the memory model
        sn = v.GetAddress().GetSection().GetName()
        if sn == "__data" or sn == ".data":
            return

        # slightly lame, this discards variables that are in registers
        if not v.location.startswith("0x"):
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
            diff = abs(d.GetLoadAddress() - v.GetLoadAddress())
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
                    if str(d.GetType()) == "char":
                        # handle heap string
                        s = ""
                        for i in range(0, num_elems):
                            elem = d.CreateValueFromAddress("(none)", base_address, d.GetType())
                            #print(i, elem, heap_alloc_size)
                            s += elem.GetValue()[1:-1]
                            base_address += element_size
                        mv = MemoryValue(section_name, int(d.location, 16), heap_alloc_size, s, "(none)", str(d.GetType()))
                        self.add(mv)
                    else:
                        # all other datatypes
                        for i in range(0, num_elems):
                            elem = d.CreateValueFromAddress("(none)", base_address, d.GetType())
                            #print(i, num_elems, base_address, elem)
                            self.add_from_stack(process, section_name, elem)
                            base_address += element_size

        elif str(v.GetType().GetArrayElementType()) == "char":
            # special case for character array
            s = ""
            for i in range(0, v.num_children):
                s += (v.GetChildAtIndex(i).GetValue())[1:-1]
            mv = MemoryValue(section_name, int(v.location, 16), v.GetByteSize(), s, v.GetName(), str(v.GetType()))
            self.add(mv)
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

    def read_text_section(self, target):

        module = target.module[target.executable.basename]

        for section in module.sections:
            for sub in section:
                if sub.GetName() == "__cstring":
                    a = []
                    for b in sub.data.uint8:
                        if b != 0:
                            a.append(chr(b))
                        else:
                            a.append("\\0")
                    s = ''.join(a).replace("\n", "\\n")
                    #print("%s\t0x%0.16x\t%s\t%s\t%d" % ("text", sub.addr.GetLoadAddress(target), s, "null", sub.GetByteSize()))
                    mv = MemoryValue("text", sub.addr.GetLoadAddress(target), sub.GetByteSize(), s, None, None)
                    self.add(mv)

    def get_memory_sections(self):
        # partition by section
        sections = dict()
        sections["heap"] = list()
        for addr, o in self.memory.items():
            if o.section not in sections:
                sections[o.section] = list()
            sections[o.section].append(o) 
        return sections

    def write_tsv(self, fp):
        # header
        fp.write("\t".join( [ "section", "address", "size", "value", "label", "type\n" ] ))

        for addr in sorted(self.memory.keys()):
            fp.write("%s\n" % self.memory[addr])
