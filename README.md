# Local LLM inference: evaluation notes

Engineering notes from running a local LLM and diffusion stack on a single
workstation (AMD RX 7900 XTX / gfx1100, Ubuntu). Each note follows the same
shape: a question, a pre-registered noise band, a measurement, and a verdict.

Several of these verdicts are negative. That is deliberate. Most published
benchmark writing reports the changes that worked; the expensive knowledge is
usually in the changes that did not, and in the measurement discipline that
tells the difference.

## Notes

| Note | Question | Verdict |
|---|---|---|
| [ROCm 7.14 evaluation](notes/01-rocm-714-evaluation.md) | Is the newer ROCm worth adopting? | No. Flat on llama.cpp, broken on PyTorch. |
| [Vulkan vs ROCm](notes/02-vulkan-vs-rocm.md) | Can the Mesa Vulkan backend replace ROCm for LLM serving? | Yes, with two named carve-outs. |
| [Speculative decoding](notes/03-speculative-decoding-is-lossy.md) | Are the n-gram speculative speedups real? | No. Every faster variant changed the output. |
| [Diagnosing a broken quant](notes/04-diagnosing-a-broken-quant.md) | Bad weights or bad config? | One greedy call separates them. |

## Method

Every measurement in these notes follows the same rules:

- Three samples plus a warm-up, medians reported, not means.
- Noise bands declared before the run, not after: prefill plus or minus 5 per
  cent, decode plus or minus 10 per cent.
- Library provenance asserted in both directions by reading `/proc/PID/maps`,
  so a claimed A/B is actually an A/B and not the same libraries twice.
- Correctness gates outrank speed. A faster configuration that changes the
  output is not a faster configuration.

## Environment

- GPU: AMD Radeon RX 7900 XTX, 24 GB, gfx1100
- CPU: Intel i5-14600KF, 48 GB DDR4
- OS: Ubuntu 24.04, kernel 6.17.0-40
- Serving: llama.cpp behind llama-swap, Open WebUI front end, ComfyUI for images

## Licence

MIT. See [LICENSE](LICENSE).
