#!/usr/bin/env bash
set -euo pipefail

DESTINATION="${1:-artifacts/astracore-sources}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST_ROOT="$REPO_ROOT/$DESTINATION"

mkdir -p "$DEST_ROOT"

get_pinned_source() {
    local name="$1"
    local repo="$2"
    local commit="$3"
    local fallback_repo="${4:-}"
    local target_dir="$DEST_ROOT/$name"

    if [[ ! -d "$target_dir" ]]; then
        echo "==> Cloning $name from $repo..."
        if ! git clone --filter=blob:none "$repo" "$target_dir"; then
            if [[ -n "$fallback_repo" ]]; then
                echo "Warning: Primary clone failed, trying fallback mirror $fallback_repo..."
                rm -rf "$target_dir"
                git clone --filter=blob:none "$fallback_repo" "$target_dir"
            else
                echo "Error: Failed to clone $name from $repo" >&2
                exit 1
            fi
        fi
    fi

    echo "==> Fetching pinned commit $commit for $name..."
    if ! git -C "$target_dir" fetch --depth 1 origin "$commit" 2>/dev/null; then
        echo "Direct shallow commit fetch rejected or failed for $name, fetching branch heads from origin..."
        git -C "$target_dir" fetch origin
    fi
    git -C "$target_dir" checkout --detach "$commit"

    local actual
    actual="$(git -C "$target_dir" rev-parse HEAD)"
    if [[ "$actual" != "$commit" ]]; then
        echo "Error: $name HEAD ($actual) does not match expected commit ($commit)!" >&2
        exit 1
    fi
    echo "==> $name verified at $actual"
}

get_pinned_source "ffmpeg" "https://github.com/FFmpeg/FFmpeg.git" "bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa" "https://git.ffmpeg.org/ffmpeg.git"
get_pinned_source "mpv" "https://github.com/mpv-player/mpv.git" "41f6a645068483470267271e1d09966ca3b9f413" ""
get_pinned_source "libass" "https://github.com/libass/libass.git" "4a05d8127f525943ebf45fdc6497c9e665947f0d" ""
get_pinned_source "libplacebo" "https://code.videolan.org/videolan/libplacebo.git" "cee9b076f2c63104ccfd497fa79c39a867293ec4" "https://github.com/haasn/libplacebo.git"
get_pinned_source "x265" "https://bitbucket.org/multicoreware/x265_git.git" "e444744c03978c1fb4e037168967020cf2648427" "https://github.com/videolan/x265.git"
get_pinned_source "harfbuzz" "https://github.com/harfbuzz/harfbuzz.git" "36cb489cb02ce4b92099669ba9f9bea348eff93f" ""
get_pinned_source "dav1d" "https://code.videolan.org/videolan/dav1d.git" "54706fc6bc0cdecab7e9593974a4039cc038fca7" "https://github.com/videolan/dav1d.git"

echo "==> All pinned source trees prepared successfully in $DEST_ROOT"
