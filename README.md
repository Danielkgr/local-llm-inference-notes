<h1 align="center">Local LLM inference</h1>

<p align="center">
  <em>Fifteen investigations from one workstation &mdash; what was measured,<br>
  what turned out to be an artefact, and what was actually adopted</em>
</p>

<p align="center">
  <img alt="15 notes" src="https://img.shields.io/badge/notes-15-24292f?style=flat-square">
  <img alt="5 tools" src="https://img.shields.io/badge/tools-5-24292f?style=flat-square">
  <img alt="no LLM judges" src="https://img.shields.io/badge/LLM_judges-none-24292f?style=flat-square">
  <img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-24292f?style=flat-square">
</p>

---

> Most published benchmark writing reports the changes that worked.  The
> expensive knowledge is in the changes that did not — and in the discipline that
> tells the difference.  More than half of the verdicts here are negative, and
> several of them overturned a claim this repository had already made.

---

## 1 · The situation

One workstation runs everything: chat, agentic coding, retrieval, and image
generation, from a single 24 GB card.  Every decision competes for the same
memory.  A larger quantisation costs context.  Context costs KV cache.  A
speculative decoding head costs 1.5 GiB, which on one model cut usable working
context by a factor of six.

Published benchmarks do not settle any of it.  They were run on other hardware,
at other context depths, with other flags, and the differences that matter here
are frequently smaller than the differences between two machines.  Every
decision therefore had to be measured on the machine that would live with it.

Measuring turned out to be the hard part.

---

## 2 · The problem

Getting numbers was never the difficulty.  The difficulty was that the first
numbers usually looked like findings, and were not.

| It looked like | It actually was | |
|---|---|:--:|
| A 7 tok/s decode win from a KV cache change | A week-old baseline.  A control in the same sitting put the real difference at 3.4%, inside the noise band. | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| A 58% speculative decoding speedup | Truncated output.  The fastest variant was dropping content. | [03](notes/03-speculative-decoding-is-lossy.md) |
| A model scoring 0/50, then 44/50 | Two separate harness bugs.  Neither number was about the model. | [09](notes/09-when-the-harness-scores-itself.md) |
| A three-point gap between sampling profiles | Noise.  Three repeats produced three different rankings. | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| A model that could not follow instructions | A token budget running out mid-reasoning.  Five times, across four harnesses. | [15](notes/15-the-same-false-negative-five-times.md) |
| Automatic compaction that never fired | A threshold set 90,000 tokens past the ceiling the server would accept. | [11](notes/11-a-guard-that-trusts-its-own-number.md) |
| A backup that exited zero | An archive that did not contain the inference binary the machine actually runs. | [07](notes/07-when-the-verifier-is-wrong.md) |

Every one of those was on its way to being recorded as a fact.

---

## 3 · The method

The fix is not more measurements.  It is a fixed procedure, where each rule
exists because breaking it produced a wrong result that was about to be
published.

| Rule | The failure that bought it | |
|---|---|:--:|
| Declare the noise band **before** the run | A band chosen after seeing the numbers is a rationalisation, not a band | |
| Three samples and a warm-up; report medians **and the spread** | Two runs were excluded when decode spread jumped while prefill stayed steady — the signature of contention, not an effect | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| Measure a control in the same sitting, even when a baseline exists | A week-old baseline turned a 3.4% null into an apparent 7 tok/s win | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| Alternate the arms; never run them in blocks | Block-sequential A/B fabricated a regression that interleaving disproved | |
| Assert library provenance in both directions, from `/proc/PID/maps` | A benchmark that silently measures the same libraries twice returns a very convincing null | [01](notes/01-rocm-714-evaluation.md) |
| Test the invariant the technique promises, not output quality | Greedy speculative decoding must be output-identical, so a single diff settles it | [03](notes/03-speculative-decoding-is-lossy.md) |
| Never use a model to grade models | A judge makes the result depend on the thing being measured | [08](notes/08-a-benchmark-with-no-judge.md) |
| Repeat one configuration before comparing two | Until the noise floor is measured, every gap is unfalsifiable | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| Compare failure sets, not totals | A one- or two-point gap is usually one coin-flip task | [13](notes/13-gating-on-the-failure-set.md) |
| Print the token budget in the output | Four different budgets produced four false capability findings | [15](notes/15-the-same-false-negative-five-times.md) |

**The full set, with the failure behind each rule, is in [METHOD.md](METHOD.md).**

---

## 4 · The tooling

A rule that can be enforced by a program should not be left to attention.  These
are the five that were worth extracting — runnable, dependency-light, and
parameterised so they work off this machine.  Defaults point at localhost; every
path and endpoint is a flag or an environment variable.

| Tool | What it enforces | |
|---|---|:--:|
| [**model-eval/**](tools/model-eval/) | Graded scoring with deterministic graders and no judge, two difficulty tiers, baseline diffing by percentage, and a failure-set adoption gate that runs only the tasks capable of deciding the question. | [08](notes/08-a-benchmark-with-no-judge.md) · [09](notes/09-when-the-harness-scores-itself.md) · [13](notes/13-gating-on-the-failure-set.md) |
| [**gguf-arch.py**](tools/gguf-arch.py) | Reads a model's architecture from the file header, because the obvious tool prints keys without values — which turns an architecture gate into one that passes everything. | [07](notes/07-when-the-verifier-is-wrong.md) |
| [**gpu-mutex-guard.sh**](tools/gpu-mutex-guard.sh) | Hands one GPU between an inference server and an image pipeline, waiting for the asynchronous VRAM release instead of racing it. | |
| [**context-readout.py**](tools/context-readout.py) | Measures how close real conversations get to each model's configured limit, before VRAM is spent on headroom nobody reaches. | |
| [**resume-dl.py**](tools/resume-dl.py) | Verifies HTTP 206 before resuming a download, and refuses to run at all without a known target size. | |

---

## 5 · The result

A measurement that does not end in a decision is a hobby.  These were taken, and
the machine runs on them.

| Decision | Outcome | |
|---|---|:--:|
| ROCm 7.14 for the serving tier | **Rejected.**  Flat on llama.cpp across every arm, and the PyTorch side did not work at all. | [01](notes/01-rocm-714-evaluation.md) |
| Mesa Vulkan in place of ROCm | **Adopted.**  +60.9% decode on the production chat model, with two carve-outs that measurement found and prose had not. | [02](notes/02-vulkan-vs-rocm.md) |
| n-gram speculative decoding | **Rejected.**  Every faster variant changed the output; the fastest was truncating it. | [03](notes/03-speculative-decoding-is-lossy.md) |
| A newly published 4-bit quantisation | **Discarded, not tuned.**  One greedy call located the fault in the weights. | [04](notes/04-diagnosing-a-broken-quant.md) |
| A q4_0 KV cache | **Adopted** for the context it buys.  The decode gain was withdrawn as an artefact. | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| An LTS operating system upgrade | **Taken early, deliberately** — against a written rollback rather than the judgement of the day. | [06](notes/06-migrating-under-a-written-go-no-go.md) |
| Six successive engine builds | **All rejected.**  Measured on a dense and a speculative arm; none beat the incumbent. | [14](notes/14-six-upstream-bumps-rejected.md) |
| A graphics driver point release | **Adopted.**  No measurable change — which is precisely the result that makes it safe. | [14](notes/14-six-upstream-bumps-rejected.md) |
| A kernel bump, with nobody at the machine | **Adopted** behind a one-shot boot entry and an automatic post-boot render test. | [14](notes/14-six-upstream-bumps-rejected.md) |
| Two candidate models | **Cleared the gate on dominance.**  A third regressed and the incumbent was restored automatically. | [13](notes/13-gating-on-the-failure-set.md) |
| Changing the served sampling profile | **Not changed.**  Three repeats gave three rankings; the difference is unresolvable at that sample size. | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| A one-line fix carried against upstream | **Sent upstream and merged**, after which the script that re-applied it became a regression detector. | [10](notes/10-carrying-a-patch-against-upstream.md) |

---

## The notes

Each note follows the same shape: a question, a noise band declared before the
run, a measurement, and a verdict.

### Backends and upgrades
*Is the newer thing faster, and is the speed real?*

| | Question | Verdict |
|---|---|---|
| **01** [ROCm 7.14 evaluation](notes/01-rocm-714-evaluation.md) | Is the newer ROCm worth adopting? | **No.**  Flat on llama.cpp, broken on PyTorch. |
| **02** [Vulkan vs ROCm](notes/02-vulkan-vs-rocm.md) | Can the Mesa Vulkan backend replace ROCm for serving? | **Yes**, by a wide margin, with two named carve-outs. |
| **03** [Speculative decoding is lossy](notes/03-speculative-decoding-is-lossy.md) | Are the n-gram speculative speedups real? | **No.**  Every faster variant changed the output. |
| **06** [Migrating under a written go/no-go](notes/06-migrating-under-a-written-go-no-go.md) | How do you upgrade the machine that serves everything? | Write the decision, the trigger, and the rollback down first. |
| **14** [Six upstream bumps rejected](notes/14-six-upstream-bumps-rejected.md) | Is staying 149 releases behind a maintenance failure? | **No.**  Six candidates measured, six flat or worse. |

### Measurement discipline
*Was that result about the model, or about the thing measuring it?*

| | Question | Verdict |
|---|---|---|
| **05** [The control that killed a false claim](notes/05-the-control-that-killed-a-false-claim.md) | Does a q4_0 KV cache buy back context for free? | Yes on VRAM.  The decode gain was an artefact of a stale baseline. |
| **08** [A benchmark with no judge](notes/08-a-benchmark-with-no-judge.md) | Can you rank models without an LLM judge? | **Yes** for grading.  The difficulty calibration ceilinged twice. |
| **09** [When the harness scores itself](notes/09-when-the-harness-scores-itself.md) | A model scores 0/50, then 44/50.  Is that the model? | **Neither result was.**  Both came from the harness. |
| **12** [Four sampling profiles, three rankings](notes/12-four-sampling-profiles-three-rankings.md) | Does the sampling profile change how well a model scores? | **Not measurably.**  Three repeats, three league tables. |
| **13** [Gating on the failure set](notes/13-gating-on-the-failure-set.md) | Can a model be adopted from fewer tasks without weakening the decision? | **Yes.**  Only the tasks the incumbent passed can disqualify — and a recovery needs a control too. |
| **15** [The same false negative, five times](notes/15-the-same-false-negative-five-times.md) | A reasoning model returns an empty string.  How often can one machine misread that? | **Five**, across four harnesses.  Raising the budget four times did not stop it. |

### Systems, verifiers, and patches
*What broke, what was carrying it, and what silently agreed with itself.*

| | Question | Verdict |
|---|---|---|
| **04** [Diagnosing a broken quant](notes/04-diagnosing-a-broken-quant.md) | Bad weights or bad config? | One greedy call separates them. |
| **07** [When the verifier is wrong](notes/07-when-the-verifier-is-wrong.md) | What if the tools that check the system are the broken part? | One shell predicate silently hid production from three of them. |
| **10** [Carrying a patch against upstream](notes/10-carrying-a-patch-against-upstream.md) | What does a local patch cost, and when does it stop being yours? | One merged upstream, one has no repro left to defend, one had its predicate narrowed twice. |
| **11** [A guard that trusts its own number](notes/11-a-guard-that-trusts-its-own-number.md) | Automatic compaction never fired before the session died.  Why? | Its threshold sat 90,000 tokens past the server's ceiling.  **Unreachable, not late.** |

New here?  [Note 09](notes/09-when-the-harness-scores-itself.md) and
[note 15](notes/15-the-same-false-negative-five-times.md) are the two that best
show what this repository is for.

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
