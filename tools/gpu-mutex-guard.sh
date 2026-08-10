#!/usr/bin/env bash
# gpu-mutex-guard.sh -- hand a single GPU between an inference server and an
# image-generation server without either one dying on an allocation failure.
#
# The problem: one consumer GPU, two services that both want most of it.  Neither
# knows about the other.  Whichever starts second fails to allocate, and on a
# 24 GB card that failure is silent enough to look like a model problem.
#
# The approach: make the inference server's start a barrier.  Wrap it in this
# script, so that before it execs it (1) waits for any in-flight render rather
# than killing it, (2) asks the image server to unload and free VRAM, and (3)
# waits for the release to actually land before allocating.  Step 3 is the one
# that is easy to miss: the free call returns immediately while the driver
# releases asynchronously, so without the wait the two race and the server dies.
#
# usage:
#   gpu-mutex-guard.sh /path/to/llama-server --model foo.gguf --port 8080
#
# Point a systemd unit's ExecStart at this script instead of the server binary.
#
# env:
#   COMFY_URL         image server base URL      (default http://127.0.0.1:8188)
#   COMFY_UNIT        systemd --user unit to test (default comfyui.service);
#                     set empty to skip the check and always attempt a free
#   VRAM_FREE_BYTES   proceed once used VRAM is below this (default 4 GiB)
#   RENDER_WAIT_SECS  max wait for an in-flight render   (default 240)
#   VRAM_WAIT_SECS    max wait for the VRAM release      (default 30)
#   PRE_EXEC_HOOK     optional command run just before exec, failures ignored;
#                     use it to evict any third consumer (a desktop LLM app, say)
#
# AMD-specific: VRAM is read from rocm-smi, falling back to sysfs.  On NVIDIA,
# replace used_vram() with a nvidia-smi query.
set -u

COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
COMFY_UNIT="${COMFY_UNIT-comfyui.service}"
VRAM_FREE_BYTES="${VRAM_FREE_BYTES:-4294967296}"
RENDER_WAIT_SECS="${RENDER_WAIT_SECS:-240}"
VRAM_WAIT_SECS="${VRAM_WAIT_SECS:-30}"

[ "$#" -ge 1 ] || { echo "usage: $0 <server-binary> [args...]" >&2; exit 2; }

used_vram() {
    local v
    v=$(rocm-smi --showmeminfo vram 2>/dev/null | awk '/Used Memory/ {print $NF}' | head -1)
    if [ -n "$v" ]; then printf '%s' "$v"; return; fi
    # Fallback.  Glob the card index rather than hardcoding one: DRM indices are
    # not stable identifiers and renumber across reboots and device resets.
    for f in /sys/class/drm/card*/device/mem_info_vram_used; do
        [ -f "$f" ] && { cat "$f"; return; }
    done
}

queue_depth() {
    curl -s --max-time 5 "$COMFY_URL/queue" 2>/dev/null | python3 -c \
        'import sys,json
d=json.load(sys.stdin)
print(len(d.get("queue_running",[]))+len(d.get("queue_pending",[])))' 2>/dev/null || echo 0
}

if [ -z "$COMFY_UNIT" ] || systemctl --user is-active --quiet "$COMFY_UNIT"; then
    # 1. wait for an in-flight render rather than killing it
    for _ in $(seq 1 $((RENDER_WAIT_SECS / 2))); do
        [ "$(queue_depth)" = "0" ] && break
        sleep 2
    done

    # 2. ask for an unload
    curl -s --max-time 15 -X POST "$COMFY_URL/free" \
        -H 'Content-Type: application/json' \
        -d '{"unload_models":true,"free_memory":true}' >/dev/null || true

    # 3. wait for the release to land.  Without this the server races the
    #    driver's async free and can die on its first allocation.
    for _ in $(seq 1 $((VRAM_WAIT_SECS / 2))); do
        used=$(used_vram)
        [ -n "$used" ] && [ "$used" -lt "$VRAM_FREE_BYTES" ] && break
        sleep 2
    done
fi

# Best-effort eviction of any third consumer.  Never fatal: this guard must not
# become a new way for the inference server to fail to start.
if [ -n "${PRE_EXEC_HOOK:-}" ]; then
    eval "$PRE_EXEC_HOOK" || true
fi

exec "$@"
