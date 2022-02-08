#!/usr/bin/env python

import lldb
import sys

class MemoryValue:
    def __init__(self, section, address, size, value, label, type_name):
        self.section = section
        self.address = address
        self.size = size
        self.value = value
        self.label = label
        self.type_name = type_name

    def __str__(self):
        out = list()
        out.append(self.section)
        out.append("0x%0.16x" % self.address)
        out.append(str(self.size))
        out.append("(unknown)" if self.value is None else str(self.value))
        out.append("(none)" if self.label is None else str(self.label))
        out.append("(none)" if self.type_name is None else str(self.type_name))
        return "\t".join(out)

class MemoryModel:
    def __init__(self):
        self.values = list()

    def add(self, value):
        self.values.append(value)

    def resolve_heap(self, process):

        # Get a dictionary of all heap allocations
        heap_allocs = dict()
        for v in self.values:
            if v.section == "heap":
                heap_allocs[v.address] = v

        # Search all other variables for pointers to a heap block
        for v in self.values:
            if v.section == "heap":
                continue
            
            # try to interpret the value as a memory address in hex
            value_as_addr = None
            try:
                value_as_addr = int(v.value, 16)
            except:
                pass

            if value_as_addr is not None:

                # this value is a memory address, infer the type
                # of the data stored on the heap so we can pretty-print it
                if value_as_addr in heap_allocs:
                    ha = heap_allocs[value_as_addr]
                    if v.type_name != "char *":
                        sys.stderr.write("Type not yet handled\n")
                        sys.exit(1)
                    error = lldb.SBError()
                    data = process.ReadMemory(value_as_addr, ha.size, error)
                    ha.value = str(data)
