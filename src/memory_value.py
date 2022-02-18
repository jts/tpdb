#!/usr/bin/env python

import lldb
import sys
from heapinspect import *

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
        self.memory = dict()
        self.heap_alloc_sizes = dict()

    def add(self, value):
        self.memory[value.address] = value

    def set_heap_data(self, heap_allocs):
        for (addr, alloc_size, type_str) in heap_allocs:
            print("heap allocation found", addr, alloc_size, type_str)
            self.heap_alloc_sizes[addr] = alloc_size

    def add_from_stack(self, process, section_name, v):

        # global variables show up on the stack frame, do not add them to the memory model
        if v.GetAddress().GetSection().GetName() == "__data":
            return

        #print(section_name, v.location, v.num_children)

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
                        print(i, num_elems, base_address, elem)
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

    def write_tsv(self):
        # header
        print("\t".join( [ "section", "address", "size", "value", "label", "type" ] ))

        for addr in sorted(self.memory.keys()):
            print(self.memory[addr])
