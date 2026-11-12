# Stage C, slice C0 — native build for the GPU capability probe APK.
#
# Builds upstream's pinned SDL 3.4.16 (shared, as SDL's own Android layout
# expects: SDLActivity loads "SDL3" then "main") plus libmain.so from the
# unmodified probe and the Android harness shim. SDL_SOURCE_DIR is supplied
# by the workflow and points at the hash-verified SDL 3.4.16 source tree
# (the exact archive Reforged's Tools/vendor.sh pins).

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
set_source_files_properties(${CMAKE_CURRENT_SOURCE_DIR}/sdl_gpu_probe.cpp
    PROPERTIES COMPILE_OPTIONS "-Dmain=probe_main")

target_link_libraries(main PRIVATE SDL3-shared log)
