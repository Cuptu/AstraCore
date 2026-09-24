# AstraCore

AstraCore is a lightweight, high-performance native media engine built on a unified **FFmpeg 9.0.1** and **libmpv (0.41.0+)** foundation. It provides a direct, minimal-overhead C ABI (ABI v4) tailored for audio-visual editing workstations, subtitle tools, and speech recognition pipelines.

Rather than running heavy CLI subprocesses or maintaining complex interop wrappers, AstraCore exposes native operations directly into memory—providing single-digit millisecond metadata probing, zero-copy peak waveform extraction, lossless container trimming, and pitch-preserving audio tempo scaling.

```
                      +------------------------------------------+
                      | Application Layer (.NET / C++ / Python)  |
                      +--------------------+---------------------+
                                           | Direct C ABI (v4)
                                           v
+---------------------------------------------------------------------------------------+
|                                    AstraCore.Native                                   |
|   ac_probe  |  ac_extract_waveform_peaks  |  ac_change_audio_speed  |  ac_trim_media   |
+---------------------+--------------------+--------------------+-----------------------+
                      |                    |                    |
                      v                    v                    v
             +-----------------+  +-----------------+  +-----------------+
             |   libavformat   |  |   libavcodec    |  |   libavfilter   |
             |  (FFmpeg 9.0.1) |  | (HW Dec & Enc)  |  | (atempo, volume)|
             +--------+--------+  +--------+--------+  +--------+--------+
                      |                    |                    |
                      +--------------------+--------------------+
                                           | Shared av*
                                           v
+---------------------------------------------------------------------------------------+
|                                    libmpv (0.41.0+)                                   |
|               Preview Surface: Direct3D11 / ANGLE | Metal / Cocoa | EGL / X11         |
+---------------------------------------------------------------------------------------+
```

---

## Key Features

- **Unified Shared Core**: `AstraCore.Native`, `libmpv`, `ffmpeg`, and `ffprobe` all dynamically link against the exact same shared `libav*` binaries, eliminating duplicate decode pipelines and reducing runtime footprint from >160 MB to ~35 MB.
- **Direct In-Memory Waveform Extraction**: `ac_extract_waveform_peaks_cancel_utf8` directly decodes and downsamples audio streams in-process, outputting normalized floating-point peaks into user-supplied buffers without writing intermediary WAV files to disk.
- **ASR Acoustic Preprocessing**: `ac_extract_audio_wav_cancel_utf8` extracts 16 kHz 16-bit mono PCM streams formatted specifically for Whisper, Faster-Whisper, and FunASR inference engines.
- **Lossless Stream Trimming**: `ac_trim_media_cancel_utf8` performs packet-level stream copy with timestamp rebasing (`rescale_rnd` / `AV_ROUND_NEAR_INF`), slicing videos instantly without re-encoding artifacts.
- **Pitch-Preserving Tempo Adjustment**: `ac_change_audio_speed_cancel_utf8` utilizes FFmpeg's `atempo` filter graph (supporting 0.25x to 4.0x speed factors) for high-speed subtitle auditioning and playback synchronization.
- **Cooperative Cancellation**: Every long-running native entry point accepts an `ac_cancel_callback`, hooking into FFmpeg's `AVIOInterruptCB` and frame processing loops to support immediate thread abortion without process termination.
- **Memory Safety & Transparency**: Strict bounds-checked reallocation invariants, zero unmanaged memory leaks, and comprehensive `error_buffer` reporting back to the caller.

---

## Codec & Hardware Acceleration Whitelist

AstraCore is moderately pruned to preserve complete compatibility with contemporary consumer and professional media formats while shedding legacy and obsolete codecs.

| Category | Supported Codecs / Formats |
| :--- | :--- |
| **Video Decoding** | H.264 (AVC), HEVC (H.265), AV1 (via `libdav1d` & HW), VP8, VP9, MPEG-4, ProRes, DNxHD, MJPEG, PNG, WebP |
| **Audio Decoding** | AAC, MP3, Opus, FLAC, Vorbis, PCM (s16, s24, s32, f32), AC-3, E-AC-3, TrueHD, DTS |
| **Video Encoding** | `libx264` (CPU), `libx265` (8-bit CPU), `libsvtav1` (CPU), PNG |
| **Hardware Acceleration** | **Windows**: D3D11VA, DXVA2, NVENC, Intel QSV, AMD AMF<br>**Linux**: VA-API, VDPAU, NVENC<br>**macOS**: VideoToolbox, AudioToolbox |
| **Audio Encoding** | `aac`, `pcm_s16le` |
| **Demuxers & Muxers** | MP4, MKV, MOV, WebM, AVI, MPEG-TS, FLV, WAV, MP3, FLAC, OGG, AAC, SRT, ASS, WebVTT |
| **Filter Graph** | `atempo`, `volume`, `aresample`, `scale`, `fps`, `format`, `subtitles`, `trim`, `atrim`, `setpts`, `asetpts` |

---

## C ABI Specification (ABI v4)

Header location: [`include/astracore.h`](include/astracore.h)

```c
#include "astracore.h"

// 1. Cooperative cancellation signature
typedef int (*ac_cancel_callback)(void *opaque);

// 2. Query runtime ABI version
uint32_t ac_abi_version(void); // Returns 4u

// 3. Fast container metadata probe
int ac_probe_cancel_utf8(
    const char *path,
    ac_media_info *result,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);

// 4. In-memory waveform extraction
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

// 5. Lossless stream trimming
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

// 6. Audio tempo adjustment
int ac_change_audio_speed_cancel_utf8(
    const char *input_path,
    const char *output_wav_path,
    double speed_factor,
    ac_cancel_callback cancel_cb,
    void *cancel_opaque,
    char *error_buffer,
    size_t error_buffer_size);
```

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

    [DllImport(LibName, EntryPoint = "ac_extract_waveform_peaks_cancel_utf8", CallingConvention = CallingConvention.Cdecl)]
    public static extern int ExtractWaveformPeaks(
        [MarshalAs(UnmanagedType.LPUTF8Str)] string path,
        int targetSampleRate,
        int samplesPerPeak,
        [Out] float[] outPeaks,
        int maxPeaks,
        out double outDuration,
        CancelCallback cancelCb,
        IntPtr cancelOpaque,
        [Out] byte[] errorBuffer,
        nuint errorBufferSize);
}
```

### Python (ctypes)

```python
import ctypes

ac = ctypes.CDLL("libAstraCore.Native.so") # or AstraCore.Native.dll / libAstraCore.Native.dylib

ac.ac_abi_version.restype = ctypes.c_uint32
print(f"AstraCore ABI: {ac.ac_abi_version()}")

# Waveform peaks extraction example
peaks = (ctypes.c_float * 1000)()
duration = ctypes.c_double(0.0)
err_buf = ctypes.create_string_buffer(512)

res = ac.ac_extract_waveform_peaks_utf8(
    b"test.mp4", 4000, 100, peaks, 1000, ctypes.byref(duration), err_buf, 512
)
if res >= 0:
    print(f"Extracted {res} peaks over {duration.value:.2f} seconds.")
else:
    print(f"Error: {err_buf.value.decode('utf-8')}")
```

---

## Building from Source

### Prerequisites

- **Windows**: MSYS2 with `CLANG64` toolchain, `meson`, `ninja`, `cmake`, `clang`.
- **Linux (Ubuntu 22.04 / 24.04)**: `build-essential`, `clang`, `meson`, `ninja-build`, `cmake`, `nasm`, `libva-dev`.
- **macOS**: Xcode Command Line Tools, Homebrew (`meson`, `ninja`, `cmake`, `nasm`, `pkg-config`).

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
