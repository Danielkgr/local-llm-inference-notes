<h1 align="center">Local LLM inference</h1>

<p align="center">
  <em>Evaluation notes from one workstation &mdash; and the measurement<br>
  discipline that separates a real effect from an artefact</em>
</p>

<p align="center">
  <img alt="15 notes" src="https://img.shields.io/badge/notes-15-24292f?style=flat-square">
  <img alt="5 tools" src="https://img.shields.io/badge/tools-5-24292f?style=flat-square">
  <img alt="no LLM judges" src="https://img.shields.io/badge/LLM_judges-none-24292f?style=flat-square">
  <img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-24292f?style=flat-square">
</p>

---

> Most published benchmark writing reports the changes that worked.  The
> expensive knowledge is in the changes that did not, and in the discipline that
> tells the difference.  More than half of the verdicts here are negative.
> Several of them corrected a claim made earlier in this same repository.

Every note has the same shape: a question, a noise band declared before the run,
a measurement, and a verdict.  The stack is llama.cpp and ComfyUI on an AMD RX
7900 XTX, with an APU alongside it carrying the always-on tier.

### The short version

| | |
|--:|:--|
| **+61%** | decode, from swapping the graphics driver.  The largest win here, and it was free — [note 02](notes/02-vulkan-vs-rocm.md) |
| **+58%** | the fastest speculative decoding variant.  It was truncating the output — [note 03](notes/03-speculative-decoding-is-lossy.md) |
| **6 of 6** | engine upgrades built, measured, and rejected — [note 14](notes/14-six-upstream-bumps-rejected.md) |
| **222,822** | the token at which compaction would have fired, on a server that stops at 131,072 — [note 11](notes/11-a-guard-that-trusts-its-own-number.md) |
| **0 and 44** | two scores out of 50.  Neither was about the model — [note 09](notes/09-when-the-harness-scores-itself.md) |
| **5×** | the same false negative, across four harnesses and four token budgets — [note 15](notes/15-the-same-false-negative-five-times.md) |

---

## Notes

### Backends and upgrades

*Is the newer thing faster, and is the speed real?*

| Note | Question | Verdict |
|---|---|---|
| **01** [ROCm 7.14 evaluation](notes/01-rocm-714-evaluation.md) | Is the newer ROCm worth adopting? | **No.** Flat on llama.cpp, broken on PyTorch. |
| **02** [Vulkan vs ROCm](notes/02-vulkan-vs-rocm.md) | Can the Mesa Vulkan backend replace ROCm for LLM serving? | **Yes**, by a wide margin, with two named carve-outs. |
| **03** [Speculative decoding is lossy](notes/03-speculative-decoding-is-lossy.md) | Are the n-gram speculative speedups real? | **No.** Every faster variant changed the output. |
| **06** [Migrating under a written go/no-go](notes/06-migrating-under-a-written-go-no-go.md) | How do you upgrade the machine that serves everything? | Write the decision, the trigger, and the rollback down first. |
| **14** [Six upstream bumps rejected](notes/14-six-upstream-bumps-rejected.md) | Is staying 149 releases behind a maintenance failure? | **No.** Six candidates measured, six flat or worse — and the driver underneath had to be measured too. |

### Measurement discipline

*Was that result about the model, or about the thing measuring it?*

| Note | Question | Verdict |
|---|---|---|
| **05** [The control that killed a false claim](notes/05-the-control-that-killed-a-false-claim.md) | Does a q4_0 KV cache buy back context for free? | Yes on VRAM.  The decode gain was an artefact of a stale baseline. |
| **08** [A benchmark with no judge](notes/08-a-benchmark-with-no-judge.md) | Can you rank models without an LLM judge? | **Yes** for grading.  The difficulty calibration ceilinged twice. |
| **09** [When the harness scores itself](notes/09-when-the-harness-scores-itself.md) | A model scores 0/50, then 44/50.  Is that the model? | **Neither result was.**  Both came from the harness. |
| **12** [Four sampling profiles, three rankings](notes/12-four-sampling-profiles-three-rankings.md) | Does the sampling profile change how well a model scores? | **Not measurably.**  Three repeats produced three different league tables. |
| **13** [Gating on the failure set](notes/13-gating-on-the-failure-set.md) | Can a model be adopted from fewer tasks without weakening the decision? | **Yes.**  Only the tasks the incumbent passed can disqualify — and a recovery needs a control too. |
| **15** [The same false negative, five times](notes/15-the-same-false-negative-five-times.md) | A reasoning model returns an empty string.  How often can one machine misread that? | **Five**, across four harnesses.  Raising the budget four times did not stop it. |

### Systems, verifiers, and patches

*What broke, what was carrying it, and what silently agreed with itself.*

| Note | Question | Verdict |
|---|---|---|
| **04** [Diagnosing a broken quant](notes/04-diagnosing-a-broken-quant.md) | Bad weights or bad config? | One greedy call separates them. |
| **07** [When the verifier is wrong](notes/07-when-the-verifier-is-wrong.md) | What if the tools that check the system are the broken part? | One shell predicate silently hid production from three of them. |
| **10** [Carrying a patch against upstream](notes/10-carrying-a-patch-against-upstream.md) | What does a local patch cost, and when does it stop being yours? | One merged upstream, one has no repro left to defend, one had its predicate narrowed twice. |
| **11** [A guard that trusts its own number](notes/11-a-guard-that-trusts-its-own-number.md) | Automatic compaction never fired before the session died.  Why? | Its threshold sat 90,000 tokens past the server's ceiling.  **Unreachable, not late.** |

New here?  [Note 09](notes/09-when-the-harness-scores-itself.md) and
[note 15](notes/15-the-same-false-negative-five-times.md) are the two that best
show what this repository is for.

---

## Tools

Runnable, dependency-light, and parameterised so they work off this machine.
Defaults point at localhost; every path and endpoint is a flag or an environment
variable.

| Tool | Purpose | Notes |
|---|---|---|
| [**model-eval/**](tools/model-eval/) | Graded eval suite for any OpenAI-compatible server.  Deterministic graders, two difficulty tiers, baseline diffing by percentage, and a failure-set adoption gate that runs only the tasks capable of deciding it. | [08](notes/08-a-benchmark-with-no-judge.md) · [09](notes/09-when-the-harness-scores-itself.md) · [13](notes/13-gating-on-the-failure-set.md) |
| [**gguf-arch.py**](tools/gguf-arch.py) | Read `general.architecture` and shape keys straight from a GGUF header, because the obvious tool prints keys without values and turns an architecture gate into one that passes everything. | [07](notes/07-when-the-verifier-is-wrong.md) |
| [**gpu-mutex-guard.sh**](tools/gpu-mutex-guard.sh) | Hand one GPU between an inference server and an image pipeline, waiting for the asynchronous VRAM release rather than racing it. | |
| [**context-readout.py**](tools/context-readout.py) | Measure how close real conversations get to each model's configured context limit, before paying VRAM for headroom nobody reaches. | |
| [**resume-dl.py**](tools/resume-dl.py) | Append-only downloader that verifies HTTP 206 before resuming and refuses to run without a known target size. | |

---

## Method

Every measurement in these notes follows the same rules:

- Three samples plus a warm-up, medians reported, not means.
- Noise bands declared before the run, not after: prefill plus or minus 5 per
  cent, decode plus or minus 10 per cent.
- Library provenance asserted in both directions by reading `/proc/PID/maps`,
  so a claimed A/B is actually an A/B and not the same libraries twice.
- Correctness gates outrank speed.  A faster configuration that changes the
  output is not a faster configuration.
- Repeat one configuration before comparing two.  A benchmark's noise floor is a
  measurable property of the benchmark, and until it is measured every gap is
  unfalsifiable.
- Report the set of tasks that fail every time, not only the total.  The total is
  a noisy statistic; the always-fail set is a property of the model.

**The full set, and the failure that produced each rule, is in
[METHOD.md](METHOD.md).**

---

## Environment

| | Serving box | Always-on tier |
|---|---|---|
| **GPU** | AMD Radeon RX 7900 XTX, 24 GB, gfx1100 | AMD Strix Halo APU, unified LPDDR5X |
| **Host** | Intel i5-14600KF, 48 GB DDR4, Ubuntu 26.04 LTS, kernel 7.0.0-30 | Same LAN, added part way through |
| **Runs** | llama.cpp behind llama-swap, Open WebUI front end, ComfyUI for images | Embedding, reranking, the small fast model, speech to text and back, plus one resident coding model that is never evicted |

The serving box was upgraded from Ubuntu 24.04 during the period these notes
cover.  Measurements were taken on the version current at the time of each note,
and each note states its own conditions where they matter.

Where a note compares results measured on both machines, pass rates are
comparable and timings are not: the same weights under greedy decoding score the
same anywhere, while tokens per second is a property of the hardware.

---

## Licence

MIT.  See [LICENSE](LICENSE).
