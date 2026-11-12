#pragma once

#define DEMO_ABI_VERSION 1

#if defined(_WIN32)
#define DEMO_API __declspec(dllexport)
#else
#define DEMO_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

DEMO_API int demo_abi_version(void);
DEMO_API int demo_answer(void);

#ifdef __cplusplus
}
#endif
