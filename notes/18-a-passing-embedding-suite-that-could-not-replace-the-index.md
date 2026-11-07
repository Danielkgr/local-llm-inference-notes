# Passing retrieval cases did not make the vectors compatible

On 30 October 2026, llama.cpp b12000 passed all forty-eight of its own
embedding ranking cases but failed compatibility with the adopted b11868
vectors and the existing consumer.  It was not adopted.

## Two different claims

An embedding model can rank a relevant document highly when it creates both
query and document vectors.  An existing service has a harder constraint.  Its
stored document vectors came from an earlier runtime, and new query vectors
must work with those existing coordinates.

The candidate's independent ranking result answered the first question.  The
compatibility checks answered the second.

| Check | Recorded outcome |
|---|---|
| Candidate's own ranking cases | 48 of 48 passed |
| Complete ranking order unchanged | 16 of 48 |
| Mean overlap among the top eight | 0.9791666666666666 |
| Minimum vector cosine against adopted runtime | 0.9995625529235244 |
| Maximum absolute vector difference | 0.009615840390324593 |
| Existing consumer check | Failed |

Query latency was within its allowed band.  Batch latency also passed.  Neither
rescued the compatibility failures.  The declared contract required stronger
agreement, and a fast query in the wrong vector space is not an upgrade to an
existing index.

The consumer failure is supporting end-to-end evidence, not proof that every
observed ranking difference caused it.  The stored result does not isolate that
causal chain, so this note makes no stronger attribution.

## The decision

The incumbent retrieval service was restored, and the 7 November command-line
inspection still selects b11868.  This was a runtime rejection under the tested
index contract.  It was not a claim that b12000 cannot produce useful
embeddings.

A future change could define a new index and migration procedure.  That would
be a different comparison, with its own corpus, compatibility decision, and
authorisation.  A cosine close to one does not grant that change implicitly.

The source is the Strix `strix-runtimes-20261030/evidence/RESULT.json` record.
Its hash and the current embedding configuration source are recorded in the
[review evidence](../evidence/2026-11-07-review.json).
