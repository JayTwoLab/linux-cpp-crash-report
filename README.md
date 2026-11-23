# linux-cpp-crash-report

## Build example

- Create crash program (`main.cpp`)
```cpp
namespace {
    void trigger_crash() {
        int* ptr = nullptr; // Initialize pointer to nullptr
        *ptr = 10; // crashes the program because ptr is nullptr and dereferencing it is undefined behavior
    }
} // namespace
```

- Build example
```bash
make clean
make

ls hello
hello

```

<br />

## Run example

- Run `hello`
   - `hello` is a **crashing** program.
```bash
./hello
Segmentation fault

```

<br />

- `dump` path will be created.
```bash
ls dump
crash_20261123_163244.log 

```

<br />

## Analyze

- `analyze_crash.py`
```py
# Default executable path (can be overridden with a command-line argument)
DEFAULT_BIN = "/home/jaytwo/workspace/github/linux-cpp-crash-report/hello"

```

- analyze crash log
```bash
$ chmod +x analyze_crash.py
$ ./analyze_crash.py dump/crash_20261123_163244.log 
========================================
[CRASH REPORT]
Time   : 2026-11-23 16:32:44
Signal : 11
PID    : 7462
========================================
Binary : /home/jaytwo/workspace/coredump/hello
========================================
Analyzed Call Stack:

#0  ./hello(_ZN5Linux13CrashReporter9on_signalEi+0x169)[0x40165d]
    -> Function: Linux::CrashReporter::on_signal(int)
    -> Location: /home/jaytwo/workspace/coredump/main.cpp:206
    --------------------------------------------------
         203 |         }
         204 | 
         205 |         void* callstack[64];
    >>>  206 |         const int frames = backtrace(callstack, 64);
         207 |         backtrace_symbols_fd(callstack, frames, fd);
         208 | 
         209 |         if (fd != STDERR_FILENO) {
    --------------------------------------------------
#1  /lib64/libc.so.6(+0x375f0)[0x714f41c375f0]
#2  ./hello[0x400f16]
    -> Function: (anonymous namespace)::trigger_crash()
    -> Location: /home/jaytwo/workspace/coredump/main.cpp:227
    --------------------------------------------------
         224 | 
         225 | void trigger_crash() {
         226 |     int* ptr = nullptr; // Initialize pointer to nullptr
    >>>  227 |     *ptr = 10; // crashes the program because ptr is nullptr and dereferencing it is undefined behavior
         228 | }
         229 | 
         230 | } // namespace
    --------------------------------------------------
#3  ./hello(main+0x7f)[0x400f9e]
    -> Function: main
    -> Location: /home/jaytwo/workspace/coredump/main.cpp:257
    --------------------------------------------------
         254 | 
         255 |     trigger_crash(); // This will cause a segmentation fault and invoke the crash reporter
         256 | 
    >>>  257 |     return 0;
         258 | }
    --------------------------------------------------
#4  /lib64/libc.so.6(__libc_start_main+0xe5)[0x714f41c235c5]
#5  ./hello(_start+0x2e)[0x400e4e]
    -> No symbol or line information (_start @ ??:?)
	
	
```



