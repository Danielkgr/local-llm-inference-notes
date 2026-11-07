# ROCm 7.14 evaluation on gfx1100

ROCm 7.14 was evaluated from a TheRock tarball against the installed 7.2.4
stack.  It did not provide a material improvement across the tested llama.cpp
workloads.  The tested PyTorch wheels failed real GPU operations, so they were
not suitable for the image pipeline.

This describes that evaluation.  Later HIP and torch configurations are
recorded in [CURRENT.md](../CURRENT.md).

## Harness

Three samples plus warm-up per configuration, medians reported.  Noise bands
declared before the runs: prefill plus or minus 5 per cent, decode plus or
minus 10 per cent.  Identical flags both sides (`-ngl 999 -fa on -b 2048 -ub
2048 --parallel 1`).

The step that mattered most was provenance.  Before trusting any A/B, the
loaded shared libraries were read out of `/proc/PID/maps` on both sides and
asserted to be disjoint trees: ROCm 7.2.4 system libraries on one side,
sandboxed 7.14 libraries on the other.  A benchmark that silently measures the
same libraries twice returns a very convincing null.

The 7.14 install lived in a disposable sandbox prefix with its own llama.cpp
build.  The production stack was never modified, and was verified untouched at
the end of the session.

## Result 1: llama.cpp tier is flat

| config | metric | 7.2.4 | 7.14 | delta | verdict |
|---|---|---|---|---|---|
| MoE 26B-A4B, 16k | prefill (3889 tok) | 1662.2 | 1709.1 | +2.8% | sub-band, repeatable |
| MoE 26B-A4B, 16k | decode | 107.9 | 108.2 | +0.3% | noise |
| Dense 27B, 16k | prefill (4518 tok) | 695.5 | 695.2 | 0.0% | noise |
| Dense 27B, 16k | decode | 35.0 | 34.7 | -0.9% | noise |
| MoE, 32k | decode at depth | 93.5 | 92.9 | -0.6% | noise |
| MoE, 64k | decode at depth | 87.2 | 89.3 | +2.4% | noise |
| MoE, 128k | prefill (107695 tok) | 903.9 | 873.2 | -3.4% | sub-band, repeatable |
| MoE, 128k | decode at depth | 78.9 | 80.0 | +1.4% | noise |

The two sub-band changes had opposite signs at different context depths.  They
do not establish a consistent benefit across the tested workloads.  Harness
noise was measured directly: one configuration was run twice within the sweep
and returned 1326.7 against 1331.1 prefill, roughly 0.3 per cent.

Adjacent tiers agreed.  Embedding vectors were bit-identical across builds
(cosine 1.0, maximum absolute difference 0.0).  Vision encode moved 2.3 per
cent, inside noise, with temp-0 output differing by exactly one near-tie token
in 192.  Four-way concurrent decode moved 2.8 per cent, inside its band.  Load
times were identical and disk-bound.  VRAM high-water differed by 30 to 40 MiB.
Average power differed by about one watt.

## Result 2: the PyTorch tier is broken, not slow

The TheRock nightly torch wheels for gfx1100 install and pass simple GPU
operations, then fail on real work.  The production image workflow crashes at
the text-encode node with `hipErrorInvalidValue`, reproducibly, with and
without flash attention, and with a bf16 rather than fp8 text encoder.

Root cause, from `AMD_LOG_LEVEL=3`: many kernel code objects in the wheel fail
to load with `kpack_load_code_object failed with error: 13`, and torch
subsequently launches a null function handle through `hipModuleLaunchKernel`.

Direct probes of `scaled_dot_product_attention` confirmed the failures are
scattered and backend-dependent rather than a single bad op.  All the same
probes pass on the production wheel.

A second nightly published three and a half weeks later behaved the same way,
with the failing set shifted but not shrunk.  The defect is persistent in that
channel rather than one bad build.

**Ten-second reproducer:** call
`torch.nn.functional.scaled_dot_product_attention(q, k, v)` with bf16 tensors
on gfx1100.  If it raises `hipErrorInvalidValue`, the wheel is unusable
regardless of what any benchmark says.

## Torch upgrade checks

The tested wheels were unsuitable regardless of speed.  A Python migration that
requires a replacement wheel needs to check the affected operations again.  The
short operation probe was retained for that purpose.

The same session also compared Vulkan.  Those results are in [note
02](02-vulkan-vs-rocm.md).

## Postscript, three weeks later: the prediction held

Three weeks later, the Ubuntu LTS upgrade brought a different driver stack.

The driver change did not cause the expected migration difficulty.

The later migration was consistent with this result.  It does not make a null
on these workloads a guarantee about every driver upgrade.  The operation probe
remained useful for checking a proposed torch replacement.  These were
historical tests.  Later HIP adoption is described in
[CURRENT.md](../CURRENT.md).
