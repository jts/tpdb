import lldb
from memory_model import *


def get_globals(target):
    
    module = target.module[target.executable.basename]

    # get the name of global variables 
    # from lldb python examples
    
    # Keep track of which variables we have already looked up
    global_names = list()
    for symbol in module.symbols:
        if symbol.type == lldb.eSymbolTypeData:
            # The symbol is a DATA symbol, lets try and find all global variables
            # that match this name and print them
            global_name = symbol.name
            # Make sure we don't lookup the same variable twice
            if global_name not in global_names:
                global_names.append(global_name)
    
    #TODO: finish
    print("Globals: ", ",".join(global_names))

# from: https://github.com/llvm/llvm-project/blob/main/lldb/examples/python/process_events.py#L65
def run_commands(command_interpreter, commands, print_output=False):
    return_obj = lldb.SBCommandReturnObject()
    for command in commands:
        command_interpreter.HandleCommand(command, return_obj)
        if print_output:
            if return_obj.Succeeded():
                print(return_obj.GetOutput())
            else:
                print(return_obj)

x86_arg_registers = [ "rdi", "rsi", "rdx", "rcx" ]
def get_register_for_argument(arg_index, arch):
    assert(arg_index < 4)
    if arch == "arm64":
        return "x" + str(arg_index)
    else:
        return x86_arg_registers[arg_index]

def get_register_for_return_value(arch):
    if arch == "arm64":
        return "x0"
    else:
        return "rax"

def handle_malloc(memory_model, thread, arch):
    debug_handle_malloc = False
    # determine if this is the target code's call to malloc
    if debug_handle_malloc:
        print("Handle malloc\n\tstack:")
        for fidx, f in enumerate(thread.frames):
            print("\t\tF[%d]: %s %s" %(fidx, thread.frames[fidx].GetFunctionName(), thread.frames[fidx].GetLineEntry()))

    # malloc's size argument is put in first argument register
    arg0 = thread.GetSelectedFrame().FindRegister( get_register_for_argument(0, arch) )
    error = lldb.SBError()
    malloc_size = arg0.GetData().GetUnsignedInt64(error, 0)

    malloc_fn = thread.GetSelectedFrame().GetFunctionName()

    # advance the thread back to the calling function
    while thread.GetSelectedFrame().GetFunctionName() == malloc_fn:
        thread.StepOut()

    # malloc's size argument is returned in register x0 on arm, or rax in x86
    ret = thread.GetSelectedFrame().FindRegister( get_register_for_return_value(arch) )
    malloc_ptr = ret.GetData().GetUnsignedInt64(error, 0)
    memory_model.add_heap_alloc(malloc_ptr, malloc_size)

    if debug_handle_malloc:
        print("\tmalloc addr:0x%x size:%lu" % (malloc_ptr, malloc_size))
        print("\treturned to", thread.GetSelectedFrame().GetFunctionName())

def handle_free(memory_model, thread, arch):
    arg0 = thread.GetSelectedFrame().FindRegister( get_register_for_argument(0, arch) )
    error = lldb.SBError()
    free_ptr = arg0.GetData().GetUnsignedInt64(error, 0)
    memory_model.add_heap_alloc(free_ptr, 0)

    # advance the thread back to the calling function
    thread.StepOut()
    
    #print("\tfree addr:0x%x" % (free_ptr))
