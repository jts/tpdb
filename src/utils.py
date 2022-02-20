import lldb
from memory_value import *
def get_text_section(memory_model, target):

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
                memory_model.add(mv)

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

def get_stack_variables(memory_model, frame):
    sf_name = "stack" + "-" + frame.GetDisplayFunctionName()
    for v in frame.variables:
        section_name = v.GetAddress().GetSection().GetName()
        # do not display globals in stack
        if section_name == "__data":
            continue
       
        if v.num_children == 0 or v.TypeIsPointerType(): 
            mv = MemoryValue(sf_name, int(v.location, 16), v.GetByteSize(), str(v.GetValue()), v.GetName(), str(v.GetType()))
            memory_model.add(mv)
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

                mv = MemoryValue(sf_name, int(child.location, 16), child.GetByteSize(), str(child.GetValue()), name, str(child.GetType()))
                memory_model.add(mv)
                # only print the name for the first entry

# from: https://github.com/llvm/llvm-project/blob/main/lldb/examples/python/process_events.py#L65
def run_commands(command_interpreter, commands):
    return_obj = lldb.SBCommandReturnObject()
    for command in commands:
        command_interpreter.HandleCommand(command, return_obj)
        if return_obj.Succeeded():
            print(return_obj.GetOutput())
        else:
            print(return_obj)

def handle_malloc(memory_model, thread):
    handle_malloc_arm(memory_model, thread)

def handle_free(memory_model, thread):
    handle_free_arm(memory_model, thread)

def handle_malloc_arm(memory_model, thread):

    debug_handle_malloc = True

    # determine if this is the target code's call to malloc
    if debug_handle_malloc:
        print("Handle malloc\n\tstack:")
        for fidx, f in enumerate(thread.frames):
            print("\t\tF[%d]: %s %s" %(fidx, thread.frames[fidx].GetFunctionName(), thread.frames[fidx].GetLineEntry()))

    # malloc's size argument is put in register x0
    x0 = thread.GetSelectedFrame().FindRegister("x0")
    error = lldb.SBError()
    malloc_size = x0.GetData().GetUnsignedInt64(error, 0)

    # advance the thread back to the calling function
    thread.StepOut()

    # malloc's size argument is returned in register x0
    x0 = thread.GetSelectedFrame().FindRegister("x0")
    malloc_ptr = x0.GetData().GetUnsignedInt64(error, 0)
    memory_model.add_heap_alloc(malloc_ptr, malloc_size)

    if debug_handle_malloc:
        print("\tmalloc addr:0x%x size:%lu" % (malloc_ptr, malloc_size))
        print("\treturned to", thread.GetSelectedFrame().GetFunctionName())

def handle_free_arm(memory_model, thread):

    # malloc's size argument is put in register x0
    x0 = thread.GetSelectedFrame().FindRegister("x0")
    error = lldb.SBError()
    free_ptr = x0.GetData().GetUnsignedInt64(error, 0)
    memory_model.add_heap_alloc(free_ptr, 0)

    # advance the thread back to the calling function
    thread.StepOut()
    
    print("\tfree addr:0x%x" % (free_ptr))
