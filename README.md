<div align="center">

# Local LLM inference

### Sixteen investigations on one 24 GB workstation, including the results that turned out to be wrong

![16 notes](https://img.shields.io/badge/notes-16-0969da?style=for-the-badge) ![8 of 16 verdicts negative](https://img.shields.io/badge/negative_verdicts-8_of_16-cf222e?style=for-the-badge) ![5 tools](https://img.shields.io/badge/tools-5-0969da?style=for-the-badge) ![no LLM judges](https://img.shields.io/badge/LLM_judges-none-8250df?style=for-the-badge) ![MIT licence](https://img.shields.io/badge/licence-MIT-57606a?style=for-the-badge)

</div>

<br>

> Most published benchmark writing reports the changes that worked.  The expensive knowledge sits in the changes that did not, and in the discipline that separates the two.  **Half of the verdicts here are negative**, and several of them overturned a claim this repository had already published.

<br>

## In plain English

Daniel Glynn-Roe is a lawyer in Melbourne.  This repository records his measurements of language models running on hardware he controls, including the measurements that turned out to be wrong.  The same questions decide whether a law firm can put a model to work on client matters.

- **Is the model good enough?**  Vendor claims and public leaderboards were measured on someone else's tasks and machines.  Only a measurement on the firm's own work answers the question, and most of these notes show how easily that measurement goes wrong.
- **Where does client material go?**  A model that runs locally keeps confidential and privileged client material on hardware the firm controls, instead of sending it to a cloud provider.  That privacy holds only while every tool in the chain is set up not to send data out, which also needs checking.
- **What does control cost?**  Running models on-premises trades capability and convenience for control over data and upgrades.

| | Hosted API in the cloud | Local inference on-premises |
|---|---|---|
| **Where client data goes** | To the provider's servers, under its contract and retention terms | It stays on hardware the firm controls |
| **Cost profile** | Pay per use, with no hardware to buy.  Spend grows with use. | Hardware bought up front, then power and staff time.  Extra use costs little until the hardware is full. |
| **Capability ceiling** | Includes the strongest commercial models, which are not released for local use | Whatever fits in local memory.  One 24 GB card holds mid-sized open models, not the largest. |
| **Maintenance burden** | The provider runs, patches, and scales the service | The firm installs, measures, and patches the whole stack.  Most of these notes are that work. |
| **Upgrade control** | The provider changes and retires models on its own timetable | Nothing changes until the firm decides.  Six engine upgrades were measured and rejected here, as [note 14](notes/14-six-upstream-bumps-rejected.md) records. |

<br>

## 1. The situation

One workstation runs chat, agentic coding, retrieval, and image generation, all from a single 24 GB card.  Every decision competes for the same memory.  A larger quantisation costs context.  Context costs KV cache.  A speculative decoding head costs 1.5 GiB, which on one model cut usable working context by a factor of six.

Published benchmarks settle none of it.  They ran on other hardware, at other context depths, with other flags, and the differences that matter here are often smaller than the differences between two machines.  Every decision therefore needed a measurement taken on the machine that would live with it.

Measuring turned out to be the hard part.

<br>

## 2. The problem

Getting numbers was never the difficulty.  The difficulty was that the first numbers usually looked like findings and were not.

| It looked like | It actually was | Note |
|---|---|:--:|
| A **7 tok/s** decode win from a KV cache change | A week-old baseline.  A control run in the same sitting put the real difference at 3.4%, inside the noise band. | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| A **58%** speculative decoding speedup | Truncated output.  The fastest variant dropped content. | [03](notes/03-speculative-decoding-is-lossy.md) |
| A model scoring **0/50**, then **44/50** | Two separate harness bugs.  Neither number described the model. | [09](notes/09-when-the-harness-scores-itself.md) |
| A **three-point gap** between sampling profiles | Noise.  Three repeats produced three different rankings. | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| A model that **could not follow instructions** | A token budget running out mid-reasoning.  This happened five times, across four harnesses. | [15](notes/15-the-same-false-negative-five-times.md) |
| Automatic compaction that **never fired** | A threshold sitting 90,000 tokens past the ceiling the server would accept. | [11](notes/11-a-guard-that-trusts-its-own-number.md) |
| A backup that **exited zero** | An archive missing the inference binary the machine actually runs. | [07](notes/07-when-the-verifier-is-wrong.md) |

> [!WARNING]
> Every one of those was on its way into the record as a fact.  Noticing that a number looked wrong caught none of them.  A procedure that ran whether or not anything looked wrong caught all seven.

<br>

## 3. The method

More measurements do not fix this.  A fixed procedure does, and most rules below earn their place because breaking them produced a wrong result that was about to be published.

| Rule | The failure that bought it | Note |
|---|---|:--:|
| Declare the noise band **before** the run | A band chosen after seeing the numbers is a rationalisation, not a band | |
| Take three samples after a warm-up, and report medians **and the spread** | Decode spread jumped on two runs while prefill held steady, the signature of contention rather than an effect, so the spread check excluded both | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| Measure a control in the same sitting, even when a baseline exists | A week-old baseline turned a 3.4% null into an apparent 7 tok/s win | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| Alternate the arms rather than running them in blocks | Thermal and cache state drift over a session, and a block design aliases that drift onto the variable under test | |
| Assert library provenance in both directions, from `/proc/PID/maps` | A benchmark that silently measures the same libraries twice returns a very convincing null | [01](notes/01-rocm-714-evaluation.md) |
| Test the invariant the technique promises, not output quality | Greedy speculative decoding must produce identical output, so a single diff settles it | [03](notes/03-speculative-decoding-is-lossy.md) |
| Never use a model to grade models | A judge makes the result depend on the very thing under test | [08](notes/08-a-benchmark-with-no-judge.md) |
| Repeat one configuration before comparing two | An unmeasured noise floor makes every gap unfalsifiable | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| Compare failure sets, not totals | A one- or two-point gap is usually one coin-flip task | [13](notes/13-gating-on-the-failure-set.md) |
| Print the token budget in the output | Five different budgets produced five false capability findings | [15](notes/15-the-same-false-negative-five-times.md) |

> [!TIP]
> **[METHOD.md](METHOD.md)** carries the full set of rules, each with the failure or the reasoning behind it.

<br>

## 4. The tooling

A rule that a program can enforce should not depend on attention.  Five proved worth extracting.  Each runs standalone, depends on little, and takes every path and endpoint as a flag or an environment variable, so it works away from this machine.  Defaults point at localhost.

| Tool | What it enforces | Notes |
|---|---|:--:|
| [**model-eval/**](tools/model-eval/) | Scores any OpenAI-compatible server with deterministic graders and no judge, across two difficulty tiers.  Diffs against a baseline by percentage, and gates adoption on the failure set by running only the tasks capable of deciding the question. | [08](notes/08-a-benchmark-with-no-judge.md), [09](notes/09-when-the-harness-scores-itself.md), [13](notes/13-gating-on-the-failure-set.md) |
| [**gguf-arch.py**](tools/gguf-arch.py) | Reads a model's architecture straight from the file header.  The obvious tool prints key names without their values, which turns an architecture gate into one that passes everything. | [07](notes/07-when-the-verifier-is-wrong.md) |
| [**gpu-mutex-guard.sh**](tools/gpu-mutex-guard.sh) | Hands one GPU between an inference server and an image pipeline, waiting for the asynchronous VRAM release instead of racing it. | |
| [**context-readout.py**](tools/context-readout.py) | Measures how close real conversations come to each model's configured limit, before VRAM buys headroom nobody reaches. | |
| [**resume-dl.py**](tools/resume-dl.py) | Verifies HTTP 206 before resuming a download, and refuses to start without a known target size. | |

<br>

## 5. The result

A measurement that ends in no decision is a hobby.  The machine now runs on these.

> 🟢 adopted, 🔴 rejected, 🟡 adopted with a claim withdrawn, ⚪ deliberately unchanged

| Decision | Outcome | Note |
|---|---|:--:|
| ROCm 7.14 for the serving tier | 🔴 **Rejected.**  Flat on llama.cpp across every arm, and the PyTorch side did not work at all. | [01](notes/01-rocm-714-evaluation.md) |
| Mesa Vulkan in place of ROCm | 🟢 **Adopted.**  Decode rose 60.9% on the production chat model.  Two models stayed on ROCm at first, and a later check found every served model on Vulkan. | [02](notes/02-vulkan-vs-rocm.md) |
| n-gram speculative decoding | 🔴 **Rejected.**  Every faster variant changed the output, and the fastest truncated it. | [03](notes/03-speculative-decoding-is-lossy.md) |
| A newly published 4-bit quantisation | 🔴 **Discarded rather than tuned.**  One greedy call located the fault in the weights. | [04](notes/04-diagnosing-a-broken-quant.md) |
| A q4_0 KV cache | 🟡 **Adopted** for the context it buys.  A stale baseline had produced the apparent decode gain, so that claim came out. | [05](notes/05-the-control-that-killed-a-false-claim.md) |
| An LTS operating system upgrade | 🟢 **Taken early, and deliberately**, against a written rollback rather than the judgement of the day. | [06](notes/06-migrating-under-a-written-go-no-go.md) |
| Six successive engine builds | 🔴 **All six rejected.**  A dense arm and a speculative arm measured each candidate, and none beat the incumbent. | [14](notes/14-six-upstream-bumps-rejected.md) |
| A graphics driver point release | 🟢 **Adopted.**  Nothing moved measurably, which is precisely the result that makes it safe. | [14](notes/14-six-upstream-bumps-rejected.md) |
| A kernel bump, with nobody at the machine | 🟢 **Adopted** behind a one-shot boot entry and an automatic post-boot render test. | [14](notes/14-six-upstream-bumps-rejected.md) |
| Two candidate models | 🟢 **Cleared the gate on dominance.**  A third candidate regressed, and the harness restored the incumbent automatically. | [13](notes/13-gating-on-the-failure-set.md) |
| Changing the served sampling profile | ⚪ **Left unchanged.**  Three repeats gave three rankings, so the difference does not resolve at that sample size. | [12](notes/12-four-sampling-profiles-three-rankings.md) |
| A one-line fix carried against upstream | 🟢 **Sent upstream and merged.**  The script that re-applied it now works as a regression detector. | [10](notes/10-carrying-a-patch-against-upstream.md) |

<br>

## The notes

Most notes follow the same shape.  They ask a question, give the verdict up front, and then show the evidence behind it.

> 🔴 the answer was no or the effect was not real, 🟡 mixed, 🟢 it worked

| # | Note | Question | Verdict |
|:--:|---|---|---|
| **01** | [ROCm 7.14 evaluation](notes/01-rocm-714-evaluation.md) | Is the newer ROCm worth adopting? | 🔴 **No.**  Flat on llama.cpp, broken on PyTorch. |
| **02** | [Vulkan vs ROCm](notes/02-vulkan-vs-rocm.md) | Can the Mesa Vulkan backend replace ROCm for serving? | 🟢 **Yes**, by a wide margin.  Both carve-outs have since gone. |
| **03** | [Speculative decoding is lossy](notes/03-speculative-decoding-is-lossy.md) | Are the n-gram speculative speedups real? | 🔴 **No.**  Every faster variant changed the output. |
| **04** | [Diagnosing a broken quant](notes/04-diagnosing-a-broken-quant.md) | Bad weights, or bad config? | 🟢 One greedy call separates them. |
| **05** | [The control that killed a false claim](notes/05-the-control-that-killed-a-false-claim.md) | Does a q4_0 KV cache buy back context for free? | 🟡 Yes on VRAM.  A stale baseline produced the decode gain. |
| **06** | [Migrating under a written go/no-go](notes/06-migrating-under-a-written-go-no-go.md) | How do you upgrade the machine that serves everything? | 🟢 Write the decision, the trigger, and the rollback down first. |
| **07** | [When the verifier is wrong](notes/07-when-the-verifier-is-wrong.md) | What if the tools that check the system are the broken part? | 🔴 One shell predicate silently hid production from three of them. |
| **08** | [A benchmark with no judge](notes/08-a-benchmark-with-no-judge.md) | Can you rank models without an LLM judge? | 🟡 **Yes** for grading.  The difficulty calibration ceilinged twice. |
| **09** | [When the harness scores itself](notes/09-when-the-harness-scores-itself.md) | A model scores 0/50, then 44/50.  Is that the model? | 🔴 **Neither result was.**  Both came from the harness. |
| **10** | [Carrying a patch against upstream](notes/10-carrying-a-patch-against-upstream.md) | What does a local patch cost, and when does it stop being yours? | 🟡 One merged upstream, one has no repro left to defend, and one had its predicate narrowed twice. |
| **11** | [A guard that trusts its own number](notes/11-a-guard-that-trusts-its-own-number.md) | Automatic compaction never fired before the session died.  Why? | 🔴 Its threshold sat 90,000 tokens past the server's ceiling.  **Unreachable, not late.** |
| **12** | [Four sampling profiles, three rankings](notes/12-four-sampling-profiles-three-rankings.md) | Does the sampling profile change how well a model scores? | 🔴 **Not measurably.**  Three repeats, three league tables. |
| **13** | [Gating on the failure set](notes/13-gating-on-the-failure-set.md) | Can a model be adopted from fewer tasks without weakening the decision? | 🟡 **Yes.**  Only the tasks the incumbent passed can disqualify, and a recovery needs a control too. |
| **14** | [Six upstream bumps rejected](notes/14-six-upstream-bumps-rejected.md) | Is staying 149 releases behind a maintenance failure? | 🔴 **No.**  Six candidates measured, six flat or worse. |
| **15** | [The same false negative, five times](notes/15-the-same-false-negative-five-times.md) | A reasoning model returns an empty string.  How often can one machine misread that? | 🔴 **Five**, across four harnesses.  Raising the budget four times did not stop it. |
| **16** | [The approval gate that blocked its own linter](notes/16-the-approval-gate-that-blocked-its-own-linter.md) | The agent harness was already hardened.  Was it safe, and was it fast? | 🟡 **Neither, quite.**  Five agents shared one slot, and the new approval rule blocked the linter it was added to protect. |

Notes `01`, `02`, `03`, `06`, and `14` cover backends and upgrades.  Notes `05`, `08`, `09`, `12`, `13`, and `15` cover measurement discipline.  Notes `04`, `07`, `10`, `11`, and `16` cover systems, verifiers, and patches.

> [!NOTE]
> If you read two notes, read [note 09](notes/09-when-the-harness-scores-itself.md) and [note 15](notes/15-the-same-false-negative-five-times.md).  They show best what this repository is for.

<br>

## Environment

| Component | Serving box | Always-on tier |
|---|---|---|
| **GPU** | AMD Radeon RX 7900 XTX, 24 GB, gfx1100 | AMD Strix Halo APU, unified LPDDR5X |
| **Host** | Intel i5-14600KF, 96 GB DDR4, Ubuntu 26.04.1 LTS, kernel 7.0.0-31 | Same LAN, added part way through |
| **Runs** | llama.cpp behind llama-swap, Open WebUI front end, ComfyUI for images | Embedding, reranking, the small fast model, speech to text and back, plus one resident coding model that is never evicted |

The serving box moved from Ubuntu 24.04 to 26.04 during the period these notes cover.  Each measurement ran on the version current at the time, and every note states its own conditions where they matter.

Where a note compares results from both machines, pass rates are comparable and timings are not.  The same weights under greedy decoding score the same anywhere, while tokens per second is a property of the hardware.

<br>

## Licence

MIT.  See [LICENSE](LICENSE).
