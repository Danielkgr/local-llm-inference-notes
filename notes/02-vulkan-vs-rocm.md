# Vulkan beat ROCm for LLM serving on a 7900 XTX

**Question.**  Asked at the end of a ROCm evaluation that had returned nothing:
the Mesa RADV Vulkan driver ships with every Ubuntu install.  Could the llama.cpp
Vulkan backend replace the ROCm backend for serving, and remove the ROCm
userspace dependency entirely?

**Verdict.**  Yes, and by a wide margin, with two carve-outs that had to be found
by measurement rather than assumed.

## Harness

Same llama.cpp commit built twice, once with `GGML_VULKAN=ON` against Mesa RADV
25.2.8 and once against system ROCm 7.2.4.  Identical flags.  Three runs plus
warm-up, medians.  Provenance asserted from `/proc/PID/maps`: ten RADV and Vulkan
libraries and zero ROCm libraries on one side, system ROCm libraries on the other.

## Result

| config | metric | ROCm 7.2.4 | Vulkan | delta |
|---|---|---|---|---|
| Production chat model | prefill 4518 tok | 2127.4 | 2053.3 | -3.5% (noise) |
| Production chat model | **decode** | **92.0** | **148.0** | **+60.9%** |
| MoE 26B-A4B, 16k | prefill | 1644.2 | 3278.5 | **+99.4%** |
| MoE 26B-A4B, 16k | decode | 106.7 | 145.9 | **+36.7%** |
| Dense 27B, 16k | decode | 34.9 | 38.7 | +10.9% |
| MoE, 128k | prefill 107695 tok | 902.9 | 1178.4 | **+30.5%** |
| MoE, 128k | decode at 128k depth | 79.0 | 94.5 | **+19.6%** |

VRAM peaked 0.4 to 0.9 GiB lower under Vulkan in every configuration.  On a 24 GB
card that is usable headroom the newer ROCm never offered.

Temp-0 outputs differ across backends.  That is expected and is not a defect:
different kernels produce different floating-point rounding, which diverges at
the first near-tie token.  Cross-backend bit-identity is not a realistic bar, so
the correctness gate has to be structural instead.

## The gates, including the two that failed

Adoption was gated on replicating every production model configuration, with a
ROCm control run for each anomaly.

| gate | result |
|---|---|
| Chat model, grammar plus tools, q8_0 KV | pass |
| Chat decode, production flags | 123.5 against 90.6 tok/s, +36% |
| Vision encode (VL 7B) | pass, 2.34 s against 2.70 s |
| OCR model, flash attention off | **fail: 77 s against 1.9 s, 40x regression** |
| 35B CPU-offload MoE | parity, no benefit |
| Four-slot concurrency | **regressive: 125 aggregate against 206** |
| Embeddings | 0.253 s against 0.305 s |
| Mixed swap-cycle soak | pass, 10 of 10 |

The two failures decided the shape of the change.  The OCR model and the
CPU-offload MoE stayed on ROCm; everything else moved to Vulkan.  A single
config macro selects the backend per model, so the rollback is a one-line edit
with no restart.

The 40x OCR regression later turned out to be an artefact of running with flash
attention disabled rather than a Vulkan defect.  With flash attention on and q8_0
KV, that model runs correctly on Vulkan and its VRAM drops from 10.07 to 3.75
GiB.  Chasing the anomaly instead of accepting the carve-out paid for itself.

The concurrency regression is real and unfixed.  Four streams produce less
aggregate throughput than one.  A later llama.cpp bump containing a queue-mutex
refactor was tested specifically against this and did not fix it, so the finding
was upgraded from changelog inference to measurement.

## Postscript: both carve-outs are gone

Checked against the live configuration three weeks after this note was written.
**Every served model now launches through the Vulkan wrapper.  None launches
through the ROCm one.**  Both carve-outs in the gate table above are obsolete.

The OCR carve-out is already corrected in place above: the 40x regression was a
flash-attention artefact rather than a Vulkan defect.

The CPU-offload carve-out went a different way.  No served model offloads to the
CPU any more.  The model roster turned over, and the current 35B runs fully on
GPU under Vulkan, so "parity, no benefit" no longer describes anything on the
machine.

The rollback the note describes still exists and is still one edit: the ROCm
launcher macro is still defined and its build is still on disk, unreferenced.

**One detail belongs in [note 07](07-when-the-verifier-is-wrong.md) rather than
here.**  The configuration still carries a comment reading "35B stays on
`${srv}` (parity, no benefit)".  That comment is now the only mention of the
ROCm macro anywhere in the file, and it is wrong.  Nothing reads comments, so it
had no effect, but it is the same failure this repository keeps finding: the
prose and the measurement disagreed, and the prose was the stale half.

## Scope, for readers arriving from elsewhere

"Remove the ROCm userspace dependency entirely" is a claim about the **serving
tier only**.  The PyTorch side of this machine still depends on system ROCm: a
running fine-tune process maps two dozen shared libraries directly out of
`/opt/rocm`.  Vulkan replaced ROCm for inference, not for training or for the
diffusion stack.

## What generalises

The upgrade worth having was not the one being evaluated.  The ROCm evaluation
was thorough, correct, and returned nothing; the throwaway question asked
afterwards returned a 61 per cent decode improvement on the model that runs all
day.  Time budgeted for a null result is not wasted, but the surrounding question
deserves as much attention as the pre-registered one.
