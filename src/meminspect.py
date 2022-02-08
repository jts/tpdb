#!/usr/bin/env python

#----------------------------------------------------------------------
# Dump the contents of memory for a given project at a given breakpoint
# using lldb's python API
#----------------------------------------------------------------------
from __future__ import print_function

import lldb
import argparse
import os
import sys
from heapinspect import *
from utils import *
from memory_value import *

# Turn on malloc logging so we can track heap memory
os.environ["MallocStackLogging"] = "malloc"

# initialize debugger, load the target
lldb.debugger = lldb.SBDebugger.Create()
lldb.debugger.SetAsync(False)
target = lldb.debugger.CreateTarget(sys.argv[1])

# set the breakpoint where we want the memory dump to occur
breakpoint0 = target.BreakpointCreateByLocation(sys.argv[2], int(sys.argv[3]))

# launch the process, it will run until the breakpoint is hit
process = target.LaunchSimple(None, None, os.getcwd())

heap_dump_options = HeapDumpOptions()

# the memory values we harvest from the debugger are stored here
memory_model = MemoryModel()

# header
print("\t".join( [ "section", "address", "size", "value", "label", "type" ] ))

#get_globals(target)
get_text_section(memory_model, target)

# print everything in the stack frame
for thread in process:

    # get all the allocations on the heap up to this point of the programs execution
    # we need to provide a stack frame to execute this dump on so we pass in
    # the current frame (where the breakpoint is)
    get_heap_allocs(memory_model, target, thread.frames[0], heap_dump_options, 0, True)
    
    for sf in thread.frames:
        get_stack_variables(memory_model, sf)

memory_model.resolve_heap(process)

for v in memory_model.values:
    print(v)
