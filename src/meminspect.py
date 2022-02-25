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

#get_globals(target)
#get_text_section(memory_model, target)

n_steps = int(sys.argv[2])
program.step(n_steps)

#print("stdout:")
#
#for s in program.stdout:
#    print(s)
program.memory_model.write_tsv()
