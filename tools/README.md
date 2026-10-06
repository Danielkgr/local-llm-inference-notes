# Tools

Small, dependency-light utilities extracted from a working local inference stack.
Each one exists because something failed quietly, and each is parameterised so it
runs somewhere other than the machine it was written on.

Defaults point at loopback addresses.  Every path, port, and endpoint is a flag or
an environment variable.

| Tool | One line | Related note |
|---|---|---|
| [`model-eval/run-eval.py`](model-eval/run-eval.py) | Score any OpenAI-compatible server against a graded task suite, with deterministic graders, baseline diffing, and a failure-set adoption gate. | [08](../notes/08-a-benchmark-with-no-judge.md), [09](../notes/09-when-the-harness-scores-itself.md), [12](../notes/12-four-sampling-profiles-three-rankings.md), [13](../notes/13-gating-on-the-failure-set.md), [15](../notes/15-the-same-false-negative-five-times.md) |
| [`model-eval/gen-hard-tasks.py`](model-eval/gen-hard-tasks.py) | Generate the hard tier reproducibly, asserting every needle is unique in its haystack. | [08](../notes/08-a-benchmark-with-no-judge.md) |
| [`model-eval/gen-legal-tasks.py`](model-eval/gen-legal-tasks.py) | Generate the synthetic legal tier reproducibly, asserting every answer appears exactly once in its excerpt. | |
| [`gguf-arch.py`](gguf-arch.py) | Read a GGUF's architecture and shape keys from the header bytes. | [07](../notes/07-when-the-verifier-is-wrong.md) |
| [`gpu-mutex-guard.sh`](gpu-mutex-guard.sh) | Hand one GPU between two services without either dying on allocation. | |
| [`context-readout.py`](context-readout.py) | Measure real context use against each model's configured limit. | |
| [`resume-dl.py`](resume-dl.py) | Resume a large download without ever truncating the partial file. | |

## Requirements

Python 3.8 or newer.  Standard library only, with one exception:
`context-readout.py` needs PyYAML to read a llama-swap config.

```
pip install pyyaml     # only for context-readout.py
```

`gpu-mutex-guard.sh` expects `curl`, `python3`, and on AMD hardware `rocm-smi`,
falling back to sysfs if that is absent.

## Checks

The tests and linters are separate from the tools.  From the repository root:

```sh
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy && pytest
```

The tests cover `run-eval.py`, both generators, `gguf-arch.py`, and `resume-dl.py`,
using hand-built inputs and local fake servers, so they need no GPU, no model, and no
network.  `context-readout.py` has no tests yet, and `gpu-mutex-guard.sh` is checked
only by `bash -n` and shellcheck.  CI runs the same commands, runs the tests on Python
3.8 and 3.13, and regenerates `tasks-hard.json` and `tasks-legal.json` to confirm
neither has changed.

## model-eval

A graded suite that answers "is model A better than model B for my work" with a
number.  Graders are deterministic by design: substring, regex, numeric with a
tolerance, exact word, word count, and JSON key presence.  There is no LLM judge,
because a judge makes the measurement depend on the thing being measured.

```sh
./run-eval.py                                  # every model the server advertises
./run-eval.py --models "my-model"              # one, or a comma separated list
./run-eval.py --tier core --category code      # a subset
./run-eval.py --baseline previous-run.json     # regression check
./run-eval.py --endpoint http://host:8080/v1/chat/completions
```

Fifty tasks in two tiers.  `tasks.json` holds the 23 core tasks; `tasks-hard.json`
holds 27 harder ones and is generated, so edit `gen-hard-tasks.py` rather than the
JSON.  Regenerating without editing the script reproduces the file byte for byte.
A separate legal tier, described below, runs only when asked for.

Results are written as JSON so runs are diffable, and `--baseline` compares
percentages rather than raw scores, because a suite that changed size makes raw
score diffs actively misleading.  Each results file also records the sampling,
token budget, and task selection that produced it, so "match the baseline's
settings" is an instruction someone can actually follow.

### The legal tier

`--tier legal` runs twelve tasks over short contract and policy excerpts.  The
excerpts are synthetic.  They were written for this suite, the parties are roles
rather than names, and none of them states the law.  No model has been run on this
tier yet, so there are no results to report.

| Category | What it checks |
|---|---|
| `extract` | The notice period, governing law, or liability cap, with a plausible distractor in the same excerpt |
| `define` | An answer taken from a defined term rather than the everyday meaning of the word |
| `xref` | A "subject to" or "in accordance with" reference followed to the clause that answers |
| `faithfulness` | NOT STATED when the excerpt is silent, and no obedience to an instruction planted in the document |

Every prompt offers NOT STATED as an answer, including the ones the excerpt does
answer, so a model that retreats to it fails those.  Grading uses only the
deterministic graders above.  `tasks-legal.json` is generated by
`gen-legal-tasks.py`, which fails loudly if an answer is not in its excerpt exactly
once, so edit the script rather than the JSON.

The tier runs only when named.  `--tier all` stays the 50-task suite, so adding the
legal tier moved no existing score or baseline comparison.

```sh
./run-eval.py --tier legal --models "my-model"
```

### The adoption gate

Adoption is a failure-set question, not a score question: **does the candidate
fail anything the incumbent passes?**  A one- or two-point difference in totals
is usually one flip-prone task, as [note 12](../notes/12-four-sampling-profiles-three-rankings.md)
shows.  That reframing splits the suite along an asymmetry: only the tasks the
baseline *passed* can disqualify, and only the ones it *failed* can improve the
verdict.  The disqualifying half therefore runs first, and can end early.

```sh
# stage 1: only the tasks that can disqualify, most expensive first, stop at two
./run-eval.py --models CANDIDATE --baseline incumbent.json \
              --gate passed --order baseline-slowest --gate-stop-after 2

# stage 2: upside only -- the tasks the incumbent failed
./run-eval.py --models CANDIDATE --baseline incumbent.json --gate failed

./run-eval.py --baseline incumbent.json --gate passed --dry-run   # selection, no GPU
```

Every new failure is retried once before it counts, because an empty response
from runaway reasoning and a transient API error both look like a failure and
both have faked a regression here.  `--gate-stop-after` refuses to run with
`--jobs > 1`: with concurrency every task is dispatched before the first result
is read, so the abort could only fire after the GPU time it exists to save.

Partial runs are labelled as partial.  The results file carries the selection
that produced it and a `complete_suite` flag, so a twelve-task gate can never be
read back later as "12/50".

A task the candidate *recovers* is a claim about the baseline file, not about
the candidate.  Check it by re-running that task against the baseline model in
the same sitting.  The first real use of this gate produced a recovery that
turned out to be a token budget running out a week earlier.

### Token budgets

`--max-tokens` defaults to 16000.  A reasoning model spends its budget on
reasoning before the answer, and when it runs out the response comes back with
empty content and a finish reason of `length`.  That is scored as an error in
its own column, never as a pass and never as a content failure, and the row
records the finish reason and the reasoning length so starvation is
distinguishable from a model that genuinely said nothing.  On this machine
budgets of 300, 500, 2000, and 4500 each produced a false capability finding,
and so did a baseline row recorded at 16000.
See [note 15](../notes/15-the-same-false-negative-five-times.md).

Read [note 08](../notes/08-a-benchmark-with-no-judge.md) for the design position
and the honest limits of this suite,
[note 09](../notes/09-when-the-harness-scores-itself.md) for two runs where the
harness scored itself instead of the model, and
[note 13](../notes/13-gating-on-the-failure-set.md) for the gate's design and
first use.

## gguf-arch.py

```sh
gguf-arch.py model.gguf           # -> qwen35moe
gguf-arch.py model.gguf --all     # plus block_count, expert_count, context_length
```

Exists because `llama-gguf <file> r n` prints key names without their string
values.  Grepping that output for the architecture yields an empty string, which
turns an architecture gate into a gate that passes everything.  This reads the
header directly.

## gpu-mutex-guard.sh

```sh
gpu-mutex-guard.sh /path/to/llama-server --model foo.gguf --port 8080
```

Point a service unit's `ExecStart` at this instead of the server binary.  Before
exec it waits for any in-flight render, asks the image server to unload, and then
waits for the VRAM release to actually land.  That last step is the one that is
easy to miss: the free call returns immediately while the driver releases
asynchronously, so without the wait the two race and the server dies on its first
allocation.

Configured entirely by environment: `COMFY_URL`, `COMFY_UNIT`, `VRAM_FREE_BYTES`,
`RENDER_WAIT_SECS`, `VRAM_WAIT_SECS`, and `PRE_EXEC_HOOK` for evicting any third
consumer.

## context-readout.py

```sh
context-readout.py --chats 400
context-readout.py --config path/to/config.yaml --db path/to/webui.db
```

Cross-references each model's configured `-c` against the largest prompt actually
seen in chat history.  Context length is easy to over-buy, and the KV cache it
costs competes with the weights for VRAM, so it is worth knowing whether anyone
reaches the limit before paying for headroom.

Reads only token counts and model ids from the chat database.  No message content
is read, printed, or stored.

## resume-dl.py

```sh
resume-dl.py URL DEST [--expect BYTES]
```

Append-only.  It verifies the server answered a range request with HTTP 206
before writing another byte, and refuses to start at all without a known target
size.  On completion it checks the file's magic bytes.  A client error such as 404
ends the run at once, because it will not change on retry.  Network errors, server
errors, 408, and 429 are retried with back-off.
