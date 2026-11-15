# Current setup

Updated 16 November 2026, Melbourne time, after I replaced Box's graphics
cards on 13 November.  The hardware table and the Box section below describe
the new cards.  They come from a read-only host check on 16 November and from
maintenance records.  No Box model was loaded during that check, so the
engines and quantisations listed for Box come from the records.

Everything from "Strix services" onward is the 7 November 2026 snapshot.  I
have not rechecked those sections since, except where one says so.

## The two machines

| Component | Box | Strix |
|---|---|---|
| Processor | Intel Core i5-14600KF | Ryzen AI Max+ 395 |
| Motherboard | ASRock B760 Pro RS/D4 | GMKtec mini PC |
| Memory | 96 GB DDR4-3200 system RAM | 64 GB unified memory |
| Graphics | Two Radeon AI PRO R9700, 32 GB each, 64 GB in total | Integrated Radeon 8060S |
| OS | Ubuntu 26.04.1 LTS | Ubuntu 26.04.1 LTS |
| Running kernel | 7.0.0-43, held at that version | 7.0.0-43, held at that version |
| Serving shape | Eight llama-swap model entries, with four engines installed | Separate agent, OCR, embedding, and voice services |

I removed the Radeon RX 7900 XTX on 13 November.  The notes written before
that date describe the single 24 GB card, or the 24 GB and 32 GB pair, and
their measurements keep that scope.

## Box graphics cards

| Detail | Card A | Card B |
|---|---|---|
| Slot | x16, PCIe Gen4, direct to the processor | x4, PCIe Gen4, through the chipset |
| Power limit | 270 W | 270 W |
| Voltage offset | -50 mV | -50 mV |

Both cards report the same device ID.  A configuration that selects a card
by device ID cannot tell them apart, so a service must select its card by
UUID or PCI address.

Box has a 1000 W power supply.  Box and Strix share one power board, and
neither has a UPS.

## Box routing and runtimes

llama-swap runs two pools, so one model can stay loaded on each card.  A
model that needs both cards takes both pools.  Two cards of the same size do
not make every pair of models compatible.

| Role | Model | Runtime and placement |
|---|---|---|
| Titan and its uncensored twin | Flash-Next | Radiance 1.17.0, split across both cards, 262k context |
| Abyss and its steered twin | DeepSeek V4.1-Flash Coder, pruned, IQ2_XXS | Maya 1.1.60, both cards |
| Ray | Qwen 27B, MXFP4 | Radiance in Docker |
| Flare | Swift 1.5 heretic, MXFP4 | Radiance in Docker |
| Sentinel, security and vision | OrcaCyber Nano 1.0 27B | llama.cpp |
| Box coding worker | Ornith 1.5 abliterated, UD-Q5_K_S | llama.cpp |

Since 14 November the coding worker no longer loads alongside Titan.  Titan
across both cards leaves Box with about 3.9 GiB of system RAM to spare.

The llama.cpp lanes use Vulkan builds.  I tested ROCm and rejected it for
decode speed.  The 7 November review had found Box on HIP for its configured
lanes, so this reverses that.  The Radiance, Maya, and Strata engines are
also installed.

Abyss, its steered twin, and Sentinel each failed the destructive-tool safety
test.  I waived those results, so these models are serving without having
passed qualification.

ComfyUI is pinned to card A.

The local coding router can send worker turns to Box or to Strix.  The
16 November check did not exercise routing.

This update records no qualification results for the new cards.  The
evidence statuses in the [7 November review](reviews/2026-11-07.md) describe
the previous cards and the models served then.

## Strix services

| Role | Observed configuration | Qualification or limitation |
|---|---|---|
| Universal coding and vision service | HaloBox 66da654-cve1 Vulkan, abliterated 35B-A3B UD-Q6_K, `-c 786432`, three separate slots | 262,144 tokens per slot.  The 6 November compact suite failed.  See below. |
| OCR | Same HaloBox runtime, LightOnOCR-3 0.8B Q8_0, BF16 projector, 8,192 context | Historical unit name still says PaddleOCR.  Effective command selects LightOnOCR. |
| Embeddings | llama.cpp b11868 Vulkan, 0.6B Q8_0, 8,192 context, last-token pooling | b12000 was rejected for vector and ranking incompatibility despite passing its own ranking cases. |
| Speech input | Socket-activated Whisper service | A listening socket can exist while the worker service is inactive. |
| Speech output | CPU Kokoro TTS service | Service metadata observed active.  No speech generated. |
| Web interface | Installed Open WebUI 0.13.0 | Unit description still names an older version.  Package metadata and running executable path were inspected. |

The agent, OCR, and embedding commands include a 300-second idle sleep option.
An active service therefore does not establish that weights are resident.  The
reranker unit remains installed but is disabled and inactive.  The old
environment table's always-resident worker and reranking description no longer
describes this host.

The agent process matched the recorded executable hash and command line.  Its
configured GTT limit is 44 GiB.  A 5 November wake guard added a pre-start
memory step and a 30-second restart delay after a wake crash.  The OCR and
embedding rows above are based on effective service configuration.  Their
running executables were not independently hashed during this review.

## Strix deployment decision

The abliterated Strix model went live under an explicit health-only cutover
grant on 3 November.  Its later full suite ran on 6 November and reported FAIL.
It failed inherited coding, the long-context coding task, minimum decode,
stream cancellation, and the native client confinement check.  All 15 safety
repetitions completed, with 12 passes.  Only that safety score had been waived.

Vision, streamed tool formatting, the joint 248,994-token retrieval request,
slot limits, identity, memory, log checks, and restoration passed.  The suite
restored the deployed abliterated model.  On 7 November, Daniel decided to keep
that model in service.  The full-suite result remains FAIL.

## Images, updates, and recovery

The 3 November record adopted ComfyUI and selected node updates while retaining
Torch 2.14.1 with ROCm 7.14.  The ComfyUI checkout still identifies as
`4d988b64`.  Its saved-image checks and render budget passed in that earlier
run.  Semantic image quality was not assessed.  The Torch 2.15 trial was not
adopted.

The updater distinguishes deferred work, no-op, ordinary failure, and recovery
required.  It preserves current service data after admission has reopened,
rather than automatically restoring an older database over newly accepted work.
These procedures remain host tooling and are not shipped here.

The 5 November storage cleanup recovered space but initially removed backup
support files and evaluation fixtures.  The recorded repair restored them and
passed CPU checks.  Some old guard rollback paths now point at deleted trees.
Daniel confirmed on 7 November that the retained rollback coverage is sufficient
and the older rollback paths can stay retired.

Both global test holds remain installed.  Box's retest queue and image smoke
timers are disabled.  The Box GLM EXL3 retest is pending a separately authorised
nightshift window.  Comet is the deployed GLM model.  Notification
resumption remains unauthorised.  Read [METHOD.md](METHOD.md) before preparing
any new comparison.

The [review](reviews/2026-11-07.md) explains coverage and gaps.  The [evidence
snapshot](evidence/2026-11-07-review.json) records source paths, SHA256 hashes,
selected unrounded measurements, and observed configuration.  The private
source files are not distributed with this repository.
