# linux-cpp-crash-report

## Build

```
make clean
make

```

<br />

## Example

```
./hello
Segmentation fault

```

<br />

## Analyze

```
chmod +x analyze_crash.py
./analyze_crash.py dump/crash_20261122_170233.log
========================================
[CRASH REPORT]
Time   : 2026-11-22 17:02:33
Signal : 11
PID    : 136611
========================================
Binary : /home/jaytwo/workspace/coredump/hello
========================================
Analyzed Call Stack:

#0  ./workspace/coredump/hello(_ZN5Linux13CrashReporter9on_signalEi+0x169)[0x40165d]
    -> 함수: Linux::CrashReporter::on_signal(int)
    -> 위치: /home/jaytwo/workspace/coredump/main.cpp:206
    --------------------------------------------------
         203 |         }
         204 |
         205 |         void* callstack[64];
    >>>  206 |         const int frames = backtrace(callstack, 64);
         207 |         backtrace_symbols_fd(callstack, frames, fd);
         208 |
         209 |         if (fd != STDERR_FILENO) {
    --------------------------------------------------
#1  /lib64/libc.so.6(+0x375f0)[0x7e60c7c375f0]
#2  ./workspace/coredump/hello[0x400f16]
    -> 함수: (anonymous namespace)::trigger_crash()
    -> 위치: /home/jaytwo/workspace/coredump/main.cpp:227
    --------------------------------------------------
         224 |
         225 | void trigger_crash() {
         226 |     int* ptr = nullptr; // Initialize pointer to nullptr
    >>>  227 |     *ptr = 10; // crashes the program because ptr is nullptr and dereferencing it is undefined behavior
         228 | }
         229 |
         230 | } // namespace
    --------------------------------------------------
#3  ./workspace/coredump/hello(main+0x7f)[0x400f9e]
    -> 함수: main
    -> 위치: /home/jaytwo/workspace/coredump/main.cpp:257
    --------------------------------------------------
         254 |
         255 |     trigger_crash(); // This will cause a segmentation fault and invoke the crash reporter
         256 |
    >>>  257 |     return 0;
         258 | }
    --------------------------------------------------
#4  /lib64/libc.so.6(__libc_start_main+0xe5)[0x7e60c7c235c5]
#5  ./workspace/coredump/hello(_start+0x2e)[0x400e4e]
    -> 심볼/라인 정보 없음 (_start @ ??:?)
	
```



