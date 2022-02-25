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

from memory_model import *
from utils import *

if len(sys.argv) != 3:
    sys.stderr.write("usage: meminspect.py <program> <n>")
    sys.exit(1)

program = ProgramState(sys.argv[1])

# the memory values we harvest from the debugger are stored here
memory_model = MemoryModel()

#get_globals(target)
#get_text_section(memory_model, target)

n_steps = int(sys.argv[2])

for _ in range(0, n_steps):
    program.step(memory_model)

#print("stdout:")
#
#for s in program.stdout:
#    print(s)
memory_model.write_tsv()
