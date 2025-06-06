#---------------------------------------------------
# OpenMM
#
# Creates OpenMM library.
#
# Windows:
#   OpenMM.dll
#   OpenMM.lib
#   OpenMM_static.lib
# Unix:
#   libOpenMM.so
#   libOpenMM_static.a
#----------------------------------------------------

find_package(PythonInterp)
mark_as_advanced(CLEAR PYTHON_EXECUTABLE)

# Don't create a new project name if this is part of a mega-build from the
# parent directory
IF( NOT PROJECT_NAME )
    PROJECT (OpenMM)
ENDIF( NOT PROJECT_NAME )

CMAKE_MINIMUM_REQUIRED(VERSION 3.17)
CMAKE_POLICY(SET CMP0042 NEW)
CMAKE_POLICY(SET CMP0003 NEW)
CMAKE_POLICY(SET CMP0005 NEW)
CMAKE_POLICY(SET CMP0011 NEW)

include(CTest)

# We have custom cmake modules for FindOpenMM and running python tests
SET(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake_modules")

# Determine what architecture we are compiling for.
INCLUDE(TargetArch)
target_architecture(TARGET_ARCH)
if ("${TARGET_ARCH}" MATCHES "x86_64|i386")
    set(X86 ON)
endif()
if ("${TARGET_ARCH}" MATCHES "arm")
    set(ARM ON)
    # OpenMM only supports 64-bit ARM
    add_definitions(-D__ARM64__=1)
endif()
if ("${TARGET_ARCH}" MATCHES "ppc")
    set(PPC ON)
    add_definitions(-D__PPC__=1)
endif()
if ("${TARGET_ARCH}" MATCHES "loongarch64")
    set(LOONGARCH64 ON)
    add_definitions(-D__LOONGARCH64__=1 -mlsx)
endif()


# Where to install
IF(WIN32)
    IF(NOT OPENMM_INSTALL_PREFIX)
        SET(OPENMM_INSTALL_PREFIX "$ENV{ProgramFiles}/OpenMM")
    ENDIF(NOT OPENMM_INSTALL_PREFIX)
ELSE(WIN32)
    IF(NOT OPENMM_INSTALL_PREFIX)
        SET(OPENMM_INSTALL_PREFIX "/usr/local/openmm")
    ENDIF(NOT OPENMM_INSTALL_PREFIX)
ENDIF(WIN32)

IF(WIN32)
    ADD_DEFINITIONS(-DWIN32)
ENDIF(WIN32)

# What type of libraries to build
SET(OPENMM_BUILD_SHARED_LIB ON CACHE BOOL "Whether to build shared OpenMM libraries")
SET(OPENMM_BUILD_STATIC_LIB OFF CACHE BOOL "Whether to build static OpenMM libraries")

# Include CPU-Features for Android
IF (ANDROID)
    INCLUDE_DIRECTORIES(${ANDROID_NDK}/sources/cpufeatures)
ENDIF (ANDROID)

# It seems that on linux and mac, everything is trying to be installed in /usr/local/openmm
# But if every install target is prefixed with /openmm/, on Windows the install files
# end up in C:/Program Files/OpenMM/openmm/ which is ugly.
# Better to set CMAKE_INSTALL_PREFIX to /usr/local/openmm and leave /openmm/ off the
# install target names.  Plus, the user now has the opportunity to install into /usr/local/
# if she so chooses.  --cmb
IF(${CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT})
  SET(CMAKE_INSTALL_PREFIX ${OPENMM_INSTALL_PREFIX} CACHE PATH "Where to install OpenMM" FORCE)
ENDIF(${CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT})

# The source is organized into subdirectories, but we handle them all from
# this CMakeLists file rather than letting CMake visit them as SUBDIRS.
SET(OPENMM_SOURCE_SUBDIRS . openmmapi olla libraries/jama libraries/quern libraries/lepton libraries/sfmt libraries/lbfgs libraries/hilbert libraries/csha1 libraries/pocketfft libraries/vkfft platforms/reference serialization libraries/irrxml)
IF(X86 OR ARM)
    SET(OPENMM_SOURCE_SUBDIRS ${OPENMM_SOURCE_SUBDIRS} libraries/vecmath)
ENDIF()

SET (CMAKE_CXX_STANDARD 11)

IF(APPLE)
    # Build 64 bit binaries compatible with OS X 10.7
    IF (NOT CMAKE_OSX_DEPLOYMENT_TARGET)
        SET (CMAKE_OSX_DEPLOYMENT_TARGET "10.7" CACHE STRING "The minimum version of OS X to support" FORCE)
    ENDIF (NOT CMAKE_OSX_DEPLOYMENT_TARGET)
    IF (NOT CMAKE_OSX_ARCHITECTURES)
        SET (CMAKE_OSX_ARCHITECTURES "${CMAKE_SYSTEM_PROCESSOR}" CACHE STRING "The processor architectures to build for" FORCE)
    ENDIF (NOT CMAKE_OSX_ARCHITECTURES)
    IF (NOT CMAKE_OSX_SYSROOT)
        EXECUTE_PROCESS(COMMAND "xcrun" "--show-sdk-path" OUTPUT_VARIABLE XCRUN_OSX_SYSROOT RESULT_VARIABLE XCRUN_OSX_SYSROOT_STATUS OUTPUT_STRIP_TRAILING_WHITESPACE)
        IF (XCRUN_OSX_SYSROOT_STATUS EQUAL 0)
            SET (CMAKE_OSX_SYSROOT "${XCRUN_OSX_SYSROOT}" CACHE STRING "SDK Path" FORCE)
        ENDIF (XCRUN_OSX_SYSROOT_STATUS EQUAL 0)
        UNSET(XCRUN_OSX_SYSROOT)
        UNSET(XCRUN_OSX_SYSROOT_STATUS)
    ENDIF (NOT CMAKE_OSX_SYSROOT)

    # Improve the linking behavior of Mac libraries
    SET (CMAKE_INSTALL_NAME_DIR "@rpath")
    IF (X86)
      SET(EXTRA_COMPILE_FLAGS "-msse2")
    ENDIF()
    SET(EXTRA_COMPILE_FLAGS "${EXTRA_COMPILE_FLAGS} -stdlib=libc++")
ELSEIF(MSVC)
    SET(EXTRA_COMPILE_FLAGS)
    # Use warning level 2, not whatever warning level CMake picked.
    STRING(REGEX REPLACE "/W[0-4]" "/W2" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
    # Explicitly suppress warnings 4305 and 4244.
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /wd4305 /wd4244")
ELSEIF(X86)
    SET(EXTRA_COMPILE_FLAGS "-msse2 -pthread")
ELSE()
    SET(EXTRA_COMPILE_FLAGS "-pthread")
ENDIF()

IF(UNIX AND NOT CMAKE_BUILD_TYPE)
    SET(CMAKE_BUILD_TYPE Release CACHE STRING "Debug or Release build" FORCE)
ENDIF (UNIX AND NOT CMAKE_BUILD_TYPE)

IF (NOT CMAKE_CXX_FLAGS_DEBUG)
    SET(CMAKE_CXX_FLAGS_DEBUG "-g" CACHE STRING "To use when CMAKE_BUILD_TYPE=Debug" FORCE)
ENDIF (NOT CMAKE_CXX_FLAGS_DEBUG)

IF (NOT CMAKE_CXX_FLAGS_RELEASE)
    IF (ANDROID)
        SET(CMAKE_CXX_FLAGS_RELEASE "-mfloat-abi=softfp -march=armv7-a -mfpu=neon -funsafe-math-optimizations -O3 -DNDEBUG" CACHE STRING
        "To use when CMAKE_BUILD_TYPE=Release" FORCE)
    ELSE (ANDROID)
        SET(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG" CACHE STRING
        "To use when CMAKE_BUILD_TYPE=Release" FORCE)
    ENDIF (ANDROID)
ENDIF (NOT CMAKE_CXX_FLAGS_RELEASE)



# Collect up information about the version of the OpenMM library we're building
# and make it available to the code so it can be built into the binaries.

SET(OPENMM_LIBRARY_NAME OpenMM)
SET(OPENMM_MAJOR_VERSION 8)
SET(OPENMM_MINOR_VERSION 2)
SET(OPENMM_BUILD_VERSION 0)

ADD_DEFINITIONS(-DOPENMM_LIBRARY_NAME=${OPENMM_LIBRARY_NAME}
                -DOPENMM_MAJOR_VERSION=${OPENMM_MAJOR_VERSION}
                -DOPENMM_MINOR_VERSION=${OPENMM_MINOR_VERSION}
                -DOPENMM_BUILD_VERSION=${OPENMM_BUILD_VERSION})

# -DOPENMM_TYPE has to be defined in the target subdirectories.
# -Dsimbody_EXPORTS defined automatically when Windows DLL build is being done.

# Report the version number to the CMake UI
SET(OPENMM_VERSION
    "${OPENMM_MAJOR_VERSION}.${OPENMM_MINOR_VERSION}.${OPENMM_BUILD_VERSION}"
     CACHE STRING "This is the version of OpenMM which will be built." FORCE)
# We don't actually use this version for anything yet
MARK_AS_ADVANCED(OPENMM_VERSION)

SET(SHARED_TARGET ${OPENMM_LIBRARY_NAME})
SET(STATIC_TARGET ${OPENMM_LIBRARY_NAME}_static)


## If no one says otherwise, change the executable path to drop into the same binary
## location as the DLLs so that the test cases will use the just-build DLLs.
IF(NOT EXECUTABLE_OUTPUT_PATH)
  SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}
      CACHE INTERNAL "Single output directory for building all executables.")
ENDIF(NOT EXECUTABLE_OUTPUT_PATH)
IF(NOT LIBRARY_OUTPUT_PATH)
  SET(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}
      CACHE INTERNAL "Single output directory for building all libraries.")
ENDIF(NOT LIBRARY_OUTPUT_PATH)
SET(${PROJECT_NAME}_EXECUTABLE_DIR ${EXECUTABLE_OUTPUT_PATH}/${CMAKE_CFG_INTDIR})
SET(${PROJECT_NAME}_LIBRARY_DIR    ${LIBRARY_OUTPUT_PATH}/${CMAKE_CFG_INTDIR})

# used by plugin
SET(OPENMM_DIR ${CMAKE_CURRENT_SOURCE_DIR})

# These are all the places to search for header files which are
# to be part of the API.
SET(API_INCLUDE_DIRS) # start empty
FOREACH(subdir ${OPENMM_SOURCE_SUBDIRS})
    # append
    SET(API_INCLUDE_DIRS ${API_INCLUDE_DIRS}
                         ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/include
                         ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/include/openmm
                         ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/include/openmm/internal)
ENDFOREACH(subdir)

# We'll need both *relative* path names, starting with their API_INCLUDE_DIRS,
# and absolute pathnames.
SET(API_REL_INCLUDE_FILES)   # start these out empty
SET(API_ABS_INCLUDE_FILES)

FOREACH(dir ${API_INCLUDE_DIRS})
    FILE(GLOB fullpaths ${dir}/*.h) # returns full pathnames
    SET(API_ABS_INCLUDE_FILES ${API_ABS_INCLUDE_FILES} ${fullpaths})

    FOREACH(pathname ${fullpaths})
        GET_FILENAME_COMPONENT(filename ${pathname} NAME)
        SET(API_REL_INCLUDE_FILES ${API_REL_INCLUDE_FILES} ${dir}/${filename})
    ENDFOREACH(pathname)
ENDFOREACH(dir)

# collect up source files
SET(SOURCE_FILES) # empty
SET(SOURCE_INCLUDE_FILES)

FOREACH(subdir ${OPENMM_SOURCE_SUBDIRS})
    FILE(GLOB src_files  ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/src/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/src/*/*.cpp)
    FILE(GLOB incl_files ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/src/*.h)
    SET(SOURCE_FILES         ${SOURCE_FILES}         ${src_files})   #append
    SET(SOURCE_INCLUDE_FILES ${SOURCE_INCLUDE_FILES} ${incl_files})

    ## Make sure we find these locally before looking in OpenMM/include if
    ## OpenMM was previously installed there.
    INCLUDE_DIRECTORIES(BEFORE ${CMAKE_CURRENT_SOURCE_DIR}/${subdir}/include)
ENDFOREACH(subdir)
IF(X86)
    SET_SOURCE_FILES_PROPERTIES(${CMAKE_SOURCE_DIR}/libraries/sfmt/src/SFMT.cpp PROPERTIES COMPILE_FLAGS "-DHAVE_SSE2=1")
    SET_SOURCE_FILES_PROPERTIES(${CMAKE_SOURCE_DIR}/libraries/lbfgs/src/lbfgs.cpp PROPERTIES COMPILE_FLAGS "-DUSE_SSE=1 -DHAVE_EMMINTRIN_H=1")
ELSE()
    SET_SOURCE_FILES_PROPERTIES(${CMAKE_SOURCE_DIR}/libraries/sfmt/src/SFMT.cpp PROPERTIES COMPILE_FLAGS "-UHAVE_SSE2")
ENDIF()
IF((X86 OR ARM) AND NOT (WIN32 AND OPENMM_BUILD_STATIC_LIB))
    FILE(GLOB src_files ${CMAKE_CURRENT_SOURCE_DIR}/libraries/asmjit/asmjit/*/*.cpp)
    FILE(GLOB incl_files ${CMAKE_CURRENT_SOURCE_DIR}/libraries/asmjit/*.h)
    SET(SOURCE_FILES ${SOURCE_FILES} ${src_files})
    SET(SOURCE_INCLUDE_FILES ${SOURCE_INCLUDE_FILES} ${incl_files})
    INCLUDE_DIRECTORIES(BEFORE "${CMAKE_CURRENT_SOURCE_DIR}/libraries/asmjit")
    SET(EXTRA_COMPILE_FLAGS "${EXTRA_COMPILE_FLAGS} -DLEPTON_USE_JIT")
ENDIF()

# If API wrappers are being generated, and add them to the build.
SET(OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS ON CACHE BOOL "Build wrappers for C and Fortran")
IF(OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS)
    ADD_SUBDIRECTORY(wrappers)
    SET(SOURCE_FILES ${SOURCE_FILES} wrappers/OpenMMCWrapper.cpp  wrappers/OpenMMFortranWrapper.cpp)
    SET_SOURCE_FILES_PROPERTIES(wrappers/OpenMMCWrapper.cpp wrappers/OpenMMFortranWrapper.cpp PROPERTIES GENERATED TRUE)
ENDIF(OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS)

INCLUDE_DIRECTORIES(BEFORE ${CMAKE_CURRENT_SOURCE_DIR}/src)

SET(EXTRA_LINK_FLAGS ${EXTRA_COMPILE_FLAGS})
IF (CMAKE_SYSTEM_NAME MATCHES "Linux")
    IF (NOT ANDROID)
        SET(EXTRA_LINK_FLAGS "${EXTRA_LINK_FLAGS} -Wl,--no-as-needed -lrt")
    ENDIF (NOT ANDROID)
ENDIF (CMAKE_SYSTEM_NAME MATCHES "Linux")
IF (MSVC)
    SET(EXTRA_LINK_FLAGS)
ENDIF (MSVC)

IF(OPENMM_BUILD_SHARED_LIB)
    ADD_LIBRARY(${SHARED_TARGET} SHARED ${SOURCE_FILES} ${SOURCE_INCLUDE_FILES} ${API_ABS_INCLUDE_FILES})
    SET_TARGET_PROPERTIES(${SHARED_TARGET} PROPERTIES LINK_FLAGS "${EXTRA_LINK_FLAGS}" COMPILE_FLAGS "${EXTRA_COMPILE_FLAGS} -DOPENMM_BUILDING_SHARED_LIBRARY -DLEPTON_BUILDING_SHARED_LIBRARY")
ENDIF(OPENMM_BUILD_SHARED_LIB)

IF(OPENMM_BUILD_STATIC_LIB)
    ADD_LIBRARY(${STATIC_TARGET} STATIC ${SOURCE_FILES} ${SOURCE_INCLUDE_FILES} ${API_ABS_INCLUDE_FILES})
    SET(EXTRA_COMPILE_FLAGS "${EXTRA_COMPILE_FLAGS} -DOPENMM_USE_STATIC_LIBRARIES -DLEPTON_USE_STATIC_LIBRARIES -DPTW32_STATIC_LIB")
    SET_TARGET_PROPERTIES(${STATIC_TARGET} PROPERTIES LINK_FLAGS "${EXTRA_LINK_FLAGS}" COMPILE_FLAGS "${EXTRA_COMPILE_FLAGS} -DOPENMM_BUILDING_STATIC_LIBRARY -DLEPTON_BUILDING_STATIC_LIBRARY")
ENDIF(OPENMM_BUILD_STATIC_LIB)

IF(OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS)
    ADD_DEPENDENCIES(${SHARED_TARGET} ApiWrappers)
    IF(OPENMM_BUILD_STATIC_LIB)
        ADD_DEPENDENCIES(${STATIC_TARGET} ApiWrappers)
    ENDIF(OPENMM_BUILD_STATIC_LIB)
ENDIF(OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS)

# On Linux need to link to libdl
IF(NOT APPLE)
    FIND_LIBRARY(DL_LIBRARY dl)
    IF(DL_LIBRARY)
        IF(OPENMM_BUILD_SHARED_LIB)
            TARGET_LINK_LIBRARIES(${SHARED_TARGET} ${DL_LIBRARY})
        ENDIF(OPENMM_BUILD_SHARED_LIB)
        IF(OPENMM_BUILD_STATIC_LIB)
            TARGET_LINK_LIBRARIES(${STATIC_TARGET} ${DL_LIBRARY})
        ENDIF(OPENMM_BUILD_STATIC_LIB)
        MARK_AS_ADVANCED(DL_LIBRARY)
    ELSE(DL_LIBRARY)
        IF(OPENMM_BUILD_SHARED_LIB)
            IF (ANDROID)
                TARGET_LINK_LIBRARIES(${SHARED_TARGET} cpufeatures)
            ELSE (ANDROID)
                TARGET_LINK_LIBRARIES(${SHARED_TARGET})
            ENDIF (ANDROID)
        ENDIF(OPENMM_BUILD_SHARED_LIB)
    ENDIF(DL_LIBRARY)
ENDIF()

IF(BUILD_TESTING)
    INCLUDE_DIRECTORIES(${CMAKE_SOURCE_DIR}/tests)
ENDIF(BUILD_TESTING)

set(OPENMM_BUILD_REFERENCE_TESTS TRUE CACHE BOOL "Whether to build Reference platform test cases")
MARK_AS_ADVANCED(OPENMM_BUILD_REFERENCE_TESTS)
IF(BUILD_TESTING AND OPENMM_BUILD_REFERENCE_TESTS)
    ADD_SUBDIRECTORY(platforms/reference/tests)
ENDIF(BUILD_TESTING AND OPENMM_BUILD_REFERENCE_TESTS)

# CUDA platform

FIND_PACKAGE(CUDAToolkit QUIET)
IF(CUDAToolkit_FOUND)
    SET(OPENMM_BUILD_CUDA_LIB ON CACHE BOOL "Build OpenMMCuda library for Nvidia GPUs")
ELSE(CUDAToolkit_FOUND)
    SET(OPENMM_BUILD_CUDA_LIB OFF CACHE BOOL "Build OpenMMCuda library for Nvidia GPUs")
ENDIF(CUDAToolkit_FOUND)
IF(OPENMM_BUILD_CUDA_LIB)
    ADD_SUBDIRECTORY(platforms/cuda)
ENDIF(OPENMM_BUILD_CUDA_LIB)

# OpenCL platform

FIND_PACKAGE(OpenCL QUIET)
IF(OPENCL_FOUND)
    SET(OPENMM_BUILD_OPENCL_LIB ON CACHE BOOL "Build OpenMMOpenCL library")
ELSE(OPENCL_FOUND)
    SET(OPENMM_BUILD_OPENCL_LIB OFF CACHE BOOL "Build OpenMMOpenCL library")
ENDIF(OPENCL_FOUND)
IF(OPENMM_BUILD_OPENCL_LIB)
    ADD_SUBDIRECTORY(platforms/opencl)
ENDIF(OPENMM_BUILD_OPENCL_LIB)

# HIP platform

LIST(APPEND CMAKE_PREFIX_PATH $ENV{ROCM_PATH} /opt/rocm)
FIND_PACKAGE(HIP CONFIG QUIET)
IF(HIP_FOUND)
    SET(OPENMM_BUILD_HIP_LIB ON CACHE BOOL "Build OpenMMHIP library for AMD GPUs")
ELSE(HIP_FOUND)
    SET(OPENMM_BUILD_HIP_LIB OFF CACHE BOOL "Build OpenMMHIP library for AMD GPUs")
ENDIF(HIP_FOUND)
IF(OPENMM_BUILD_HIP_LIB)
    ADD_SUBDIRECTORY(platforms/hip)
ENDIF(OPENMM_BUILD_HIP_LIB)

# Common compute files

SET(OPENMM_BUILD_COMMON OFF CACHE BOOL "Build common files even if CUDA or OpenCL platforms are not built")

IF(OPENMM_BUILD_CUDA_LIB OR OPENMM_BUILD_OPENCL_LIB OR OPENMM_BUILD_HIP_LIB OR OPENMM_BUILD_COMMON)
    ADD_SUBDIRECTORY(platforms/common)
ENDIF()

# Optimized CPU platform

SET(OPENMM_BUILD_CPU_LIB ON CACHE BOOL "Build optimized CPU platform")
IF(OPENMM_BUILD_CPU_LIB)
   ADD_SUBDIRECTORY(platforms/cpu)
ENDIF(OPENMM_BUILD_CPU_LIB)

# Amoeba plugin

SET(OPENMM_BUILD_AMOEBA_PLUGIN ON CACHE BOOL "Build Amoeba plugin")
SET(OPENMM_BUILD_AMOEBA_PATH)
IF(OPENMM_BUILD_AMOEBA_PLUGIN)
   SET(OPENMM_BUILD_AMOEBA_PATH ${CMAKE_CURRENT_SOURCE_DIR}/plugins/amoeba)
   ADD_SUBDIRECTORY(plugins/amoeba)
ENDIF(OPENMM_BUILD_AMOEBA_PLUGIN)

# RPMD plugin

SET(OPENMM_BUILD_RPMD_PLUGIN ON CACHE BOOL "Build RPMD plugin")
SET(OPENMM_BUILD_RPMD_PATH)
IF(OPENMM_BUILD_RPMD_PLUGIN)
   SET(OPENMM_BUILD_RPMD_PATH ${CMAKE_CURRENT_SOURCE_DIR}/plugins/rpmd)
   ADD_SUBDIRECTORY(plugins/rpmd)
ENDIF(OPENMM_BUILD_RPMD_PLUGIN)

# Drude plugin

SET(OPENMM_BUILD_DRUDE_PLUGIN ON CACHE BOOL "Build Drude plugin")
SET(OPENMM_BUILD_DRUDE_PATH)
IF(OPENMM_BUILD_DRUDE_PLUGIN)
   SET(OPENMM_BUILD_DRUDE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/plugins/drude)
   ADD_SUBDIRECTORY(plugins/drude)
ENDIF(OPENMM_BUILD_DRUDE_PLUGIN)

# CPU PME plugin

SET(OPENMM_BUILD_PME_PLUGIN ON CACHE BOOL "Build CPU PME plugin")
SET(OPENMM_BUILD_PME_PATH)
IF(OPENMM_BUILD_PME_PLUGIN)
   SET(OPENMM_BUILD_PME_PATH ${CMAKE_CURRENT_SOURCE_DIR}/plugins/cpupme)
   ADD_SUBDIRECTORY(plugins/cpupme)
ENDIF(OPENMM_BUILD_PME_PLUGIN)

IF(OPENMM_BUILD_SHARED_LIB)
    INSTALL_TARGETS(/lib RUNTIME_DIRECTORY /lib ${SHARED_TARGET})
ENDIF(OPENMM_BUILD_SHARED_LIB)
IF(OPENMM_BUILD_STATIC_LIB)
  INSTALL_TARGETS(/lib RUNTIME_DIRECTORY /lib ${STATIC_TARGET})
ENDIF(OPENMM_BUILD_STATIC_LIB)
FILE(GLOB CORE_HEADERS     include/*.h          */include/*.h)
FILE(GLOB TOP_HEADERS      include/openmm/*.h          */include/openmm/*.h)
FILE(GLOB INTERNAL_HEADERS include/openmm/internal/*.h */include/openmm/internal/*.h )
FILE(GLOB REFERENCE_HEADERS platforms/reference/include/*.h)
FILE(GLOB LEPTON_HEADERS   libraries/lepton/include/lepton/*.h)
FILE(GLOB SFMT_HEADERS     libraries/sfmt/include/sfmt/SFMT.h)
INSTALL_FILES(/include                 FILES ${CORE_HEADERS})
INSTALL_FILES(/include/openmm          FILES ${TOP_HEADERS})
INSTALL_FILES(/include/openmm/internal FILES ${INTERNAL_HEADERS})
INSTALL_FILES(/include/openmm/reference FILES ${REFERENCE_HEADERS})
INSTALL_FILES(/include/lepton          FILES ${LEPTON_HEADERS})
INSTALL_FILES(/include/sfmt            FILES ${SFMT_HEADERS})

# Serialization support

ADD_SUBDIRECTORY(serialization)
FILE(GLOB serialization_files  ${CMAKE_SOURCE_DIR}/serialization/src/*.cpp)
SET_SOURCE_FILES_PROPERTIES(${serialization_files} PROPERTIES COMPILE_FLAGS "-DOPENMM_BUILDING_SHARED_LIBRARY -DIEEE_8087")

# Python wrappers

SET(OPENMM_BUILD_PYTHON_WRAPPERS ON CACHE BOOL "Build wrappers for Python")
IF(OPENMM_BUILD_PYTHON_WRAPPERS)
    IF(NOT OPENMM_BUILD_AMOEBA_PLUGIN)
        MESSAGE(SEND_ERROR "The Python wrappers require that the AMOEBA plugin be built.")
    ENDIF(NOT OPENMM_BUILD_AMOEBA_PLUGIN)
    IF(NOT OPENMM_BUILD_RPMD_PLUGIN)
        MESSAGE(SEND_ERROR "The Python wrappers require that the RPMD plugin be built.")
    ENDIF(NOT OPENMM_BUILD_RPMD_PLUGIN)
    IF(NOT OPENMM_BUILD_DRUDE_PLUGIN)
        MESSAGE(SEND_ERROR "The Python wrappers require that the Drude plugin be built.")
    ENDIF(NOT OPENMM_BUILD_DRUDE_PLUGIN)
    ADD_SUBDIRECTORY(wrappers/python)
ENDIF(OPENMM_BUILD_PYTHON_WRAPPERS)

#
# Testing
#

ENABLE_TESTING()

IF (EXECUTABLE_OUTPUT_PATH)
  SET (TEST_PATH ${EXECUTABLE_OUTPUT_PATH})
ELSE (EXECUTABLE_OUTPUT_PATH)
  SET (TEST_PATH .)
ENDIF (EXECUTABLE_OUTPUT_PATH)

ADD_SUBDIRECTORY(docs-source)
IF(BUILD_TESTING)
    ADD_SUBDIRECTORY(tests)
ENDIF(BUILD_TESTING)

SET(OPENMM_BUILD_EXAMPLES ON CACHE BOOL "Build example executables")
IF(OPENMM_BUILD_EXAMPLES)
  ADD_SUBDIRECTORY(examples)
ENDIF(OPENMM_BUILD_EXAMPLES)
