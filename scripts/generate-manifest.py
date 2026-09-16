#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def get_tool_version(tool_path):
    try:
        tool_dir = os.path.dirname(os.path.abspath(tool_path))
        env = os.environ.copy()
        env["PATH"] = f"{tool_dir}{os.pathsep}{env.get('PATH', '')}"
        env["LD_LIBRARY_PATH"] = f"{tool_dir}{os.pathsep}{env.get('LD_LIBRARY_PATH', '')}"
        env["DYLD_LIBRARY_PATH"] = f"{tool_dir}{os.pathsep}{env.get('DYLD_LIBRARY_PATH', '')}"
        out = subprocess.check_output([tool_path, "-hide_banner", "-version"], stderr=subprocess.STDOUT, text=True, env=env)
        return out.strip().splitlines()[0]
    except Exception as e:
        print(f"Warning: Failed to get version from {tool_path}: {e}", file=sys.stderr)
        return "unknown"

def main():
    parser = argparse.ArgumentParser(description="Generate astracore-runtime.json manifest")
    parser.add_argument("--runtime-dir", required=True, help="Directory containing the built AstraCore runtime")
    parser.add_argument("--rid", required=True, help="Runtime Identifier (e.g. win-x64, linux-x64, osx-arm64)")
    parser.add_argument("--mpv-version", default="0.41.0", help="libmpv version")
    parser.add_argument("--libass-version", default="0.17.5", help="libass version")
    parser.add_argument("--ffmpeg-commit", default="bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa", help="Pinned FFmpeg commit")
    parser.add_argument("--mpv-commit", default="41f6a645068483470267271e1d09966ca3b9f413", help="Pinned mpv commit")
    args = parser.parse_args()

    runtime_dir = os.path.abspath(args.runtime_dir)
    if not os.path.isdir(runtime_dir):
        sys.exit(f"Error: Runtime directory not found: {runtime_dir}")

    # Find key components
    is_win = args.rid.startswith("win-")
    is_mac = args.rid.startswith("osx-")

    ffmpeg_name = "ffmpeg.exe" if is_win else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if is_win else "ffprobe"

    ffmpeg_path = os.path.join(runtime_dir, ffmpeg_name)
    ffprobe_path = os.path.join(runtime_dir, ffprobe_name)

    if not os.path.isfile(ffmpeg_path):
        sys.exit(f"Error: Missing {ffmpeg_name} in {runtime_dir}")
    if not os.path.isfile(ffprobe_path):
        sys.exit(f"Error: Missing {ffprobe_name} in {runtime_dir}")

    libmpv_candidates = ["libmpv-2.dll"] if is_win else (["libmpv.2.dylib", "libmpv.dylib"] if is_mac else ["libmpv.so.2", "libmpv.so"])
    libmpv_name = next((c for c in libmpv_candidates if os.path.isfile(os.path.join(runtime_dir, c))), None)
    if not libmpv_name:
        sys.exit(f"Error: Missing libmpv binary in {runtime_dir}")

    native_candidates = ["AstraCore.Native.dll"] if is_win else (["libAstraCore.Native.dylib"] if is_mac else ["libAstraCore.Native.so"])
    native_name = next((c for c in native_candidates if os.path.isfile(os.path.join(runtime_dir, c))), None)
    if not native_name:
        sys.exit(f"Error: Missing AstraCore.Native shared library in {runtime_dir}")

    ffmpeg_version = get_tool_version(ffmpeg_path)
    ffprobe_version = get_tool_version(ffprobe_path)

    # Collect files
    files = []
    for root, _, filenames in os.walk(runtime_dir):
        for name in sorted(filenames):
            if name == "astracore-runtime.json":
                continue
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, runtime_dir).replace("\\", "/")
            files.append({
                "path": rel_path,
                "size": os.path.getsize(full_path),
                "sha256": sha256_file(full_path)
            })

    manifest = {
        "schemaVersion": 1,
        "runtimeIdentifier": args.rid,
        "components": {
            "libMpv": libmpv_name,
            "ffmpeg": ffmpeg_name,
            "ffprobe": ffprobe_name,
            "native": native_name
        },
        "versions": {
            "mpv": args.mpv_version,
            "mpvClientApi": "2.5",
            "ffmpeg": ffmpeg_version,
            "ffprobe": ffprobe_version,
            "libass": args.libass_version,
            "libplacebo": "7.360.1",
            "x265": "4.2-8bit",
            "harfbuzz": "14.4.0-minimal",
            "dav1d": "1.5.4"
        },
        "build": {
            "sourceCommits": {
                "ffmpeg": args.ffmpeg_commit,
                "mpv": args.mpv_commit,
                "libass": "4a05d8127f525943ebf45fdc6497c9e665947f0d",
                "libplacebo": "cee9b076f2c63104ccfd497fa79c39a867293ec4",
                "x265": "e444744c03978c1fb4e037168967020cf2648427",
                "harfbuzz": "36cb489cb02ce4b92099669ba9f9bea348eff93f",
                "dav1d": "54706fc6bc0cdecab7e9593974a4039cc038fca7"
            },
            "generatedUtc": datetime.now(timezone.utc).isoformat()
        },
        "features": {
            "preview": ["libmpv-opengl-render-api", "hardware-acceleration", "software-fallback"],
            "subtitles": ["ass", "ssa", "srt", "webvtt", "mov_text", "font-shaper"],
            "export": ["libx264", "libx265", "libsvtav1", "hardware-encoders", "aac", "atempo", "volume"],
            "editing": ["ac_probe", "ac_waveform_peaks", "ac_wav_extract", "ac_speed_change", "ac_lossless_trim", "ac_extract_stream"],
            "tools": ["ffmpeg", "ffprobe", "native-c-abi-v4"]
        },
        "files": files
    }

    manifest_path = os.path.join(runtime_dir, "astracore-runtime.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"==> Generated {manifest_path} with {len(files)} files.")

if __name__ == "__main__":
    main()
