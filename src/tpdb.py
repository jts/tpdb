#! /usr/bin/env python

from import_lldb import *
import curses
from memory_value import *
from utils import *

border_width = 1
addr_width = 22
label_width = 12
value_width = addr_width

def pad_or_truncate(s, max_length):
    if len(s) > max_length:
        return s[0:max_length]
    else:
        return s.ljust(max_length)

class Dimension:
    def __init__(self, x, y, height, width):
        self.x = x
        self.y = y
        self.height = height
        self.width = width

class CodeWindow:
    def __init__(self, x_start, y_start, width, height):
        self.max_lines = height - 2*border_width - 2
        self.max_line_length = width - 2 * border_width - 1

        code_dims = Dimension(0, 0, height, width)
        self.window = curses.newwin(code_dims.height, code_dims.width, code_dims.y, code_dims.x)
        self.width = width

        self.init()

    def init(self):
        self.window.clear()
        self.window.border()

    def update_title(self, title):
        self.window.addstr(0, 2, " %s " % (title))
    
    def update_code(self, lines, current_line_number):
        for c, l in enumerate(lines):
        
            prefix = "  "
            if c == current_line_number - 1:
                prefix = "->"
            l = pad_or_truncate(prefix + l, self.max_line_length)
            self.window.addstr(2 + c, 1, l)
    
    def draw(self):
        self.window.refresh()

class OutputWindow:
    def __init__(self, x_start, y_start, width, height, name):
        self.max_lines = height - 2*border_width
        self.max_line_length = width - 2 * border_width - 1

        dims = Dimension(x_start, y_start, height, width)
        self.window = curses.newwin(dims.height, dims.width, dims.y, dims.x)
        self.width = width
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, " %s " % (name))

    def update(self, lines ):
        lines = lines[-self.max_lines:]

        for c, l in enumerate(lines):
            l = pad_or_truncate(l, self.max_line_length)
            self.window.addstr(1 + c, 1, l)
   
    def draw(self):
        self.window.refresh()


class MemoryWindow:
    def __init__(self, x_start, y_start, height, section_name):
        line_num = 0
        self.max_lines = height - 2 * border_width
        self.addr_window = curses.newwin(height, addr_width, y_start, x_start)
        self.max_addr_length = addr_width - 2 * border_width - 2

        x_start += addr_width
        self.value_window = curses.newwin(height, value_width, y_start, x_start)
        self.max_value_length = value_width - 2 * border_width - 2
        
        x_start += value_width
        self.label_window = curses.newwin(height, label_width, y_start, x_start)
        self.max_label_length = label_width - 2 * border_width - 2

        # write titles
        self.addr_window.border(0, 0, 0, 0, 0, curses.ACS_TTEE, 0, curses.ACS_BTEE)
        self.value_window.border(' ', 0, 0, 0, curses.ACS_HLINE, curses.ACS_TTEE, curses.ACS_HLINE, curses.ACS_BTEE)
        self.label_window.border(' ', 0, 0, 0, curses.ACS_HLINE, 0, curses.ACS_HLINE, 0)
        
        self.addr_window.addstr(0, 2, " " + section_name + " ")

    @staticmethod
    def get_width():
        return addr_width + value_width + label_width

    def draw(self):
        self.addr_window.refresh()
        self.value_window.refresh()
        self.label_window.refresh()

    def set(self, idx, value):

        if idx >= self.max_lines:
            return

        astr = pad_or_truncate(value.get_addr_as_str(), self.max_addr_length)
        self.addr_window.addstr(idx + border_width, 1 + border_width, astr)
        
        vstr = pad_or_truncate(value.get_value_as_str(), self.max_value_length)
        self.value_window.addstr(idx + border_width, 1, vstr)

        lstr = pad_or_truncate(value.get_label_as_str(), self.max_label_length)
        self.label_window.addstr(idx + border_width, 1, lstr)


def main(stdscr, program):

    # initialize windows
    code_height = 36
    code_width = curses.COLS - MemoryWindow.get_width()
    stack_height = 18

    output_height = 5
    command_height = 1
    fixed_element_height = output_height + command_height
    code_height = curses.LINES - fixed_element_height
    heap_height = int(code_height / 2)
    stack_height = code_height - heap_height

    # hide cursor
    curses.curs_set(0)

    # Code
    code_window = CodeWindow(0, 0, code_width, code_height)

    # Memory
    mem_x_start = code_width
    heap_window = MemoryWindow(mem_x_start, 0, heap_height, "heap")

    stack_window = MemoryWindow(mem_x_start, heap_height, stack_height, "stack")
 
    # Output
    output_window = OutputWindow(0, code_height, code_width + MemoryWindow.get_width(), output_height, "stdout")

    stdscr.addstr(code_height +  output_height, 0, " Press ENTER to advance line")
    stdscr.refresh()
    memory_model = MemoryModel()
    
    while True:

        # Update UI
        
        # Code
        code = program.get_code()
        ln = program.get_line_number()
        code_window.update_title(program.line_entry.GetFileSpec().GetFilename())
        code_window.update_code(code, ln)

        # Memory
        heap_count = 0
        stack_count = 0
        for v in memory_model.get_ordered():
            if v.section == "heap":
                heap_window.set(heap_count, v)
                heap_count += 1
            else:
                stack_window.set(stack_count, v)
                stack_count += 1

        # Output
        output_window.update(program.stdout)

        heap_window.draw()
        stack_window.draw()
        code_window.draw()
        output_window.draw()

        #key = code_window.window.getstr()
        key = code_window.window.getch()
        program.step(memory_model)
        curses.napms(50)
 
#       
program = ProgramState(sys.argv[1])
curses.wrapper(main, program)
