cmake_minimum_required(VERSION 3.20.0)
project(hatch-cpp-test-project-cmake-c-abi VERSION "0.1.0" LANGUAGES C)

set(CMAKE_INSTALL_NAME_DIR "@rpath")

add_library(demo SHARED cpp/demo.c)
target_include_directories(demo PUBLIC "${CMAKE_SOURCE_DIR}/cpp/include")
target_compile_definitions(demo PRIVATE DEMO_BUILD)
set_target_properties(demo PROPERTIES PUBLIC_HEADER cpp/include/demo/demo.h)
install(TARGETS demo
        LIBRARY DESTINATION project/lib
        RUNTIME DESTINATION project/lib
        ARCHIVE DESTINATION project/lib
        PUBLIC_HEADER DESTINATION project/include/demo
       )

find_package(Python ${HATCH_CPP_TEST_PROJECT_CMAKE_C_ABI_PYTHON_VERSION} EXACT REQUIRED COMPONENTS Interpreter Development.Module)
python_add_library(extension MODULE WITH_SOABI cpp/extension.c)
target_link_libraries(extension PRIVATE demo)
if(APPLE)
    set_target_properties(extension PROPERTIES INSTALL_RPATH "@loader_path/lib")
elseif(UNIX)
    set_target_properties(extension PROPERTIES INSTALL_RPATH "\$ORIGIN/lib")
endif()
install(TARGETS extension
        LIBRARY DESTINATION project
        RUNTIME DESTINATION project
       )
