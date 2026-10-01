cmake_minimum_required(VERSION 3.25)
project(AstraCoreNative VERSION 0.1.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN YES)

set(ASTRA_FFMPEG_SDK "" CACHE PATH "FFmpeg shared SDK for MSVC")
if(WIN32 AND ASTRA_FFMPEG_SDK)
    add_library(astra_ffmpeg_sdk INTERFACE)
    target_include_directories(astra_ffmpeg_sdk INTERFACE "${ASTRA_FFMPEG_SDK}/include")
    foreach(component IN ITEMS avformat avcodec avutil swresample swscale avfilter)
        set(library "${ASTRA_FFMPEG_SDK}/lib/${component}.lib")
        if(NOT EXISTS "${library}")
            message(FATAL_ERROR "Missing FFmpeg SDK import library: ${library}")
        endif()
        target_link_libraries(astra_ffmpeg_sdk INTERFACE "${library}")
    endforeach()
    set(ffmpeg_target astra_ffmpeg_sdk)
    set(CMAKE_REQUIRED_INCLUDES "${ASTRA_FFMPEG_SDK}/include")
    set(CMAKE_REQUIRED_LIBRARIES "${ASTRA_FFMPEG_SDK}/lib/avcodec.lib")
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(LIBAV REQUIRED IMPORTED_TARGET
        libavformat>=60.16
        libavcodec>=60.31
        libavutil>=58.29
        libswresample>=4.12
        libswscale>=7.5
        libavfilter>=9.12)
    set(ffmpeg_target PkgConfig::LIBAV)
    set(CMAKE_REQUIRED_LIBRARIES PkgConfig::LIBAV)
endif()
include(CheckSymbolExists)
check_symbol_exists(avcodec_get_supported_config "libavcodec/avcodec.h" ASTRA_HAVE_SUPPORTED_CONFIG)
unset(CMAKE_REQUIRED_INCLUDES)
unset(CMAKE_REQUIRED_LIBRARIES)

add_library(AstraCore.Native SHARED src/astracore.c)
target_compile_definitions(AstraCore.Native PRIVATE ASTRACORE_BUILD
    $<$<BOOL:${ASTRA_HAVE_SUPPORTED_CONFIG}>:ASTRA_HAVE_SUPPORTED_CONFIG>)
target_include_directories(AstraCore.Native PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_link_libraries(AstraCore.Native PRIVATE ${ffmpeg_target})
if(UNIX)
    target_link_libraries(AstraCore.Native PRIVATE m)
endif()
set_target_properties(AstraCore.Native PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    OUTPUT_NAME "AstraCore.Native")

if(WIN32)
    set_target_properties(AstraCore.Native PROPERTIES PREFIX "")
elseif(APPLE)
    set_target_properties(AstraCore.Native PROPERTIES
        PREFIX "lib"
        INSTALL_RPATH "@loader_path"
        BUILD_WITH_INSTALL_RPATH TRUE)
else()
    set_target_properties(AstraCore.Native PROPERTIES
        PREFIX "lib"
        INSTALL_RPATH "$ORIGIN"
        BUILD_WITH_INSTALL_RPATH TRUE)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(astracore_probe_smoke tests/probe_smoke.c)
    target_link_libraries(astracore_probe_smoke PRIVATE AstraCore.Native)

    add_executable(astracore_test_editing tests/test_editing.c)
    target_link_libraries(astracore_test_editing PRIVATE AstraCore.Native)

    if(APPLE)
        set_target_properties(astracore_probe_smoke PROPERTIES
            INSTALL_RPATH "@executable_path"
            BUILD_WITH_INSTALL_RPATH TRUE)
        set_target_properties(astracore_test_editing PROPERTIES
            INSTALL_RPATH "@executable_path"
            BUILD_WITH_INSTALL_RPATH TRUE)
    elseif(UNIX)
        set_target_properties(astracore_probe_smoke PROPERTIES
            INSTALL_RPATH "$ORIGIN"
            BUILD_WITH_INSTALL_RPATH TRUE)
        set_target_properties(astracore_test_editing PROPERTIES
            INSTALL_RPATH "$ORIGIN"
            BUILD_WITH_INSTALL_RPATH TRUE)
    endif()

    add_test(NAME astracore_probe_invalid_path COMMAND astracore_probe_smoke)
    add_test(NAME astracore_editing_tests COMMAND astracore_test_editing)
    find_program(ASTRA_TEST_FFMPEG ffmpeg HINTS "${ASTRA_FFMPEG_SDK}/bin" "${CMAKE_INSTALL_PREFIX}/bin" REQUIRED)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(astra_native_video_contract tests/video_contract.c)
    target_link_libraries(astra_native_video_contract PRIVATE AstraCore.Native)
    add_executable(astra_native_dynamic_load tests/dynamic_load.c)
    target_include_directories(astra_native_dynamic_load PRIVATE include)
    target_link_libraries(astra_native_dynamic_load PRIVATE ${CMAKE_DL_LIBS})
    if(UNIX)
        target_link_libraries(astra_native_video_contract PRIVATE m)
        target_link_libraries(astra_native_dynamic_load PRIVATE m)
    endif()
    add_test(NAME astracore_real_media_contract COMMAND ${CMAKE_COMMAND}
        "-DFFMPEG=${ASTRA_TEST_FFMPEG}" "-DPROBE=$<TARGET_FILE:astracore_probe_smoke>"
        "-DVIDEO=$<TARGET_FILE:astra_native_video_contract>"
        "-DLOADER=$<TARGET_FILE:astra_native_dynamic_load>"
        "-DNATIVE=$<TARGET_FILE:AstraCore.Native>"
        "-DPYTHON=${Python3_EXECUTABLE}"
        "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}/media-test/$<CONFIG>"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/media_smoke.cmake")
    set_tests_properties(astracore_real_media_contract PROPERTIES TIMEOUT 30)
endif()

install(TARGETS AstraCore.Native
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib)

install(FILES include/astracore.h DESTINATION include)

configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/astracore.pc.in
    ${CMAKE_CURRENT_BINARY_DIR}/astracore.pc
    @ONLY
)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/astracore.pc DESTINATION lib/pkgconfig)
