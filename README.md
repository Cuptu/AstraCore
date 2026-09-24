# AstraCore

AstraCore is a lightweight, high-performance native media engine built on a unified **FFmpeg 9.0.1** and **libmpv (0.41.0+)** foundation. It provides a minimal-overhead C ABI tailored for audio-visual editing workstations, high-precision subtitle typography engines, and speech recognition pipelines.

Rather than spawning separate CLI subprocesses or maintaining heavyweight interop layers, AstraCore exposes native operations directly into memory—providing sub-millisecond container probing, packet-level keyframe discovery, zero-copy peak waveform and STFT spectrogram extraction, in-memory frame grabbing with colorspace conversion, lossless container trimming, and HDR10/HLG mastering metadata probing.

```
                      +-------------------------------------------------------+
                      |       Application Layer (.NET / C++ / Qt / Python)    |
                      +---------------------------+---------------------------+
                                                  | Direct C ABI (ABI v5)
                                                  v
+-------------------------------------------------------------------------------------------------------------------+
|                                                 AstraCore.Native                                                  |
|  ac_probe  |  ac_extract_waveform_peaks  |  ac_extract_spectrogram  |  ac_extract_keyframes  |  ac_grab_frame_image  |
|  ac_probe_hdr  |  ac_extract_timecodes  |  ac_change_audio_speed   |  ac_trim_media         |  ac_extract_audio_wav |
+---------------------+---------------------------+---------------------------+-------------------------------------+
                      |                           |                           |
                      v                           v                           v
             +-----------------+         +-----------------+         +-----------------+
             |   libavformat   |         |   libavcodec    |         |   libavfilter   |
             |  (FFmpeg 9.0.1) |         | (HW Dec & Enc)  |         | (atempo, volume)|
             +--------+--------+         +--------+--------+         +--------+--------+
                      |                           |                           |
                      +---------------------------+---------------------------+
                                                  |
                                                  +--------------------+
                                                  | Shared av*         |
                                                  v                    v
                      +-------------------------------------+  +-----------------+
                      |          libmpv (0.41.0+)           |  |   libswscale    |
                      | Surface: D3D11 / Metal / Cocoa / EGL|  | (Colorspace /   |
                      +-------------------------------------+  |  Pixel Conv)    |
                                                               +-----------------+
```

---

## Key Features

- **Unified Shared Core**: `AstraCore.Native`, `libmpv`, `ffmpeg`, and `ffprobe` all dynamically link against the exact same shared `libav*` binaries, eliminating duplicate decode pipelines and shrinking the runtime footprint from >160 MB to ~35 MB.
- **Fast Demuxer-Level Keyframe Discovery**: `ac_extract_keyframes_cancel_utf8` inspects container packet headers (`AV_PKT_FLAG_KEY`) without decoding video frames, returning complete millisecond timestamps of all seek points in linear time.
- **In-Memory Frame Grabber & Scaler**: `ac_grab_frame_image_cancel_utf8` seeks to target timestamps, decodes single video frames, and converts pixel formats via `libswscale` directly into caller-allocated buffers (`RGBA`, `BGRA`, `RGB24`, `GRAY8`, `NV12`, `YUV420P`) for instant timeline thumbnails and OCR.
- **VFR Timecodes v2 Exporter**: `ac_extract_timecodes_cancel_utf8` traverses packet presentation timestamps (PTS) and exports standard Matroska / Aegisub v2 timecode files for variable frame rate synchronization.
- **STFT Spectrogram Extraction**: `ac_extract_spectrogram_cancel_utf8` computes Short-Time Fourier Transform frequency magnitude matrices directly in memory using periodic Hann windows and configurable FFT sizes, providing data for audio spectrum displays.
- **HDR10 & HLG Metadata Probing**: `ac_probe_hdr_cancel_utf8` extracts mastering display color volume (`SMPTE 2086`), content light level (`CTA-861.3` CLL/FALL), transfer characteristics (`SMPTE 2084` PQ / `ARIB STD-B67` HLG), and color primaries (`BT.2020`).
- **Direct In-Memory Waveform Extraction**: `ac_extract_waveform_peaks_cancel_utf8` decodes and downsamples audio streams in-process, outputting normalized floating-point peaks into caller buffers without writing intermediary files to disk.
- **ASR Acoustic Preprocessing**: `ac_extract_audio_wav_cancel_utf8` extracts 16 kHz 16-bit mono PCM streams formatted specifically for Whisper, Faster-Whisper, and FunASR inference pipelines.
- **Lossless Stream Trimming**: `ac_trim_media_cancel_utf8` performs packet-level stream copying with timestamp rebasing (`rescale_rnd` / `AV_ROUND_NEAR_INF`), slicing media without re-encoding quality loss.
- **Pitch-Preserving Tempo Adjustment**: `ac_change_audio_speed_cancel_utf8` utilizes FFmpeg's `atempo` filter graph (0.25x to 4.0x) for high-speed subtitle auditioning and playback synchronization.
- **Cooperative Cancellation**: Every long-running entry point accepts an `ac_cancel_callback`, hooking into FFmpeg's `AVIOInterruptCB` and decode loops to support responsive thread abortion without killing processes.
- **10-bit & HDR10+ Encoding**: Built-in x265 pipeline is compiled with multi-depth 10-bit support and HDR10+ metadata multiplexing.

---

## Codec & Hardware Acceleration Whitelist

AstraCore is pruned to preserve complete compatibility with contemporary consumer and professional media formats while shedding legacy and obsolete codecs.

| Category | Supported Codecs / Formats |
| :--- | :--- |
| **Video Decoding** | H.264 (AVC), HEVC (H.265 8-bit & 10-bit), AV1 (via `libdav1d` & HW), VP8, VP9, MPEG-4, ProRes, DNxHD, MJPEG, PNG, WebP |
| **Audio Decoding** | AAC, MP3, Opus, FLAC, Vorbis, PCM (s16, s24, s32, f32), AC-3, E-AC-3, TrueHD, DTS |
| **Video Encoding** | `libx264` (CPU), `libx265` (8-bit & 10-bit Main10 CPU with HDR10+), `libsvtav1` (CPU), PNG |
| **Audio Encoding** | `aac`, `pcm_s16le` |
| **Hardware Acceleration** | **Windows**: D3D11VA, DXVA2, NVENC, Intel QSV, AMD AMF<br>**Linux**: VA-API, VDPAU, NVENC<br>**macOS**: VideoToolbox, AudioToolbox |
| **Demuxers & Muxers** | MP4, MKV, MOV, WebM, AVI, MPEG-TS, FLV, WAV, MP3, FLAC, OGG, AAC, SRT, ASS, WebVTT |
| **Filter Graph** | `atempo`, `volume`, `aresample`, `scale`, `fps`, `format`, `subtitles`, `trim`, `atrim`, `setpts`, `asetpts` |

---

## C ABI Specification (ABI v5)

Header location: [`include/astracore.h`](include/astracore.h)

### Version & Capability Discovery

```c
#include "astracore.h"

// Semantic Version Triplet
#define AC_VERSION_MAJOR 5u
#define AC_VERSION_MINOR 0u
#define AC_VERSION_PATCH 0u

// Legacy single-scalar ABI revision (returns AC_VERSION_MAJOR, e.g. 5u)
uint32_t ac_abi_version(void);

// Packed semantic version integer: (MAJOR << 16) | (MINOR << 8) | PATCH
uint32_t ac_version(void);

// Semantic version string literal: "5.0.0"
const char *ac_version_string(void);

// Query runtime engine capabilities ("keyframes", "spectrogram", "frame_grabber", "hdr_prober", etc.)
int ac_has_feature(const char *feature_name);

// Check if an audio/video encoder is registered and available
int ac_check_encoder(const char *encoder_name);

// Cooperative cancellation callback: return non-zero to cancel operation
typedef int (*ac_cancel_callback)(void *opaque);
```

### Media Probing & Analysis

```c
// 1. Basic Media Metadata
typedef struct ac_media_info {
    uint32_t struct_size;       // Must be set to sizeof(ac_media_info)
    double   duration_seconds;  // Container duration in seconds
    int64_t  bit_rate;          // Average container bitrate in bps
    int32_t  width;             // Primary video stream width
    int32_t  height;            // Primary video stream height
    double   frame_rate;        // Primary video stream average framerate
    int32_t  has_video;         // Non-zero if video stream is present
    int32_t  has_audio;         // Non-zero if audio stream is present
} ac_media_info;

int ac_probe_cancel_utf8(
    const char *path,
    ac_media_info *result,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 2. HDR10 / HLG Metadata
typedef struct ac_hdr_info {
    uint32_t struct_size;          // sizeof(ac_hdr_info)
    int32_t  has_hdr;              // Non-zero if HDR metadata was detected
    int32_t  color_primaries;      // AVColorPrimaries enum
    int32_t  color_transfer;       // AVColorTransferCharacteristic enum
    int32_t  color_space;          // AVColorSpace enum
    int32_t  color_range;          // AVColorRange enum
    int32_t  has_mastering_display;// Non-zero if SMPTE 2086 metadata exists
    double   primary_r_x, primary_r_y;
    double   primary_g_x, primary_g_y;
    double   primary_b_x, primary_b_y;
    double   white_point_x, white_point_y;
    double   max_luminance;        // cd/m^2
    double   min_luminance;        // cd/m^2
    int32_t  has_content_light;    // Non-zero if CTA-861.3 metadata exists
    uint32_t max_cll;              // Maximum Content Light Level (cd/m^2)
    uint32_t max_fall;             // Maximum Frame-Average Light Level (cd/m^2)
} ac_hdr_info;

int ac_probe_hdr_cancel_utf8(
    const char *path,
    ac_hdr_info *result,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);
```

### Video Extraction & Keyframes

```c
// 1. Keyframe Timestamps Discovery (Fast Demuxer Pass)
int ac_extract_keyframes_cancel_utf8(
    const char *path,
    int64_t *out_pts_ms,
    int max_keyframes,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 2. In-Memory Video Frame Grabber with sws_scale
typedef enum ac_pixel_format {
    AC_PIX_FMT_RGBA    = 0,
    AC_PIX_FMT_BGRA    = 1,
    AC_PIX_FMT_RGB24   = 2,
    AC_PIX_FMT_GRAY8   = 3,
    AC_PIX_FMT_NV12    = 4,
    AC_PIX_FMT_YUV420P = 5,
} ac_pixel_format;

int ac_grab_frame_image_cancel_utf8(
    const char *path,
    double timestamp_seconds,
    ac_pixel_format target_format,
    int target_width,
    int target_height,
    uint8_t *out_buffer,
    size_t buffer_size,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 3. VFR Timecodes v2 File Exporter
int ac_extract_timecodes_cancel_utf8(
    const char *input_path,
    const char *output_txt_path,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);
```

### Audio Processing & Waveforms

```c
// 1. In-Memory Waveform Peak Extraction
int ac_extract_waveform_peaks_cancel_utf8(
    const char *path,
    int target_sample_rate,
    int samples_per_peak,
    float *out_peaks,
    int max_peaks,
    double *out_duration,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 2. STFT Spectrogram Frequency Matrix Extraction
int ac_extract_spectrogram_cancel_utf8(
    const char *path,
    int fft_size,
    int hop_size,
    float *out_magnitudes,
    int max_frames,
    int *out_num_frames,
    int *out_num_bins,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 3. Lossless Stream Trimming
int ac_trim_media_cancel_utf8(
    const char *input_path,
    const char *output_path,
    double start_seconds,
    double duration_seconds,
    int stream_copy,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 4. Audio Tempo Adjustment (0.25x - 4.0x)
int ac_change_audio_speed_cancel_utf8(
    const char *input_path,
    const char *output_wav_path,
    double speed_factor,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 5. 16 kHz Mono PCM Extraction (for Whisper / ASR)
int ac_extract_audio_wav_cancel_utf8(
    const char *input_path,
    const char *output_wav_path,
    int target_sample_rate,
    int channels,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);
```

---

## ABI Compatibility & Versioning Contract

AstraCore adheres to a **Monotonically Increasing ABI Contract**:

1. **Additive Invariance**: Any new entry points or enum options added in newer ABI versions preserve 100% backward binary compatibility with existing entry points. Functions introduced in ABI v1 through v4 maintain identical function signatures, calling conventions (`cdecl`), and structure packing (`#pragma pack(push, 8)`).
2. **Explicit Struct Sizing**: All mutable structures (`ac_media_info`, `ac_hdr_info`) declare a `struct_size` field. Callers must initialize `struct_size = sizeof(...)` prior to invocation, enabling safe, forward-compatible field additions.
3. **Consumer Version Checks**:
   - Consumers SHOULD verify `ac_abi_version() >= MIN_REQUIRED_ABI` rather than enforcing an arbitrary upper bound ceiling.
   - Enforcing `abi <= MAX_ABI` in downstream wrappers causes artificial load rejections when non-breaking additive features are introduced.

---

## Integration Examples

### C# (.NET 10 / P/Invoke)

```csharp
using System;
using System.Runtime.InteropServices;

public static class AstraCore
{
    private const string LibName = "AstraCore.Native";

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    public delegate int CancelCallback(IntPtr opaque);

    [StructLayout(LayoutKind.Sequential, Pack = 8)]
    public struct MediaInfo
    {
        public uint StructSize;
        public double DurationSeconds;
        public long BitRate;
        public int Width;
        public int Height;
        public double FrameRate;
        public int HasVideo;
        public int HasAudio;
    }

    [DllImport(LibName, EntryPoint = "ac_abi_version", CallingConvention = CallingConvention.Cdecl)]
    public static extern uint GetAbiVersion();

    [DllImport(LibName, EntryPoint = "ac_probe_cancel_utf8", CallingConvention = CallingConvention.Cdecl)]
    public static extern int Probe(
        [MarshalAs(UnmanagedType.LPUTF8Str)] string path,
        ref MediaInfo result,
        CancelCallback cancelCb,
        IntPtr cancelOpaque,
        [Out] byte[] errorBuffer,
        nuint errorBufferSize);

    [DllImport(LibName, EntryPoint = "ac_extract_keyframes_cancel_utf8", CallingConvention = CallingConvention.Cdecl)]
    public static extern int ExtractKeyframes(
        [MarshalAs(UnmanagedType.LPUTF8Str)] string path,
        [Out] long[] outPtsMs,
        int maxKeyframes,
        CancelCallback cancelCb,
        IntPtr cancelOpaque,
        [Out] byte[] errorBuffer,
        nuint errorBufferSize);
}
```

### C++ / Qt (Dynamic Resolution)

```cpp
#include <QLibrary>
#include <QDebug>

typedef uint32_t (*ac_abi_version_fn)();
typedef int (*ac_extract_keyframes_fn)(const char*, int64_t*, int, void*, void*, char*, size_t);

QLibrary lib("AstraCore.Native.dll");
if (lib.load()) {
    auto ac_abi = reinterpret_cast<ac_abi_version_fn>(lib.resolve("ac_abi_version"));
    if (ac_abi && ac_abi() >= 5) {
        auto get_keyframes = reinterpret_cast<ac_extract_keyframes_fn>(
            lib.resolve("ac_extract_keyframes_cancel_utf8"));
        // Ready for keyframe extraction
    }
}
```

### Python (ctypes)

```python
import ctypes

ac = ctypes.CDLL("AstraCore.Native.dll") # or libAstraCore.Native.so
ac.ac_abi_version.restype = ctypes.c_uint32
print(f"Loaded AstraCore ABI: {ac.ac_abi_version()}")

# In-memory frame grabber example (RGBA 1920x1080)
target_w, target_h = 1920, 1080
buf_size = target_w * target_h * 4
frame_buffer = (ctypes.c_uint8 * buf_size)()
err_buf = ctypes.create_string_buffer(512)

# Seek to 12.5 seconds and grab RGBA frame
ret = ac.ac_grab_frame_image_cancel_utf8(
    b"video.mp4",
    ctypes.c_double(12.5),
    0, # AC_PIX_FMT_RGBA
    target_w,
    target_h,
    frame_buffer,
    buf_size,
    None,
    None,
    err_buf,
    512
)
if ret == 0:
    print("Successfully grabbed RGBA frame into memory")
else:
    print(f"Frame grab failed: {err_buf.value.decode('utf-8')}")
```

---

## Building from Source

### Prerequisites

- **Windows**: MSYS2 with `CLANG64` toolchain, `meson`, `ninja`, `cmake`, `clang`.
- **Linux (Ubuntu 22.04 / 24.04)**: `build-essential`, `clang`, `meson`, `ninja-build`, `cmake`, `nasm`, `libva-dev`.
- **macOS (Apple Silicon / Intel)**: Xcode Command Line Tools, Homebrew (`meson`, `ninja`, `cmake`, `nasm`, `pkg-config`).

### 1. Synchronize Pinned Source Trees

```bash
# On Linux / macOS
./scripts/prepare-sources.sh

# On Windows (PowerShell)
pwsh ./scripts/prepare-sources.ps1
```

This clones and verifies the pinned commits for FFmpeg 9.0.1 (`bf1b838f`), mpv 0.41.0 (`41f6a645`), libass (`4a05d812`), libplacebo (`cee9b076`), dav1d (`54706fc6`), x265 (`e444744c`), and HarfBuzz (`36cb489c`).

### 2. Build Platform Runtime

- **Windows (x64)**:
  ```bash
  # Inside MSYS2 CLANG64 shell
  ./scripts/build-windows.sh
  ```
- **Linux (x64)**:
  ```bash
  ./scripts/build-linux.sh
  ```
- **macOS (Apple Silicon / Intel)**:
  ```bash
  ./scripts/build-macos.sh
  ```

### 3. Verify Runtime & Manifest

```bash
python3 ./scripts/generate-manifest.py --runtime-dir artifacts/astracore/win-x64 --rid win-x64
python3 ./scripts/verify-runtime.py --runtime-dir artifacts/astracore/win-x64
```

---

## License

AstraCore is licensed under the **GNU General Public License v3.0** ([LICENSE](LICENSE)).
Included third-party libraries retain their respective licenses:
- **FFmpeg**: GPLv3
- **mpv**: GPLv2+ / GPLv3
- **libass**: ISC
- **libplacebo**: LGPLv2.1+
- **dav1d**: BSD-2-Clause
- **x265**: GPLv2
- **HarfBuzz**: MIT
