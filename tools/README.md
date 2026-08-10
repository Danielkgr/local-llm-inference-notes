# Tools

Small, dependency-light utilities extracted from a working local inference stack.
Each one exists because something failed quietly, and each is parameterised so it
runs somewhere other than the machine it was written on.

Defaults point at loopback addresses.  Every path, port, and endpoint is a flag or
an environment variable.

| Tool | One line | Related note |
|---|---|---|
| [`model-eval/run-eval.py`](model-eval/run-eval.py) | Score any OpenAI-compatible server against a graded task suite, with deterministic graders and baseline diffing. | [08](../notes/08-a-benchmark-with-no-judge.md), [09](../notes/09-when-the-harness-scores-itself.md) |
| [`model-eval/gen-hard-tasks.py`](model-eval/gen-hard-tasks.py) | Generate the hard tier reproducibly, asserting every needle is unique in its haystack. | [08](../notes/08-a-benchmark-with-no-judge.md) |
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

Results are written as JSON so runs are diffable, and `--baseline` compares
percentages rather than raw scores, because a suite that changed size makes raw
score diffs actively misleading.

Read [note 08](../notes/08-a-benchmark-with-no-judge.md) for the design position
and the honest limits of this suite, and
[note 09](../notes/09-when-the-harness-scores-itself.md) for two runs where the
harness scored itself instead of the model.

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
size.  On completion it checks the file's magic bytes.
