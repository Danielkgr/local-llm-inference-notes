# Vulkan and ROCm on a 7900 XTX

Vulkan improved the tested llama.cpp workloads on the 7900 XTX.  Decode on the
production chat model rose from 92.0 to 148.0 tokens per second.  OCR and one
CPU-offload configuration initially stayed on ROCm, for the reasons below.

The follow-up describes the setup at that time.  Box now uses other runtimes,
including HIP.  See [CURRENT.md](../CURRENT.md).

## Harness

Same llama.cpp commit built twice, once with `GGML_VULKAN=ON` against Mesa RADV
25.2.8 and once against system ROCm 7.2.4.  Identical flags.  Three runs plus
warm-up, medians.  Provenance asserted from `/proc/PID/maps`: ten RADV and
Vulkan libraries and zero ROCm libraries on one side, system ROCm libraries on
the other.

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

VRAM peaked 0.4 to 0.9 GiB lower under Vulkan in every configuration.  On a 24
GB card that is usable headroom the newer ROCm never offered.

Temp-0 outputs differ across backends.  That is expected and is not a defect:
different kernels produce different floating-point rounding, which diverges at
the first near-tie token.  Cross-backend bit-identity is not a realistic bar,
so the correctness gate has to be structural instead.

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
attention disabled rather than a Vulkan defect.  With flash attention on and
q8_0 KV, that model runs correctly on Vulkan and its VRAM drops from 10.07 to
3.75 GiB.  Chasing the anomaly instead of accepting the carve-out paid for
itself.

The concurrency regression is real and unfixed.  Four streams produce less
aggregate throughput than one.  A later llama.cpp bump containing a queue-mutex
refactor was tested specifically against this and did not fix it, so the
finding was upgraded from changelog inference to measurement.

## Three weeks later

The configuration then selected the Vulkan wrapper for every served model.  OCR
worked with flash attention enabled, and the replacement 35B ran fully on GPU.
The ROCm launcher and build were still retained for rollback at that check.

One stale comment still said the 35B used the ROCm launcher.  The effective
command showed otherwise.  See [note 07](07-when-the-verifier-is-wrong.md) for
other instances where comments or verifiers disagreed with the launch path.

This change concerned language model serving.  The image and training stack
still used ROCm.  A running training process mapped libraries from `/opt/rocm`.
The later Box HIP configuration is recorded in [CURRENT.md](../CURRENT.md).
