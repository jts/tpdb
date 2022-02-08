# Meminspect

Write the contents of memory for short, simple programs using lldb's python API.

## Usage

First, compile the demo program with debugging symbols turned on:

```
gcc -Wall -g -o example/demo example/demo.c
```

This will dump memory as a .tsv file once execution hits line 12 of demo.c

```
python3 src/meminspect.py example/demo demo.c 12 | column -t
```

## Notes

This will only work on MacOS. 

## Credit

This package re-uses parts of `heap.py` from lldb's examples. `import_lldb.py` is from: https://opensource.apple.com/source/lldb/lldb-300.2.47/utils/vim-lldb/python-vim-lldb/import_lldb.py.auto.html.
