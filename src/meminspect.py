#!/usr/bin/env python

#----------------------------------------------------------------------
# Dump the contents of memory for a given program at a given breakpoint
# using lldb's python API
#----------------------------------------------------------------------
from import_lldb import *
import lldb.utils.symbolication

import argparse
import sys
import os
from heapinspect import *
from memory_value import *
from utils import *

# Turn on malloc logging so we can track heap memory
os.environ["MallocStackLogging"] = "malloc"

# initialize debugger, load the target
debugger = lldb.SBDebugger.Create()
debugger.SetAsync(False)
command_interpreter = debugger.GetCommandInterpreter()
target = debugger.CreateTarget(sys.argv[1])

# set the breakpoint where we want the memory dump to occur
#breakpoint0 = target.BreakpointCreateByLocation(sys.argv[2], int(sys.argv[3]))
breakpoint0 = target.BreakpointCreateByName("main")

launch_info = lldb.SBLaunchInfo(None)

# launch the process, it will run until the breakpoint is hit
#process = target.LaunchSimple(None, None, os.getcwd())
error = lldb.SBError()
process = target.Launch(launch_info, error)

#https://github.com/llvm/llvm-project/blob/main/lldb/examples/python/process_events.py
debugger.HandleCommand("_regexp-break malloc")
run_commands(command_interpreter, ['breakpoint list'])
#run_commands(command_interpreter, ['settings set target.process.virtual-addressable-bits 39'])
#run_commands(command_interpreter, ['settings show'])
run_commands(command_interpreter, ['settings set target.process.thread.step-in-avoid-nodebug false'])
#breakpoint1 = target.BreakpointCreateByName("malloc")
#breakpoint1 = target.BreakpointCreateByName("malloc")
#breakpoint1 = target.BreakpointCreateByAddress("0x100003f90")
heap_dump_options = HeapDumpOptions()

# the memory values we harvest from the debugger are stored here
memory_model = MemoryModel()

#get_globals(target)
get_text_section(memory_model, target)

n_instructions = int(sys.argv[2])

# print everything in the stack frame
for _ in range(0, n_instructions):

    for thread in process:

        thread.StepInto()
        sf = thread.GetSelectedFrame()
        current_function = sf.GetFunctionName()
        le = sf.GetLineEntry()
        print(current_function, thread.GetStopReason(), le)
        if current_function == "malloc":
            handle_malloc(memory_model, thread)

    for frame in thread.frames:
        sf_name = "stack" + "-" + frame.GetDisplayFunctionName()
        for v in frame.variables:
            memory_model.add_from_stack(process, sf_name, v)

memory_model.write_tsv()
