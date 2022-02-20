import curses

class Dimension:
    def __init__(self, x, y, height, width):
        self.x = x
        self.y = y
        self.height = height
        self.width = width

class MemoryWindow:
    def __init__(self, x_start, y_start, height, section_name):
        border_width = 1
    
        addr_width = 22

        line_num = 0 # debug
        self.addr_window = curses.newwin(height, addr_width, y_start, x_start)
        self.addr_window.border(0, 0, 0, 0, 0, curses.ACS_TTEE, 0, curses.ACS_BTEE)
        self.addr_window.addstr(line_num, 2 + border_width, " " + section_name + " ")
        self.addr_window.addstr(line_num + border_width, 1 + border_width, "0x000000016fdffb80")

        x_start += addr_width
        value_width = 12
        self.value_window = curses.newwin(height, value_width, y_start, x_start)
        self.value_window.border(' ', 0, 0, 0, curses.ACS_HLINE, curses.ACS_TTEE, curses.ACS_HLINE, curses.ACS_BTEE)
        self.value_window.addstr(line_num + border_width, 1, "5213")
        
        x_start += value_width
        label_width = 12
        self.label_window = curses.newwin(height, label_width, y_start, x_start)
        self.label_window.border(' ', 0, 0, 0, curses.ACS_HLINE, 0, curses.ACS_HLINE, 0)
        self.label_window.addstr(line_num + border_width, 1 + border_width, "x")

    def draw(self):
        self.addr_window.refresh()
        self.value_window.refresh()
        self.label_window.refresh()

def demomain(stdscr):
    # Clear screen
    #stdscr.clear()
    
    code_dims = Dimension(0, 0, 20, 80)
    code_win = curses.newwin(code_dims.height, code_dims.width, code_dims.y, code_dims.x)

    memory_dims = Dimension(code_dims.width, 0, 20, 60)
    memory_win = curses.newwin(memory_dims.height, memory_dims.width, memory_dims.y, memory_dims.x)

    code_win.addstr(1, 1, "code line 1")
    code_win.addstr(2, 1, "code line 2")
    code_win.border()
    memory_win.addstr(1, 1, "memory line 1")
    memory_win.addstr(2, 1, "memory line 2")
    memory_win.border()

    code_win.refresh()
    memory_win.refresh()
    #stdscr.refresh()
    code_win.getkey()

def main(stdscr):
    border = 1
    base_height = 40
    code_width = 80
    code_dims = Dimension(0, 0, base_height + 2*border, code_width)
    code_win = curses.newwin(code_dims.height, code_dims.width, code_dims.y, code_dims.x)
    code_win.addstr(1, 1, "code line 1")
    code_win.addstr(2, 1, "code line 2")
    code_win.border()

    mem_x_start = code_width
    heap_height = 20
    heap = MemoryWindow(mem_x_start, 0, heap_height, "Heap")

    stack_height = 10
    stack = MemoryWindow(mem_x_start, heap_height, stack_height, "Stack")
    
    heap.draw()
    stack.draw()
    code_win.getkey()

curses.wrapper(main)
