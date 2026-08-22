# stratadb 1.0.2 — SDK fixes implementation plan

## Context

An adversarial test pass against **1.0.1** (~644 checks, 11 sample apps, 5 torture
suites; every defect re-reproduced in a clean process) filed 31 defects (#31–#61;
#30 is the tracking report). Roughly half are strata-core engine bugs; the other
half are fixable entirely in this repo (Python or the thin PyO3 binding).

This plan covers **only the SDK-fixable set**, shipped as a **1.0.2 patch**. It
closes 13 issues fully and one partially; it needs no strata-core change and one
`.so` rebuild (for the concurrency fix). Each fix was root-caused against the code
during a deep-dive pass; file:line anchors below are current as of `main` @ 1.0.1.

The engine-side issues (#33–#38, #42–#45, #48, #50, #53, #56, #57, #58, #60, and
parts of #59/#61) are tracked separately for strata-core (see **Out of scope**).

## Scope

**In scope (SDK 1.0.2):** #31, #32 (binding); #51, #52 (error contract); #40, #41,
#39, #59-part, #61-part (pagination/namespace); #46, #54 (filters/scope); #47, #49,
#55 (docs).

**Corrections from the initial triage:**
- **#58 moved out** — all five requested `as_of` additions are core-blocked (the
  underlying `kv_exists`/`event_exists`/`event_range`/`event_range_time`/
  `event_verify_chain` commands take no `as_of`). SDK can't fix; defer to core.
- **#47** — the wrong "int µs" text exists **only** in `_data/agent-guide.md` (added
  in the 1.0.1 `#24` work); `README.md` is already correct. Narrow doc fix.
- **#59** — `db.json.scan()` is SDK-fixable; the "catalog ids aren't executable
  wire names" half is an IDL/core concern (deferred).
- **#61** — the `metadata` dict guard and metric aliases are SDK; the rest
  (kv increment, ontology validation, cdlp) are core.

## New SDK-raised error codes

All built via `errors.client_error(...)` (matches the existing
`invalid_argument.cli.no_database` / `unsupported.sdk.state_removed` convention).

| Code | Class → exception | Raised for |
|---|---|---|
| `failed_precondition.sdk.fork_not_supported` | `FailedPreconditionError` | #32 handle used after `os.fork()` |
| `invalid_argument.sdk.command` | `InvalidArgumentError` | #52 malformed command / unserializable payload / serde-rejected arg |
| `invalid_argument.sdk.entry` | `InvalidArgumentError` | #52 batch entry missing a required field |
| `invalid_argument.sdk.limit` | `InvalidArgumentError` | #41 `limit <= 0` |
| `invalid_argument.sdk.vector_metadata` | `InvalidArgumentError` | #61 non-dict `metadata=` |
| `invalid_argument.sdk.vector_metric` | `InvalidArgumentError` | #61 unknown vector metric |

---

## WS1 — Concurrency & lifecycle (Rust binding) · #31, #32 · **rebuild required**

### #31 (S0) — concurrent use deadlocks the whole interpreter
**Root cause (`src/lib.rs:96-108`).** `execute` acquires the `Mutex<Option<Executor>>`
(`lib.rs:61`) **while holding the GIL**, then calls `py.allow_threads(...)` with the
guard still held. Thread A: locks mutex → releases GIL → runs engine (mutex held) →
must re-acquire GIL to return. Thread B: has GIL → blocks on `.lock()` **while holding
the GIL**. A needs the GIL (held by B); B needs the mutex (held by A) → deadlock; the
GIL is never released so *every* Python thread freezes; only SIGKILL recovers. The same
lock-before-`allow_threads` bug is in `set_scope`, `default_branch`, `default_space`,
`close` — each can deadlock against an in-flight `execute` (this is why reads freeze too).

**Fix.** Acquire the mutex **inside** `allow_threads` (release the GIL before blocking on
the lock). The closure returns a plain Rust `Result`; build every `PyErr` after the GIL is
re-acquired (a `PyErr` can't be constructed without the GIL). Add a small carrier:

```rust
enum CallError { Closed, Forked, Domain(ExecutorError) }   // Forked = #32
```
```rust
fn execute(&self, py: Python<'_>, command_json: &str) -> PyResult<String> {
    let command: Command = serde_json::from_str(command_json)          // stays OUTSIDE (GIL held; PyValueError needs GIL)
        .map_err(|e| PyValueError::new_err(format!("invalid command: {e}")))?;
    let outcome = py.allow_threads(|| {                                // GIL released BEFORE locking
        let mut guard = self.inner.lock().expect("handle mutex poisoned");
        // if std::process::id() != self.pid { return Err(CallError::Forked); }  // #32 (if done in Rust)
        let executor = guard.as_mut().ok_or(CallError::Closed)?;
        executor.execute(command).map_err(CallError::Domain)
    });
    match outcome {                                                     // back under GIL: build PyErr, serialize
        Ok(output) => serde_json::to_string(&output)
            .map_err(|e| PyRuntimeError::new_err(format!("envelope serialization failed: {e}"))),
        Err(CallError::Closed) => Err(closed_error()),
        Err(CallError::Domain(e)) => Err(native_error(e)),
        Err(CallError::Forked) => Err(fork_error()),
    }
}
```
Apply the same "lock inside `allow_threads`, capture error text as `String`, build `PyErr`
after" pattern to `set_scope`, `default_branch`, `default_space`, `close` (sketches in the
deep-dive notes). Keep `serde_json::from_str` and envelope `to_string` outside the closure.

**Notes/risks.** `&Handle: Send`/`Executor: Send` already hold (the engine call is already
inside `allow_threads` today). The `MutexGuard` is created and dropped inside the closure on
the same OS thread — its `!Send`ness is irrelevant. Optionally harden poisoning with
`.unwrap_or_else(|e| e.into_inner())`. No public signatures change (`py: Python` is injected
by PyO3, invisible to Python; `.pyi` unchanged).

### #32 (S1) — `os.fork()` silently discards acknowledged commits
**Root cause.** No process-identity guard anywhere. A forked child inherits a live
`Handle`; a child write returns a full success receipt but never reaches the parent's
storage.

**Fix (recommended: Python, in `_core.py`).** Every namespace funnels through `Core`, so a
pid guard there covers all methods with no `.so` dependency:
```python
class Core:
    __slots__ = ("_handle", "_pid")
    def __init__(self, handle): self._handle, self._pid = handle, os.getpid()
    def _guard(self):
        if os.getpid() != self._pid:
            raise client_error(FailedPreconditionError,
                "failed_precondition.sdk.fork_not_supported",
                "database handle used in a forked child process",
                "open a fresh Strata handle after os.fork(); do not share one across fork()")
```
Call `self._guard()` first in `execute`, `data`, `set_scope`, `default_branch`,
`default_space`, `close`. `FailedPreconditionError` already exists. (A Rust-side variant is
possible since we rebuild for #31, but Python is cleaner — the accessors don't route through
`error_from_payload`, so a native error there would leak untyped.)

**Known-limitation follow-up (note in changelog, not fixing in 1.0.2):** `close()`/GC in a
forked child can still touch the parent's fds via `Executor::Drop`. Have `Core.close()` skip
the native call when forked; a full fix (native `impl Drop for Handle` that `mem::forget`s
the inner executor when the pid changed) is a follow-up.

**Tests (new `tests/test_concurrency.py`).** 8 threads × 50 puts complete (join timeout →
fail on hang); 2 threads × 300 reads; a pure-Python watchdog keeps ticking during native
writes; `close()` racing an op doesn't hang/crash. Fork test (POSIX-only, via a pipe +
`os._exit()` in child): child `kv.put` raises `FailedPreconditionError`
(`.code == failed_precondition.sdk.fork_not_supported`) and the write never lands.

---

## WS2 — Error contract (Python) · #51, #52

### #51 (S1/S4) — `StrataNativeError` escapes the hierarchy on `open()`
**Root cause (`_core.py:28-34`).** `Core.open_durable`/`open_cache` lack the
`try/except _NativeError → error_from_payload` wrapper that `Core.execute` has
(`_core.py:45-46`). Native open errors carry the same JSON status (code
`unavailable.engine.persistence`) but surface raw and untyped.

**Fix.** Wrap both classmethods with the existing idiom (`_NativeError` and
`error_from_payload` are already imported):
```python
@classmethod
def open_durable(cls, path):
    try: return cls(_stratadb.Handle.open_durable(path))
    except _NativeError as exc: raise error_from_payload(exc.args[0] if exc.args else "{}") from None
```
`Strata.__init__` and `clone()` route through these → covered transitively. No Rust change.

**Tests (`tests/test_durable.py`).** `open(<regular file>)` and double-open of one durable
path raise a typed `errors.UnavailableError` with a populated `.code`.

### #52 (S4) — bare `ValueError`/`TypeError`/`KeyError` leak serde internals (~40 sites)
**Root cause.** The ~40 sites collapse to 4 buckets: (a) the binding's `PyValueError` for
serde-rejected commands (u64 range, unknown variant, NaN/Inf) via `self._handle.execute`;
(b) `json.dumps(command)` `TypeError` in `Core.execute` (bytes payloads); (c) `KeyError`
from Python batch entry-helpers; (d) misc (`_wire.b64e` `TypeError`, `branches.fork`).

**Fix — central where possible.**
- Buckets (a)+(b): widen the existing `Core.execute` catch:
```python
try:
    raw = self._handle.execute(json.dumps(command))
except _NativeError as exc:                                   # domain error — first, unchanged
    raise error_from_payload(exc.args[0] if exc.args else "{}") from None
except (TypeError, ValueError) as exc:                        # our-side encode / serde-rejected input
    raise client_error(InvalidArgumentError, "invalid_argument.sdk.command", str(exc)) from exc
return json.loads(raw)                                        # STAYS OUTSIDE the try (engine output)
```
- Bucket (c): a shared `_require(entry, field)` guard raising
  `invalid_argument.sdk.entry`, applied in the 4 entry-helpers (`json.py` `_set_entries`/
  `_kp_entries`, `vectors.py` `_vector_entries`, `events.py` `_event_entries`).
- Bucket (d): optional — route `branches.py:83` through `client_error`; leave `_wire.b64e`.

**Over-catch guardrails.** Keep `json.loads(raw)` and all `models.*.from_wire(...)` decoding
**outside** the catch — a failure there is engine/SDK corruption, not user input, and must
not be mistyped. `PyRuntimeError` (closed handle, poison panic) is neither `ValueError` nor
`TypeError`, so it correctly still surfaces.

**Compat / escape hatch.** `db.execute({"type":"bogus"})` now raises `InvalidArgumentError`
instead of `ValueError`. Update `tests/test_foundation.py:90-92` and the `Core.execute` /
`Strata.execute` docstrings; changelog it as "all invalid input now raises a typed
`StrataError`."

**Tests (new `tests/test_errors.py`).** Parametrize every #52 example → each raises a
`StrataError` subclass with truthy `.code`. Regression guards: a valid command still
round-trips; a genuine domain error keeps its engine `.code` (not rewritten); a miss still
returns `None`.

**Sequencing note.** WS1 and WS2 both edit `_core.py`/`lib.rs` error paths. Land WS2 (small,
additive Python) first, rebase WS1 (Rust) on top. The widened catch depends only on the
stable binding contract (serde reject → `PyValueError`; domain → `StrataNativeError`), which
WS1 preserves.

---

## WS3 — Pagination & namespace gaps (Python) · #40, #41, #39, #59, #61

### #40 (S2) — `Page` doesn't auto-paginate on iteration
**Root cause (`_results.py:32-33`).** `Page.__iter__` returns `iter(self.items)` — first
page only. Every listing returns a bare `Page`; `for x in db.kv.keys()` silently drops the
rest. (Also: `vectors` has no `iter_keys`; `kv.keys`/`json.keys` differ in default page size;
`events.range()`/`list()` with no limit return the whole log — unbounded memory.)

**Fix (Option A — auto-paginating `__iter__` via a `fetch_next` closure).** `Page` gains an
optional `_fetch_next` (repr/compare excluded); `__iter__` and a new `pages()` walk the
cursor lazily (one page at a time); add `.all()`. Each Page-returning call site passes a
closure that re-issues the command with the next cursor and pins `limit` to `PAGE_SIZE` when
unset:
```python
@dataclass
class Page:
    items: List[Any]; has_more: bool; cursor: Optional[Any] = None
    _fetch_next: Optional[Callable[[Any], "Page"]] = field(default=None, repr=False, compare=False)
    def __iter__(self):
        page = self
        while True:
            yield from page.items
            if not page.has_more or page._fetch_next is None: return
            page = page._fetch_next(page.cursor)
    def all(self): return list(self)
    def pages(self): ...            # yields Page objects
    @classmethod
    def from_wire(cls, record, fetch_next=None): ...
```
**Call sites to convert** (identical closure shape): `kv.keys`/`kv.scan`, `json.keys`/new
`json.scan`, `vectors.keys`, `graphs.list_nodes`/`neighbors`/`nodes_by_type`/
`bindings_for_entity`, `events.range`/`range_by_time`/`list`. For `events.*`, pin the
first-page `limit` to `PAGE_SIZE` so a no-limit call is bounded.

**Compat.** `len(page)`/`page[i]`/`page.items` stay **first-page** (back-compat) while
`for x in page`/`list(page)`/`.all()` yield **all** pages — document that
`len(page) != len(list(page))` when `has_more`. `iter_*` helpers stay as thin wrappers.

### #41 (S2) — `keys(limit=0)` reports `has_more=False` over a non-empty store
**Root cause.** `limit=0` is forwarded verbatim (`kv.py:134` → `commands.py:1343`); engine
returns empty + `has_more=False`, so a `while has_more` loop exits at once.
**Fix.** A `_check_limit` guard on `Namespace` (`base.py`) rejecting `limit <= 0` as
`invalid_argument.sdk.limit`; call it in every `keys`/`scan`/`range`/`list`/`neighbors`/
`list_nodes`/`nodes_by_type`. `limit=None` stays "default". (Reject, don't coerce — `0` is a
caller bug, and coercing to "no limit" resurrects the unbounded-memory risk.)

### #39 (S2, SDK part) — `neighbors()` returns a cursor it won't accept
**Root cause.** `graphs.neighbors` (`graphs.py:208-242`) exposes no `cursor=`, though the
core command already accepts one (`commands.py:705`).
**Fix.** Add `cursor=None` to the signature and forward it (+ `fetch_next` closure per #40).
Pure-SDK; the 100-item default cap itself is core (tracked separately).

### #59 (S3, SDK part) — `db.json.scan()` missing
**Root cause.** `command_index()` lists `json.scan` and `json_scan` exists
(`commands.py:1169`), but `JSONNamespace` has no `scan()`. `json_scan` takes `start` (a seek
into id order), not `prefix`.
**Fix.** Add `db.json.scan(start=None, *, limit=None, cursor=None)` + `iter_rows`, mirroring
`kv.scan` exactly; expose `start` (seek) honestly and document that `keys(prefix=…)` is the
filter. (The "catalog ids aren't wire names" half of #59 is IDL/core — deferred.)

### #61 (S5, SDK part) — non-dict metadata; metric aliases
**Root cause.** `vectors.upsert` types `metadata: Optional[dict]` but does no validation
(`vectors.py:110-126`), so a list is stored and never matches `filters.eq`. `create_collection`
forwards `metric` unchecked; `l2`/`dot` yield a bare engine `ValueError`.
**Fix.** `_check_metadata` guard (raise `invalid_argument.sdk.vector_metadata`) at `upsert`,
`_vector_entries`, `update_metadata`; and a metric alias map (`l2→euclidean`, `dot→dot_product`)
in `create_collection` with `invalid_argument.sdk.vector_metric` for unknowns.

**WS3 tests.** >`PAGE_SIZE` rows: `list(...)`/`.all()` return all N for kv/json/vectors/
graphs/events; `events.list()` no-limit first page ≤ `PAGE_SIZE` + `has_more`; back-compat
`len`/`getitem` first-page. `limit=0`/`-1` raise `invalid_argument.sdk.limit`. `neighbors`
cursor round-trip. `json.scan` seek. metadata/metric guards raise typed errors; `l2`→`euclidean`.

---

## WS4 — Filters & scope (Python) · #46, #54

### #46 (S1) — `filters.eq()` broken for int/float/bool
**Root cause (`filters.py` `_tag`, lines 19-32).** Emits `integer`/`float`/`boolean`; the
engine's IDL (`idl/v1/schemas/vector.query.json`, `$defs/VectorMetadataFilter`) accepts only
`null`/`bool`/`number`/`string`. Only `str` lines up. The module docstring's own example
(`{"type":"integer","value":5}`) is the broken form. Slipped through because both filter
tests use a string value.
**Fix.** Map `int→number`, `float→number`, `bool→bool`, `str→string` (keep bool-before-int
ordering); fix the docstring example. One function; fixes `query`, `index_query`,
`delete_by_filter` at once. Pure-SDK.
**Tests.** Parametrize `filters.eq` over int/float/bool/str against `vectors.query` + a
`delete_by_filter` int/bool case; a `to_wire()` unit assertion.

### #54 (S2) — scoped views mis-report scope; `at()` rebinds
**Root cause (`__init__.py`).** `at()` (238-252) stores `_branch`/`_space` overrides and
routing uses them correctly, but the `branch`/`space` properties (259-267) return
`self._core.default_branch`/`default_space` — the shared session default — so
`db.at(branch="feat", space="s1").branch/.space == ("default","default")`.
**Fix.** Properties report the effective scope (`self._branch` else session default):
```python
@property
def branch(self): return self._branch if self._branch is not None else self._core.default_branch
@property
def space(self):  return self._space  if self._space  is not None else self._core.default_space
```
Read-only correctness fix; routing untouched. `test_foundation.py:124` still passes (base
handle `_branch is None` → falls back). **`at()` rebind-vs-narrow:** keep rebind for the
patch; fix the docstring to state `at()` rebinds and that **space isolation is routing, not a
security sandbox** (a hard narrow is a behavior change for a later minor).
**Tests.** `db.at(branch="feat", space="s1").branch/.space == ("feat","s1")`; unspecified
axis inherits; rebind documented.

---

## WS5 — Docs (guide/demo) · #47, #49, #55

All in `_data/agent-guide.md` (hand-edited; guarded by `test_agent_guide.py` [each
`db.<ns>` string must still appear] and `test_packaging.py` [`agents_guide()` == bundled]).
Keep all `db.<ns>` mentions. A **wheel rebuild** re-bundles the guide before shipping.

- **#47** — `_data/agent-guide.md:161` says `receipt.commit.timestamp (int µs)` (added in
  1.0.1). It is a **logical counter == `commit.version`**, confirmed (`timestamp == version`).
  Replace with text stating version/timestamp are the same logical commit value (not
  wall-clock), that `as_of` takes the logical value, and that only `event.timestamp` /
  `range_by_time` are wall-clock µs. **README needs no change** (line 140 already correct).
  Optional: drop "(microseconds)" prose in `branches.py:106,111` (first-paragraph prose is
  safe to hand-edit; the `Examples:` blocks are generator-managed — do not touch). Optional
  lock test: `r.commit.timestamp == r.commit.version` and `get(as_of=r.commit.timestamp)`.
- **#49** — the guide's only error example (`_data/agent-guide.md:181-186`) uses
  `db.branches.get("nope")`, which returns `None` (never raises). Replace with
  `db.at(branch="ghost").kv.get("k")`, which genuinely raises `NotFoundError`
  (`not_found.engine.branch`; verified, and README already uses this form).
- **#55** — the guide's branching example (`:165-169`) uses `create()` (empty branch);
  switch to `fork("default", "feature")`, add a create-vs-fork note + `fork_at_version`/
  `fork_at_timestamp`. Also switch `_demo.py:101` `create("experiment")` → `fork("default",
  "experiment")` (currently the exact copy-vs-empty footgun; `test_demo.py` still passes —
  it checks the header, `"on-branch"`, and clean exit). README already uses `fork`.

---

## Sequencing

1. **WS2** (#51/#52) — small, additive Python error-path edits in `_core.py`.
2. **WS4** + **WS5** (#46/#54 + docs) — independent, land any time.
3. **WS3** (#40 + #41/#39/#59/#61) — touches `_results.py` + many namespace call sites; do
   as one batch.
4. **WS1** (#31/#32) — Rust; rebase on WS2 (shared `_core.py`/`lib.rs` lines). **Requires
   `maturin develop` rebuild.** Put the #32 pid guard in `_core.py` alongside WS2.
5. **Version + verify + release.**

## Testing & verification

- New: `tests/test_concurrency.py` (#31/#32), `tests/test_errors.py` (#52), open-failure
  cases in `tests/test_durable.py` (#51). Extend `tests/test_kv_json.py` (#40/#41/#59),
  `tests/test_vectors_events.py` (#46/#61), `tests/test_graph_branch_space.py` (#54/#39).
- Update `tests/test_foundation.py:90-92` (escape-hatch error type) and the version literals.
- `maturin develop` (rebuild for #31/#32), then `python tools/generate.py` +
  `tools/generate_examples.py --check` (drift guards), then full `pytest` (baseline 119
  passed / 7 skipped; expect green + the new tests). Manually re-run the report's repros for
  #31 (threaded), #46, #51, #54.

## Release plan (1.0.2)

- Bump `pyproject.toml` + `Cargo.toml` to `1.0.2`; update SDK-version test literals
  (`test_packaging.py`, `test_foundation.py`); leave `admin.ping().version == "1.0.0"`
  (engine unchanged). Keep `STRATA_CORE_REV` at `9d906ca5`.
- **Compatibility notes for the release:** several previously-untyped failures now raise
  typed `StrataError` subclasses — the intended fixes, but caught-exception types change:
  `open()` errors (`StrataNativeError` → `UnavailableError`); invalid input incl. the
  `db.execute` escape hatch (`ValueError`/`TypeError`/`KeyError` → `InvalidArgumentError`);
  `Page` iteration now yields all pages (`len(page)` stays first-page). `os.fork()` on an
  open handle now raises instead of silently dropping writes.
- Ship via the existing `release.yml` (publish the `v1.0.2` GitHub release → wheels → PyPI).

## Out of scope (file/track for strata-core)

- **Engine bugs:** #33 (int>2⁶³→float), #34 (arrow vector metadata), #35 (tiny vector→zero),
  #36 (WAL delete wipes DB), #37 (bfs caps), #38 (cosine at extremes), #42 (events reverse),
  #43 (range inclusivity), #44 (budget key ignored), #45 (JSONPath `$..`), #48 (arrow import
  events/graphs), #50 (`as_of=0`), #53 (corruption retryable), #56 (branch/space asymmetry),
  #57 (batch caps), #60 (json indexes/path), and the non-SDK parts of #59/#61.
- **#58** — `as_of` on `kv.exists`/`events.*`/`verify_chain`: core commands must add `as_of`
  first; SDK add becomes trivial afterward.
- **Deferred SDK follow-ups (not 1.0.2):** child-safe `Drop`/`close()` hardening for #32;
  hard-narrow `at()` semantics for #54; per-argument (vs central) input validation for #52.
