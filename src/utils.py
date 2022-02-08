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
    for v in frame.variables:
        section_name = v.GetAddress().GetSection().GetName()

        # do not display globals in stack
        if section_name == "__data":
            continue
        
        mv = MemoryValue("stack" + "-" + frame.GetDisplayFunctionName(), int(v.location, 16), v.GetByteSize(), str(v.GetValue()), v.GetName(), str(v.GetType()))
        memory_model.add(mv)
