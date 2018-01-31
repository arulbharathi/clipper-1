# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.9

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:


#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:


# Remove some rules from gmake that .SUFFIXES does not remove.
SUFFIXES =

.SUFFIXES: .hpux_make_needs_suffix_list


# Suppress display of executed commands.
$(VERBOSE).SILENT:


# A target that is always out of date.
cmake_force:

.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /Applications/CLion.app/Contents/bin/cmake/bin/cmake

# The command to remove a file.
RM = /Applications/CLion.app/Contents/bin/cmake/bin/cmake -E remove -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /Users/tim/Documents/Clipper_proj/clipper

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug

# Include any dependencies generated for this target.
include src/management/CMakeFiles/management_frontend.dir/depend.make

# Include the progress variables for this target.
include src/management/CMakeFiles/management_frontend.dir/progress.make

# Include the compile flags for this target's objects.
include src/management/CMakeFiles/management_frontend.dir/flags.make

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o: src/management/CMakeFiles/management_frontend.dir/flags.make
src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o: ../src/management/src/management_frontend_main.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o"
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management && /Library/Developer/CommandLineTools/usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o -c /Users/tim/Documents/Clipper_proj/clipper/src/management/src/management_frontend_main.cpp

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.i"
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management && /Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /Users/tim/Documents/Clipper_proj/clipper/src/management/src/management_frontend_main.cpp > CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.i

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.s"
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management && /Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /Users/tim/Documents/Clipper_proj/clipper/src/management/src/management_frontend_main.cpp -o CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.s

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.requires:

.PHONY : src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.requires

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.provides: src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.requires
	$(MAKE) -f src/management/CMakeFiles/management_frontend.dir/build.make src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.provides.build
.PHONY : src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.provides

src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.provides.build: src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o


# Object files for target management_frontend
management_frontend_OBJECTS = \
"CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o"

# External object files for target management_frontend
management_frontend_EXTERNAL_OBJECTS =

src/management/management_frontend: src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o
src/management/management_frontend: src/management/CMakeFiles/management_frontend.dir/build.make
src/management/management_frontend: src/libclipper/libclipperd.a
src/management/management_frontend: src/libs/redox/libredoxd.0.3.0.dylib
src/management/management_frontend: /usr/local/lib/libhiredis.dylib
src/management/management_frontend: /usr/local/lib/libev.dylib
src/management/management_frontend: /usr/local/lib/libboost_thread-mt.a
src/management/management_frontend: /usr/local/lib/libboost_system-mt.a
src/management/management_frontend: /usr/local/lib/libboost_chrono-mt.a
src/management/management_frontend: /usr/local/lib/libboost_date_time-mt.a
src/management/management_frontend: /usr/local/lib/libboost_atomic-mt.a
src/management/management_frontend: /usr/local/lib/libfolly.dylib
src/management/management_frontend: /usr/local/lib/libzmq.dylib
src/management/management_frontend: src/management/CMakeFiles/management_frontend.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Linking CXX executable management_frontend"
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management && $(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/management_frontend.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
src/management/CMakeFiles/management_frontend.dir/build: src/management/management_frontend

.PHONY : src/management/CMakeFiles/management_frontend.dir/build

src/management/CMakeFiles/management_frontend.dir/requires: src/management/CMakeFiles/management_frontend.dir/src/management_frontend_main.cpp.o.requires

.PHONY : src/management/CMakeFiles/management_frontend.dir/requires

src/management/CMakeFiles/management_frontend.dir/clean:
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management && $(CMAKE_COMMAND) -P CMakeFiles/management_frontend.dir/cmake_clean.cmake
.PHONY : src/management/CMakeFiles/management_frontend.dir/clean

src/management/CMakeFiles/management_frontend.dir/depend:
	cd /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /Users/tim/Documents/Clipper_proj/clipper /Users/tim/Documents/Clipper_proj/clipper/src/management /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management /Users/tim/Documents/Clipper_proj/clipper/cmake-build-debug/src/management/CMakeFiles/management_frontend.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : src/management/CMakeFiles/management_frontend.dir/depend
