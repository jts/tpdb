# Tiny program debugger (tpdb)

This is a small set of tools based on llbd's excellent python API to debug tiny (<50 loc) C programs. It is indended to aid learning C programming for the first time, by displaying how the step-by-step execution of a program changes the state of the values stored in the stack and heap. `tpdb.py` is a curses program that allows the user to interactive step through the program. `meminspect.py` is a non-interactive program that writes out the state of memory after n steps of execution.

The `examples` directory contains small C programs that can be used to demonstrate the functionality.

## Usage

First, compile the program you wish to debug. Debugging symbols must be turned on:

```
gcc -Wall -g -o example/demo example/demo.c
```

To launch curses-based debugger (`tbdb.py`) run:

```
python3 src/tpdb.py example/demo
```

To launch a non-interactive memory dump after 10 steps of execution, run:

```
python3 src/meminpsect.py example/demo 10
```

## Dependencies

`lldb` must be installed and with its python API built. On MacOS if you have xcode installed you'll likely already have it. On linux, you should be able to install it through your package manager.

## Notes/Known Issues

If you receive lldb import errors you need to set PYTHONPATH to location of lldb python modules. This package uses a script from Apple to automatically determine where these modules live but it doesn't work consistently on linux so you may need to set this manually.

If you receive an error during launch that `lldb-server` cannot be found, set this environemnt variable: `export LLDB_DEBUGSERVER_PATH=/usr/lib/llvm-6.0/bin/lldb-server` (you may need to change the path depending on your version of llvm).

## Credit

`import_lldb.py` is from: https://opensource.apple.com/source/lldb/lldb-300.2.47/utils/vim-lldb/python-vim-lldb/import_lldb.py.auto.html.

Development relied heavily on the examples and documentation contained within lldb's repo.
