cmake_minimum_required(VERSION 3.20.0)
project(hatch-cpp-test-project-basic VERSION "0.1.0")
set(CMAKE_CXX_STANDARD 20)
include(CheckCCompilerFlag)
include(CheckLinkerFlag)

if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    set(WIN32 ON)
    set(MACOS OFF)
    set(LINUX OFF)
elseif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    set(WIN32 OFF)
    set(MACOS ON)
    set(LINUX OFF)
else()
    set(WIN32 OFF)
    set(MACOS OFF)
    set(LINUX ON)
endif()

option(CMAKE_BUILD_TYPE "Release/Debug build" RELEASE)
option(HATCH_CPP_TEST_PROJECT_BASIC_BUILD_TESTS "Build tests" OFF)
option(HATCH_CPP_TEST_PROJECT_BASIC_MANYLINUX "Build for python's manylinux setup" OFF)

string(TOLOWER "${CMAKE_BUILD_TYPE}" CMAKE_BUILD_TYPE_LOWER)

set(BUILD_SHARED_LIBS TRUE)
set(CMAKE_MACOSX_RPATH TRUE)
set(CMAKE_SKIP_RPATH FALSE)
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(CMAKE_INSTALL_NAME_DIR "@rpath")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

string(REGEX REPLACE "[ ]*-O[^ ]+[ ]*" " " CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
string(REGEX REPLACE "[ ]*-Wl,-O2 -Wl,[^ ]+[ ]*" " " CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS}")
string(REGEX REPLACE "[ ]*-Wl,-O2 -Wl,[^ ]+[ ]*" " " CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS}")


if(MACOS)
    set(CMAKE_THREAD_LIBS_INIT "-lpthread")
    set(CMAKE_HAVE_THREADS_LIBRARY 1)
    set(CMAKE_USE_WIN32_THREADS_INIT 0)
    set(CMAKE_USE_PTHREADS_INIT 1)
    set(THREADS_PREFER_PTHREAD_FLAG ON)
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -undefined dynamic_lookup")
endif()


if(MACOS)
    set(CMAKE_INSTALL_RPATH "@loader_path/")
elseif(LINUX)
    set(CMAKE_INSTALL_RPATH "\$ORIGIN")
endif()

if(WIN32)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /EHsc /MP /bigobj")
    foreach(warning 4244 4251 4267 4275 4290 4786 4305 4996)
        SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /wd${warning}")
    endforeach(warning)
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    -g \
    -Wall \
    -Werror \
    -Wno-deprecated-declarations \
    -Wno-deprecated \
    ")
endif()


find_package(Python ${CSP_PYTHON_VERSION} EXACT REQUIRED COMPONENTS Interpreter Development.Module)
link_directories(${Python_LIBRARY_DIRS})
include_directories(${Python_INCLUDE_DIRS})

set(CMAKE_SHARED_LIBRARY_PREFIX "")
if(NOT WIN32)
    set(CMAKE_SHARED_LIBRARY_SUFFIX .so)
else()
    set(CMAKE_SHARED_LIBRARY_SUFFIX .pyd)
endif()

include_directories("${CMAKE_SOURCE_DIR}/cpp")

add_library(extension SHARED cpp/project/basic.cpp)
set_target_properties(extension PROPERTIES PUBLIC_HEADER cpp/project/basic.hpp)
install(TARGETS extension
        PUBLIC_HEADER DESTINATION project/include/project
        RUNTIME DESTINATION project/
        LIBRARY DESTINATION project/
       )
