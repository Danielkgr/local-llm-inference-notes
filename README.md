<div align="center">

# Local LLM inference

### Measurements, failed upgrades, and the tools used to check them

![20 notes](https://img.shields.io/badge/notes-20-0969da?style=for-the-badge) ![2 hosts](https://img.shields.io/badge/hosts-2-0969da?style=for-the-badge) ![5 utilities](https://img.shields.io/badge/utilities-5-0969da?style=for-the-badge) [![CI](https://img.shields.io/github/actions/workflow/status/Danielkgr/local-llm-inference-notes/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/Danielkgr/local-llm-inference-notes/actions/workflows/ci.yml) ![MIT licence](https://img.shields.io/badge/licence-MIT-57606a?style=for-the-badge)

</div>

<br>

I run local language models for coding, chat, and document work.  This
repository records what I changed, what I measured, and why I kept or rejected
it.  It also records the occasions when the measurement was wrong.

The early notes concern a single 24 GB Radeon card.  The setup now spans two
machines, Box and Strix, with different memory limits and workloads.  The
[current setup](CURRENT.md) was reviewed on 7 November 2026.  The older notes
describe the conditions at the time of each investigation.

<br>

## Where to start

| Looking for | Read |
|---|---|
| What runs now, including unresolved failures | [Current setup](CURRENT.md) |
| The procedure for a new comparison | [Measurement rules](METHOD.md) |
| Changes missing from the earlier repository | [7 November review](reviews/2026-11-07.md) |
| Small tools to use elsewhere | [Tools and checks](tools/README.md) |
| The older coding harness configuration | [Historical harness example](harness/README.md) |

The latest Strix coding model is deployed, but its full suite on 6 November
failed several checks.  Only its safety score had been waived.  Box also has
adoptions made under specific waivers.  [CURRENT.md](CURRENT.md) separates what
is serving from what passed qualification.

<br>

## Why I keep these notes

I am a lawyer in Melbourne.  Running a model locally gives me control over its
weights, configuration, and upgrades.  It also leaves me responsible for
checking that it does the work and that its tools handle data as intended.
Local inference alone does not establish confidentiality.

Most of the work here concerns fairly ordinary decisions.  Does a new backend
improve the workload I use?  Will more context fit without making the machine
unreliable?  Did an upgrade preserve tool calls and retrieval?  Can I restore
the previous setup if it fails?

The misleading results have been at least as useful as the successful changes.

| Initial result | What the check found |
|---|---|
| About 7 tokens/s gained by changing the KV cache | A stale reference.  The matched comparison showed 3.4%, inside that experiment's band. |
| A 58% speculative decoding improvement | Shorter, truncated output. |
| A model scoring zero across fifty tasks | The harness had combined two model names into one invalid identifier. |
| A model failing to follow instructions | Several runs had exhausted the output budget before producing an answer. |
| All forty-eight embedding ranking cases passed | The new vectors still failed compatibility with the existing index and consumer. |

The notes give the conditions and limits behind those findings.  They are
measurements of these workloads, not a ranking of models for every use.

<br>

## The investigations

| # | Investigation | Recorded result |
|:--:|---|---|
| 01 | [ROCm 7.14 evaluation](notes/01-rocm-714-evaluation.md) | No material llama.cpp gain in that test.  The tested PyTorch wheels failed real operations. |
| 02 | [Vulkan vs ROCm](notes/02-vulkan-vs-rocm.md) | Vulkan improved the tested serving workloads.  Box has since moved to other runtimes. |
| 03 | [N-gram speculative decoding](notes/03-speculative-decoding-is-lossy.md) | Faster variants changed the greedy output.  None were adopted. |
| 04 | [Diagnosing a broken quant](notes/04-diagnosing-a-broken-quant.md) | The suspect file was replaced.  Greedy decoding narrowed the diagnosis but could not prove it alone. |
| 05 | [The stale performance reference](notes/05-the-control-that-killed-a-false-claim.md) | The smaller KV cache saved memory.  The claimed decode gain was withdrawn. |
| 06 | [The operating system migration](notes/06-migrating-under-a-written-go-no-go.md) | Upgraded against a written plan, rollback, and verification list. |
| 07 | [Failures in the verification tools](notes/07-when-the-verifier-is-wrong.md) | Worktree detection and stale manifests omitted the production runtime. |
| 08 | [A benchmark without a model judge](notes/08-a-benchmark-with-no-judge.md) | Deterministic grading worked.  The task suite reached its ceiling twice. |
| 09 | [Two misleading evaluation runs](notes/09-when-the-harness-scores-itself.md) | Model-name parsing and sampling explained the apparent failures. |
| 10 | [Local patches and upstream](notes/10-carrying-a-patch-against-upstream.md) | One patch merged upstream.  Others remained local with different limits. |
| 11 | [A compaction threshold beyond the server limit](notes/11-a-guard-that-trusts-its-own-number.md) | An ignored configuration key left the client using the wrong context limit. |
| 12 | [Sampling profiles and repeatability](notes/12-four-sampling-profiles-three-rankings.md) | Three repeats produced different rankings.  The served profile stayed unchanged. |
| 13 | [Comparing failure sets](notes/13-gating-on-the-failure-set.md) | Useful historical gate design.  Its early-exit procedure is superseded on these hosts. |
| 14 | [Six rejected engine updates](notes/14-six-upstream-bumps-rejected.md) | None justified replacing the incumbent under the tested conditions. |
| 15 | [Repeated output-budget errors](notes/15-the-same-false-negative-five-times.md) | Five false capability findings across four harnesses. |
| 16 | [Coding harness permissions and capacity](notes/16-the-approval-gate-that-blocked-its-own-linter.md) | Routing, permission ordering, and missing language tools needed correction. |
| 17 | [Shorter complete suites](notes/17-complete-tests-without-duplicate-work.md) | Reuse applicable references and remove repeated work while completing the planned checks. |
| 18 | [Embedding compatibility](notes/18-a-passing-embedding-suite-that-could-not-replace-the-index.md) | Candidate ranking success did not establish compatibility with stored vectors. |
| 19 | [DFlash memory and cancellation](notes/19-a-draft-that-fit-until-the-first-batch.md) | Two memory failures and a later cancellation crash.  No adoption. |
| 20 | [Deployment and qualification](notes/20-serving-is-not-qualification.md) | The deployed Strix model failed its later full suite.  Restoration returned the same incumbent. |

<br>

## Tools

Five standalone utilities are included.  The evaluation utility also has two
task generators.

| Utility | Purpose |
|---|---|
| [model-eval](tools/model-eval/) | Deterministic grading, task-level results, baseline summaries, and an optional historical failure-set gate |
| [gguf-arch.py](tools/gguf-arch.py) | Read architecture and shape metadata from a GGUF header |
| [gpu-mutex-guard.sh](tools/gpu-mutex-guard.sh) | Make a bounded, best-effort attempt to release image-generation VRAM before starting inference |
| [context-readout.py](tools/context-readout.py) | Compare recorded prompt counts with configured context per slot, returning only metadata from SQLite |
| [resume-dl.py](tools/resume-dl.py) | Resume a download after checking the response range and expected size |

The portable evaluation suite is not the hosts' complete qualification runner.
The safety, retrieval, family, client, and recovery checks described in later
notes live in the host tooling.  Source hashes are recorded in the [review
evidence](evidence/2026-11-07-review.json), but private fixtures and logs are
not included.

<br>

## Checks

These checks exercise code against synthetic fixtures and loopback fake
servers.  They do not run a model or require a GPU.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
bash -n tools/gpu-mutex-guard.sh
.venv/bin/shellcheck tools/gpu-mutex-guard.sh
```

CI also runs the tests and task generators on Python 3.8 and 3.13.  See
[tools/README.md](tools/README.md) for requirements, commands, and known
limits.

<br>

## Licence

MIT.  See [LICENSE](LICENSE).  Security reports are covered by
[SECURITY.md](SECURITY.md).
