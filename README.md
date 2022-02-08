# Meminspect

Write the contents of memory for short, simple programs using lldb's python API.

## Usage

This will dump memory as a .tsv file once execution hits line 12 of demo.c

```
PYTHONPATH=/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python python3 meminspect.py ./demo demo.c 12
```

## Notes

This will only work on MacOS. Debug symbols must be turned on when compiling the program to profile.
