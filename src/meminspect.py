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
lldb.debugger = lldb.SBDebugger.Create()
lldb.debugger.SetAsync(False)
target = lldb.debugger.CreateTarget(sys.argv[1])

# set the breakpoint where we want the memory dump to occur
#breakpoint0 = target.BreakpointCreateByLocation(sys.argv[2], int(sys.argv[3]))
breakpoint0 = target.BreakpointCreateByName("main")

# launch the process, it will run until the breakpoint is hit
process = target.LaunchSimple(None, None, os.getcwd())

heap_dump_options = HeapDumpOptions()

# the memory values we harvest from the debugger are stored here
memory_model = MemoryModel()

#get_globals(target)
get_text_section(memory_model, target)

n_instructions = int(sys.argv[2])

#symbolicator = lldb.utils.symbolication.Symbolicator()
#symbolicator.target = target

# print everything in the stack frame
for thread in process:
    
    # for unknown reasons we need to make a step before we can start getting data from the heap
    thread.StepOver()
    for _ in range(0, n_instructions):
        thread.StepOver()
        sf = thread.GetSelectedFrame()
        le = sf.GetLineEntry()

    heap = get_heap(target, thread.GetSelectedFrame(), heap_dump_options, 0, True)
    print(heap)
    memory_model.set_heap_data(heap)

    for frame in thread.frames:
        sf_name = "stack" + "-" + frame.GetDisplayFunctionName()
        for v in frame.variables:
            memory_model.add_from_stack(process, sf_name, v)

memory_model.write_tsv()
