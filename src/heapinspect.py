#!/usr/bin/env python

#----------------------------------------------------------------------
# Dump the contents of the heap using MacOS's built-in malloc logging
# (MallocStackLogging). This code is largely from 
# https://github.com/llvm/llvm-project/blob/main/lldb/examples/darwin/heap_find/heap.py
# but with minor modifications to run outside of the debugger.
#----------------------------------------------------------------------
import os
import lldb
import lldb.utils.symbolication

from memory_value import *

class HeapDumpOptions:
    def __init__(self):
        self.max_frames = 16
        self.max_history = 16
        self.verbose = False

# all of this is from heap.py
def get_heap_allocs(memory_model, target, frame, options, addr, history):
    # malloc_stack_entry *get_stack_history_for_address (const void * addr)
    expr_prefix = '''
typedef int kern_return_t;
typedef struct $malloc_stack_entry {
    uint64_t address;
    uint64_t argument;
    uint32_t type_flags;
    uint32_t num_frames;
    uint64_t frames[512];
    kern_return_t err;
} $malloc_stack_entry;
'''
    single_expr = '''
#define MAX_FRAMES %u
typedef unsigned task_t;
$malloc_stack_entry stack;
stack.address = 0x%x;
stack.type_flags = 2;
stack.num_frames = 0;
stack.frames[0] = 0;
uint32_t max_stack_frames = MAX_FRAMES;
stack.err = (kern_return_t)__mach_stack_logging_get_frames (
    (task_t)mach_task_self(),
    stack.address,
    &stack.frames[0],
    max_stack_frames,
    &stack.num_frames);
if (stack.num_frames < MAX_FRAMES)
    stack.frames[stack.num_frames] = 0;
else
    stack.frames[MAX_FRAMES-1] = 0;
stack''' % (options.max_frames, addr)

    history_expr = '''
typedef int kern_return_t;
typedef unsigned task_t;
#define MAX_FRAMES %u
#define MAX_HISTORY %u
typedef struct mach_stack_logging_record_t {
	uint32_t type_flags;
	uint64_t stack_identifier;
	uint64_t argument;
	uint64_t address;
} mach_stack_logging_record_t;
typedef void (*enumerate_callback_t)(mach_stack_logging_record_t, void *);
typedef struct malloc_stack_entry {
    uint64_t address;
    uint64_t argument;
    uint32_t type_flags;
    uint32_t num_frames;
    uint64_t frames[MAX_FRAMES];
    kern_return_t frames_err;
} malloc_stack_entry;
typedef struct $malloc_stack_history {
    task_t task;
    unsigned idx;
    malloc_stack_entry entries[MAX_HISTORY];
} $malloc_stack_history;
$malloc_stack_history lldb_info = { (task_t)mach_task_self(), 0 };
uint32_t max_stack_frames = MAX_FRAMES;
enumerate_callback_t callback = [] (mach_stack_logging_record_t stack_record, void *baton) -> void {
    $malloc_stack_history *lldb_info = ($malloc_stack_history *)baton;
    if (lldb_info->idx < MAX_HISTORY) {
        malloc_stack_entry *stack_entry = &(lldb_info->entries[lldb_info->idx]);
        stack_entry->address = stack_record.address;
        stack_entry->type_flags = stack_record.type_flags;
        stack_entry->argument = stack_record.argument;
        stack_entry->num_frames = 0;
        stack_entry->frames[0] = 0;
        stack_entry->frames_err = (kern_return_t)__mach_stack_logging_frames_for_uniqued_stack (
            lldb_info->task,
            stack_record.stack_identifier,
            stack_entry->frames,
            (uint32_t)MAX_FRAMES,
            &stack_entry->num_frames);
        // Terminate the frames with zero if there is room
        if (stack_entry->num_frames < MAX_FRAMES)
            stack_entry->frames[stack_entry->num_frames] = 0;
    }
    ++lldb_info->idx;
};
(kern_return_t)__mach_stack_logging_enumerate_records (lldb_info.task, (uint64_t)0x%x, callback, &lldb_info);
lldb_info''' % (options.max_frames, options.max_history, addr)

    #frame = lldb.debugger.GetSelectedTarget().GetProcess(
    #).GetSelectedThread().GetSelectedFrame()
    
    if history:
        expr = history_expr
    else:
        expr = single_expr
    expr_options = lldb.SBExpressionOptions()
    expr_options.SetIgnoreBreakpoints(True)
    expr_options.SetTimeoutInMicroSeconds(5 * 1000 * 1000)  # 5 second timeout
    expr_options.SetTryAllThreads(True)
    expr_options.SetLanguage(lldb.eLanguageTypeObjC_plus_plus)
    expr_options.SetPrefix(expr_prefix)
    expr_sbvalue = frame.EvaluateExpression(expr, expr_options)
    if options.verbose:
        print("expression:")
        print(expr)
        print("expression result:")
        print(expr_sbvalue)
    if expr_sbvalue.error.Success():
        if history:
            malloc_stack_history = lldb.value(expr_sbvalue)
            num_stacks = int(malloc_stack_history.idx)
            if num_stacks <= options.max_history:
                i_max = num_stacks
            else:
                i_max = options.max_history
            for i in range(i_max):
                stack_history_entry = malloc_stack_history.entries[i]
                dump_stack_history_entry(memory_model, target, options, stack_history_entry, i)
        else:
            stack_history_entry = lldb.value(expr_sbvalue)
            dump_stack_history_entry(memory_model, target, options, stack_history_entry, 0)

    else:
        sys.stderr.write("Failure to get heap data")

def type_flags_to_string(type_flags):
    if type_flags == 0:
        type_str = 'free'
    elif type_flags & 2:
        type_str = 'malloc'
    elif type_flags & 4:
        type_str = 'free'
    elif type_flags & 1:
        type_str = 'generic'
    elif type_flags & 8:
        type_str = 'stack'
    elif type_flags & 16:
        type_str = 'stack (red zone)'
    elif type_flags & 32:
        type_str = 'segment'
    elif type_flags & 64:
        type_str = 'vm_region'
    else:
        type_str = hex(type_flags)
    return type_str

def dump_stack_history_entry(memory_model, target, options, stack_history_entry, idx):
    symbolicator = lldb.utils.symbolication.Symbolicator()
    symbolicator.target = target
    target_name = str(target)

    address = int(stack_history_entry.address)
    #type_flags = int(stack_history_entry.type_flags)
    argument = int(stack_history_entry.argument)
    #print("ADDR: 0x%x flags: %d argument: %d" % (address, type_flags, argument))
    #return 
    if address:
        type_flags = int(stack_history_entry.type_flags)
        type_str = type_flags_to_string(type_flags)
        allocation_in_user_code = False
        frame_idx = 0
        idx = 0
        pc = int(stack_history_entry.frames[idx])
        while pc != 0:
            if pc >= 0x1000:
                frames = symbolicator.symbolicate(pc)
                if frames:
                    for frame in frames:
                        func_call_str = str(frame.symbolication)

                        # This checks whether a function called within the target
                        # is the second entry after the stack, which indicates it was a 
                        # malloc() (or related function) call within our program of interest
                        if frame_idx == 1 and func_call_str.startswith(target_name):
                            allocation_in_user_code = True
                        if options.verbose:
                            print('     [%u] %s' % (frame_idx, frame))
                        frame_idx += 1
                else:
                    if options.verbose:
                        print('     [%u] 0x%x' % (frame_idx, pc))
                    frame_idx += 1
                idx = idx + 1
                pc = int(stack_history_entry.frames[idx])
            else:
                pc = 0
        if allocation_in_user_code:
            value = MemoryValue("heap", address, argument, None, None, None)
            memory_model.add(value)

