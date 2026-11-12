# Stage C, slices C0 + C2 — native build for the GPU probe harness APK.
#
# Builds upstream's pinned SDL 3.4.16 (shared, as SDL's own Android layout
# expects: SDLActivity loads "SDL3" then "main") plus libmain.so from the
# unmodified probe and the Android harness shim. SDL_SOURCE_DIR is supplied
# by the workflow and points at the hash-verified SDL 3.4.16 source tree
# (the exact archive Reforged's Tools/vendor.sh pins).
#
# C2 note: the renderer harness's payloads (the engine selfchecks) are NOT
# built here — the workflow builds them from the pinned Reforged tree with
# the C1 route and build-apk.sh packages them next to this library; the
# shim only locates (dladdr) and runs them as child processes.

cmake_minimum_required(VERSION 3.22)
project(reforged_gpu_probe)

if(NOT DEFINED SDL_SOURCE_DIR)
    message(FATAL_ERROR "SDL_SOURCE_DIR must point at the pinned SDL 3.4.16 source tree")
endif()

set(SDL_SHARED ON CACHE BOOL "" FORCE)
set(SDL_STATIC OFF CACHE BOOL "" FORCE)
set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
set(SDL_TESTS OFF CACHE BOOL "" FORCE)
set(SDL_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory(${SDL_SOURCE_DIR} ${CMAKE_BINARY_DIR}/sdl)

add_library(main SHARED
    ${CMAKE_CURRENT_SOURCE_DIR}/sdl_gpu_probe.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/gpu_probe_shim.cpp)
set_target_properties(main PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

# Harness mechanics ONLY: the probe translation unit is compiled with its
# `main` renamed to `probe_main`, so the shim's SDL_main can invoke it and
# capture its stdout. The probe source file itself stays byte-identical to
# upstream (SHA-256-verified in the workflow before this build runs).
#
# Device-creation mode (PROBE_DEVICE_MODE, set by the workflow's
# device_mode input):
#   plain  — the probe calls SDL_CreateGPUDevice with SDL's documented
#            defaults, which require the Vulkan core features depthClamp
#            and shaderClipDistance. On the owner's Mali-G52 (neither
#            feature implemented) that fails in SDL's PrepareDriver with
#            "No supported SDL_GPU backend found!" (record §8).
#   compat — the probe TU additionally gets
#            -DSDL_CreateGPUDevice=probe_compat_create_gpu_device, so its
#            creation call is routed to the harness shim's forwarder,
#            which creates the device via SDL_CreateGPUDeviceWithProperties
#            with the depth-clamping and clip-distance feature properties
#            set false (SDL_gpu.h:2380-2381) and the caller's format
#            flags, debug flag and name passed through. Same compile-time
#            rename family as the `main` rename; the probe source is
#            byte-identical in both modes.
set(PROBE_DEVICE_MODE "plain" CACHE STRING "probe device creation mode: plain|compat")
set_property(CACHE PROBE_DEVICE_MODE PROPERTY STRINGS plain compat)
if(NOT PROBE_DEVICE_MODE STREQUAL "plain" AND NOT PROBE_DEVICE_MODE STREQUAL "compat")
    message(FATAL_ERROR "PROBE_DEVICE_MODE must be 'plain' or 'compat', got '${PROBE_DEVICE_MODE}'")
endif()
message(STATUS "probe device mode: ${PROBE_DEVICE_MODE}")

set(PROBE_TU_OPTIONS "-Dmain=probe_main")
if(PROBE_DEVICE_MODE STREQUAL "compat")
    list(APPEND PROBE_TU_OPTIONS "-DSDL_CreateGPUDevice=probe_compat_create_gpu_device")
    set_source_files_properties(${CMAKE_CURRENT_SOURCE_DIR}/gpu_probe_shim.cpp
        PROPERTIES COMPILE_DEFINITIONS "PROBE_DEVICE_COMPAT=1")
endif()
set_source_files_properties(${CMAKE_CURRENT_SOURCE_DIR}/sdl_gpu_probe.cpp
    PROPERTIES COMPILE_OPTIONS "${PROBE_TU_OPTIONS}")

# dl: dladdr, which the shim uses to locate the C2 selfcheck payloads
# packaged next to this library.
target_link_libraries(main PRIVATE SDL3-shared log dl)
