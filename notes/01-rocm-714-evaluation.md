# ROCm 7.14 on gfx1100: a null result, and a broken PyTorch tier

**Question.**  ROCm 7.14 was available as a TheRock tarball while the box ran
7.2.4.  Was it worth adopting for either the llama.cpp serving tier or the
PyTorch image-generation tier?

**Verdict.**  No, on both counts, for different reasons.  The llama.cpp tier is
flat to within noise across every architecture and context length tested.  The
PyTorch tier is not slow but broken.

## Harness

Three samples plus warm-up per configuration, medians reported.  Noise bands
declared before the runs: prefill plus or minus 5 per cent, decode plus or
minus 10 per cent.  Identical flags both sides
(`-ngl 999 -fa on -b 2048 -ub 2048 --parallel 1`).

The step that mattered most was provenance.  Before trusting any A/B, the loaded
shared libraries were read out of `/proc/PID/maps` on both sides and asserted to
be disjoint trees: ROCm 7.2.4 system libraries on one side, sandboxed 7.14
libraries on the other.  A benchmark that silently measures the same libraries
twice returns a very convincing null.

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

Two sub-band wiggles were repeatable across runs but opposite in sign, so they
cancel and indicate no coherent direction.  Harness noise was measured directly:
one configuration was run twice within the sweep and returned 1326.7 against
1331.1 prefill, roughly 0.3 per cent.

Adjacent tiers agreed.  Embedding vectors were bit-identical across builds
(cosine 1.0, maximum absolute difference 0.0).  Vision encode moved 2.3 per cent,
inside noise, with temp-0 output differing by exactly one near-tie token in 192.
Four-way concurrent decode moved 2.8 per cent, inside its band.  Load times were
identical and disk-bound.  VRAM high-water differed by 30 to 40 MiB.  Average
power differed by about one watt.

## Result 2: the PyTorch tier is broken, not slow

The TheRock nightly torch wheels for gfx1100 install and pass simple GPU
operations, then fail on real work.  The production image workflow crashes at the
text-encode node with `hipErrorInvalidValue`, reproducibly, with and without
flash attention, and with a bf16 rather than fp8 text encoder.

Root cause, from `AMD_LOG_LEVEL=3`: many kernel code objects in the wheel fail to
load with `kpack_load_code_object failed with error: 13`, and torch subsequently
launches a null function handle through `hipModuleLaunchKernel`.

Direct probes of `scaled_dot_product_attention` confirmed the failures are
scattered and backend-dependent rather than a single bad op.  All the same probes
pass on the production wheel.

A second nightly published three and a half weeks later behaved the same way,
with the failing set shifted but not shrunk.  The defect is persistent in that
channel rather than one bad build.

**Ten-second reproducer:** call
`torch.nn.functional.scaled_dot_product_attention(q, k, v)` with bf16 tensors on
gfx1100.  If it raises `hipErrorInvalidValue`, the wheel is unusable regardless of
what any benchmark says.

## Why this was worth writing down

The correctness failure outranks every speed number, and it generalises: any
future migration that needs a newer Python, and therefore a newer torch wheel,
inherits this risk.  The ten-second probe now runs before any torch upgrade is
considered.  A null result plus a cheap standing test is a better outcome than an
adopted upgrade nobody measured.

The genuinely useful finding arrived as a side question at the end of the
session, and it was not ROCm at all.  See
[the Vulkan note](02-vulkan-vs-rocm.md).

## Postscript, three weeks later: the prediction held

This evaluation was written to answer a question nobody was forced to ask, and
it returned nothing.  Three weeks later the machine was upgraded to a new Ubuntu
LTS, which brought a different driver stack with it.

The driver tier had been the largest perceived risk in that migration.  It was a
non-event, exactly as this report had predicted in writing.

That is the argument for publishing null results rather than filing them.  A
measured null is not an absence of information: it is a forecast about the next
decision, and it can be checked.  This one was, and it was right.  The same report
also left behind the ten-second probe that now runs before any dependency
upgrade, which is a cheaper control than the evaluation that produced it.
