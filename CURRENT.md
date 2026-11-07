# Current setup

Observed 7 November 2026, Melbourne time.  This is a dated configuration
snapshot, supported by read-only host inspection and existing maintenance
records.  No model was loaded or tested for this review.

## The two machines

| Component | Box | Strix |
|---|---|---|
| Processor | Intel Core i5-14600KF | Ryzen AI Max+ 395 |
| Memory | 96 GB system RAM | 64 GB unified memory |
| Graphics | Radeon RX 7900 XTX, 24 GB, plus Radeon AI PRO R9700, 32 GB | Integrated Radeon 8060S |
| OS | Ubuntu 26.04.1 LTS | Ubuntu 26.04.1 LTS |
| Running kernel | 7.0.0-42-generic | 7.0.0-42-generic |
| Mesa Vulkan package | 26.0.8-1ubuntu0.3 | 26.0.8-1ubuntu0.3 |
| Serving shape | Ten configured llama-swap model entries across four backend families | Separate agent, OCR, embedding, and voice services |

The original sixteen investigations mostly describe the earlier single-card
setup.  Their measurements retain their original scope.  The claim in [note
02](notes/02-vulkan-vs-rocm.md) that all serving had moved to Vulkan was true
at its dated follow-up.  Box now uses HIP again for its configured lanes.

## Box routing and runtimes

llama-swap runs with configuration watching enabled.  Its capacity router has
one XTX lease and one R9700 lease.  The main chat family uses the XTX alone,
allowing the new coding worker to occupy the R9700 concurrently.  Models
needing both cards compete for both resources.  Two installed GPUs do not make
every pair of models compatible.

| Role | Effective runtime or configuration | Evidence status |
|---|---|---|
| Main chat and its steered twin | Strata 0.2.10, HIP, IQ4_XS, 262,144 context, XTX only, 768 MiB reserve | Full primary suite passed on 5 November.  Twin received routed light verification. |
| Large 4.1 family and its steered twin | Strata 0.2.10 engine, HIP, two GPUs, 131,072 context | Adopted 3 November with a one-run returning-latency waiver.  Original performance failure remains. |
| Comet and its steered twin | Maya 1.1.50, HIP, 262,144 context | Adopted 3 November after qualification, family, client, and recovery checks. |
| Atlas and the specialist vision lane | llama.cpp achyudh 3ef1275 with DoS patch, HIP, R9700 | Guard points at this runtime.  The specialist lane has no complete performance record. |
| Box coding worker | Same HIP llama.cpp, abliterated 35B-A3B UD-Q5_K_S, three slots of 131,072 | Adopted 5 November after co-residence and actual-client checks, with recorded waivers. |
| Dense 27B EXL3 lane | EXL3 RDNA 1.6.6 through tabbyAPI, R9700 | Promoted 2 November after a separately authorised passing rerun.  Safety score remains diagnostic. |

The 4.1 server wrapper still launches from an older Strata Python tree while
its configuration selects the 0.2.10 engine.  The engine, wrapper,
configuration, libraries, and support files all matter for provenance and
backup coverage.

The local coding router can distribute worker turns across Box and Strix.  Its
Box worker is text-only and uses a smaller context than Strix.  Router source
shows eligibility and conflict checks.  This review did not exercise routing or
assert the current state of its separate operator control file.

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
