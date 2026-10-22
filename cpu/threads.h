/* Minimal portable thread pool: run fn(arg_i) on n threads and join. */
#pragma once
#ifdef _WIN32
#include <windows.h>
typedef DWORD(WINAPI *thread_fn)(LPVOID);
#define THREAD_RET DWORD WINAPI
static void run_threads(int n, LPTHREAD_START_ROUTINE fn, void *args, size_t stride) {
    HANDLE h[256];
    for (int i = 0; i < n; i++) h[i] = CreateThread(NULL, 0, fn, (char *)args + i * stride, 0, NULL);
    WaitForMultipleObjects(n, h, TRUE, INFINITE);
    for (int i = 0; i < n; i++) CloseHandle(h[i]);
}
#else
#include <pthread.h>
#define THREAD_RET void *
static void run_threads(int n, void *(*fn)(void *), void *args, size_t stride) {
    pthread_t t[256];
    for (int i = 0; i < n; i++) pthread_create(&t[i], NULL, fn, (char *)args + i * stride);
    for (int i = 0; i < n; i++) pthread_join(t[i], NULL);
}
#endif
