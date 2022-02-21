# Meminspect

Write the contents of memory for short, simple programs using lldb's python API.

## Usage

First, compile the demo program with debugging symbols turned on:

```
gcc -Wall -g -o example/demo example/demo.c
```

Launch curses-based debugger:

```
python3 src/tpdb.py example/demo
```

## Notes

If you receive lldb import errors you need to set PYTHONPATH to location of lldb python modules. This seems to not be set consistently on some linux distros. If you receive a launch error about "lldb-server" set this environment variable: `export LLDB_DEBUGSERVER_PATH=/usr/lib/llvm-6.0/bin/lldb-server` (you may need to change the path depending on your version of llvm).

## Credit

This package re-uses parts of `heap.py` from lldb's examples. `import_lldb.py` is from: https://opensource.apple.com/source/lldb/lldb-300.2.47/utils/vim-lldb/python-vim-lldb/import_lldb.py.auto.html.
