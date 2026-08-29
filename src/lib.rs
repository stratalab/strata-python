//! Native binding for Strata's Python SDK.
//!
//! A deliberately tiny `PyO3` adapter over the executor's serialized command
//! boundary — the same wire the CLI, MCP server, and wasm bindings speak.
//! Commands cross the boundary as JSON strings (`deny_unknown_fields`), and
//! outputs come back as `{"type": ..., "data": ...}` envelopes on success.
//! This crate adds no semantics of its own: the executor owns command
//! behavior, and everything ergonomic lives in pure Python above it.
//!
//! There is no per-command Rust code here. The entire typed API surface is
//! generated in Python from the executor's IDL catalog; the binding only
//! opens a handle, ferries one command string across, and reports failures.
//!
//! Durable opens route through the executor's transport-transparent
//! [`Connection`](strata_executor::ipc::Connection) (unix): the first opener
//! owns the store and may host a socket; later opens broker to the owner, so
//! multiple processes (or handles) share one durable database. On non-unix
//! targets the `ipc` module does not exist and a local-only stand-in with the
//! same surface is used — `ipc="host"/"client"` is rejected in Python first.
//!
//! Data-plane only: built without the `hub` (network) and `inference` (model
//! runtime) executor features, so the wheel is lean and needs no toolchain to
//! install.

use std::path::PathBuf;
use std::sync::RwLock;

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use strata_executor::{
    guard_json_integers, Command, DurabilityMode, DurableLocalOpenOptions, ExecutorError, IpcMode,
};

/// Platform shim: one `Inner` connection type with a uniform surface.
///
/// On unix the executor's `Connection` brokers durable opens across
/// processes; elsewhere a minimal local-only twin keeps the exact same
/// method surface (including the deferred, per-command scope application),
/// so `Handle` below is platform-independent.
#[cfg(unix)]
mod conn {
    #![allow(
        clippy::result_large_err,
        reason = "ExecutorError is the executor's frozen serialized-boundary type; \
                  the executor deliberately declined to box it, so the size is not ours to change"
    )]
    use std::path::PathBuf;

    pub use strata_executor::ipc::Connection as Inner;
    use strata_executor::{
        DurableLocalOpenOptions, Executor, ExecutorError, IpcMode, SessionAccess,
    };

    pub fn open_durable(
        path: PathBuf,
        options: DurableLocalOpenOptions,
        ipc: IpcMode,
    ) -> Result<Inner, ExecutorError> {
        // The Python SDK opens full read-write handles; it exposes no read-only
        // session surface, so it declares the pre-hello default access. A
        // brokered read-only client is a CLI/server concept (`--read-only`) that
        // the SDK does not surface yet.
        Inner::open_durable_local_brokered(path, options, ipc, SessionAccess::ReadWrite)
    }

    pub fn open_cache() -> Result<Inner, ExecutorError> {
        Executor::open_cache().map(Inner::cache)
    }
}

#[cfg(not(unix))]
mod conn {
    #![allow(
        clippy::result_large_err,
        reason = "ExecutorError is the executor's frozen serialized-boundary type; \
                  the executor deliberately declined to box it, so the size is not ours to change"
    )]
    use std::path::PathBuf;
    use std::sync::Mutex;

    use strata_executor::{
        Command, DurableLocalOpenOptions, Executor, ExecutorError, IpcMode, Output,
    };

    /// Local-only stand-in for the unix `Connection`: same surface, no
    /// brokering. Scope is stored and applied per command, mirroring
    /// `Connection::execute`'s Local arm, so validation timing is identical
    /// across platforms.
    pub struct Inner {
        executor: Mutex<Executor>,
        scope: Mutex<(String, String)>,
    }

    impl Inner {
        fn wrap(executor: Executor) -> Self {
            let scope = (
                executor.default_branch().to_owned(),
                executor.default_space().to_owned(),
            );
            Self {
                executor: Mutex::new(executor),
                scope: Mutex::new(scope),
            }
        }

        pub fn execute(&self, command: Command) -> Result<Output, ExecutorError> {
            let (branch, space) = self.scope.lock().expect("scope lock poisoned").clone();
            let mut executor = self.executor.lock().expect("executor lock poisoned");
            executor.set_default_branch(branch)?;
            executor.set_default_space(space)?;
            executor.execute(command)
        }

        pub fn set_default_branch(&self, branch: String) {
            self.scope.lock().expect("scope lock poisoned").0 = branch;
        }

        pub fn set_default_space(&self, space: String) {
            self.scope.lock().expect("scope lock poisoned").1 = space;
        }

        #[must_use]
        pub fn default_branch(&self) -> String {
            self.scope.lock().expect("scope lock poisoned").0.clone()
        }

        #[must_use]
        pub fn default_space(&self) -> String {
            self.scope.lock().expect("scope lock poisoned").1.clone()
        }

        pub fn close(self) -> Result<(), ExecutorError> {
            let mut executor = self
                .executor
                .into_inner()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            executor.close()
        }
    }

    pub fn open_durable(
        path: PathBuf,
        options: DurableLocalOpenOptions,
        ipc: IpcMode,
    ) -> Result<Inner, ExecutorError> {
        // host/client are rejected by the Python layer on non-unix targets;
        // every reachable mode here means a plain single-process open.
        let _ = ipc;
        Executor::open_durable_local_with_options(path, options).map(Inner::wrap)
    }

    pub fn open_cache() -> Result<Inner, ExecutorError> {
        Executor::open_cache().map(Inner::wrap)
    }
}

create_exception!(
    _stratadb,
    StrataNativeError,
    PyException,
    "Raised on a domain failure. Its single argument is the executor error \
     status as a JSON string; the Python layer maps it to a typed StrataError."
);

/// Serializes an executor error (transparent over the public error status)
/// into a `StrataNativeError` carrying its JSON payload, so the Python layer
/// can raise a typed exception matched on the stable `code`.
fn native_error(error: ExecutorError) -> PyErr {
    match serde_json::to_string(&error) {
        Ok(payload) => StrataNativeError::new_err(payload),
        Err(serde_error) => {
            PyRuntimeError::new_err(format!("error serialization failed: {serde_error}"))
        }
    }
}

fn closed_error() -> PyErr {
    PyRuntimeError::new_err("database handle is closed")
}

/// A call's outcome carried back across the `allow_threads` (no-GIL) boundary.
///
/// A `PyErr` cannot be constructed without the GIL, so the closure that runs
/// with the GIL released returns this instead, and the caller converts it to a
/// `PyErr` after the GIL is re-acquired.
#[allow(
    clippy::large_enum_variant,
    reason = "ExecutorError is the executor's frozen serialized-boundary type; it \
              is only ever a short-lived local here, so the size is not worth boxing"
)]
enum CallError {
    Closed,
    Domain(ExecutorError),
}

/// One open Strata database, wrapping one connection.
///
/// The connection's `execute` is `&self` (it synchronizes internally at the
/// right granularity — the executor mutex locally, the socket client mutex
/// remotely), so calls take this lock in `read` mode and only `close` takes
/// `write`. Every lock is taken *inside* `Python::allow_threads`, i.e. with
/// the GIL released, so a thread waiting on a busy handle never holds the GIL
/// while it waits (issue #31). A durable database has one owner per path; on
/// unix additional opens broker to the owner over IPC instead of failing.
#[pyclass]
struct Handle {
    inner: RwLock<Option<conn::Inner>>,
}

impl Handle {
    fn wrap(inner: conn::Inner) -> Self {
        Self {
            inner: RwLock::new(Some(inner)),
        }
    }
}

#[pymethods]
impl Handle {
    /// Opens a durable database at `path`, creating it if absent.
    ///
    /// `durability` selects the commit-durability mode: `"standard"` (default)
    /// or `"always"`. `ipc` selects the multi-process policy: `"host"`
    /// (default — own the store or broker to its owner, hosting a socket for
    /// others when owning), `"client"` (broker on contention, never host), or
    /// `"off"` (raw exclusive open, no brokering). `memory_budget` sets the
    /// total storage memory budget in bytes for the opened database; when
    /// omitted the engine derives one from host memory at open. The Python
    /// layer validates all three; the checks here are backstops (the storage
    /// layer rejects a budget below its minimum with a typed error).
    #[staticmethod]
    #[pyo3(signature = (path, durability=None, ipc=None, memory_budget=None))]
    fn open_durable(
        path: String,
        durability: Option<&str>,
        ipc: Option<&str>,
        memory_budget: Option<u64>,
    ) -> PyResult<Self> {
        let mut options = DurableLocalOpenOptions::new();
        if let Some(total_bytes) = memory_budget {
            options = options.with_memory_budget(total_bytes);
        }
        match durability {
            None | Some("standard") => {}
            Some("always") => options = options.with_durability(DurabilityMode::Always),
            Some(other) => {
                return Err(PyValueError::new_err(format!(
                    "invalid durability {other:?}: expected \"standard\" or \"always\""
                )))
            }
        }
        let ipc = match ipc {
            None | Some("host") => IpcMode::Host,
            Some("client") => IpcMode::Client,
            Some("off") => IpcMode::Off,
            Some(other) => {
                return Err(PyValueError::new_err(format!(
                    "invalid ipc mode {other:?}: expected \"host\", \"client\", or \"off\""
                )))
            }
        };
        let inner = conn::open_durable(PathBuf::from(path), options, ipc).map_err(native_error)?;
        Ok(Self::wrap(inner))
    }

    /// Opens a volatile in-memory database (nothing persists, no brokering).
    #[staticmethod]
    fn open_cache() -> PyResult<Self> {
        let inner = conn::open_cache().map_err(native_error)?;
        Ok(Self::wrap(inner))
    }

    /// Executes one serialized command and returns its JSON output envelope.
    ///
    /// Raises `ValueError` when `command_json` is not a valid command object
    /// (the deserializer names the offending field and the valid set), and
    /// `StrataNativeError` carrying the error-status JSON on a domain failure.
    /// Successful commands — including misses, which are ordinary outputs —
    /// return the `{"type": ..., "data": ...}` envelope.
    #[allow(
        clippy::result_large_err,
        reason = "ExecutorError is the executor's frozen serialized-boundary type; \
                  the executor deliberately declined to box it, so the size is not ours to change"
    )]
    fn execute(&self, py: Python<'_>, command_json: &str) -> PyResult<String> {
        // Reject JSON integers outside i64/u64 before serde silently coerces
        // them to a lossy f64 and persists the damage (strata-core #2687). A
        // cheap text scan that touches no lock, so it runs under the GIL.
        guard_json_integers(command_json).map_err(native_error)?;
        // Parse under the GIL: it is cheap and a `PyValueError` needs the GIL,
        // so an invalid command fails fast before any locking.
        let command: Command = serde_json::from_str(command_json)
            .map_err(|error| PyValueError::new_err(format!("invalid command: {error}")))?;
        // Release the GIL *before* locking (issue #31): a reader blocked
        // behind `close`'s write lock — or, downstream, on the connection's
        // internal executor/client mutex — waits with the GIL released.
        let outcome = py.allow_threads(|| {
            let guard = self.inner.read().expect("handle lock poisoned");
            let connection = guard.as_ref().ok_or(CallError::Closed)?;
            connection.execute(command).map_err(CallError::Domain)
        });
        // Back under the GIL: safe to build `PyErr` and serialize the envelope.
        match outcome {
            Ok(output) => serde_json::to_string(&output).map_err(|error| {
                PyRuntimeError::new_err(format!("envelope serialization failed: {error}"))
            }),
            Err(CallError::Closed) => Err(closed_error()),
            Err(CallError::Domain(error)) => Err(native_error(error)),
        }
    }

    /// Sets the session default branch and/or space used when a command omits
    /// its own. The names are applied to each subsequent command (and
    /// validated there — an invalid name surfaces as that command's typed
    /// error), matching the connection's brokered-scope semantics.
    #[pyo3(signature = (branch=None, space=None))]
    fn set_scope(
        &self,
        py: Python<'_>,
        branch: Option<String>,
        space: Option<String>,
    ) -> PyResult<()> {
        let result: Result<(), ()> = py.allow_threads(|| {
            let guard = self.inner.read().expect("handle lock poisoned");
            let connection = guard.as_ref().ok_or(())?;
            if let Some(branch) = branch {
                connection.set_default_branch(branch);
            }
            if let Some(space) = space {
                connection.set_default_space(space);
            }
            Ok(())
        });
        result.map_err(|()| closed_error())
    }

    /// Returns the session default branch.
    fn default_branch(&self, py: Python<'_>) -> PyResult<String> {
        py.allow_threads(|| {
            let guard = self.inner.read().expect("handle lock poisoned");
            guard.as_ref().map(conn::Inner::default_branch).ok_or(())
        })
        .map_err(|()| closed_error())
    }

    /// Returns the session default product space.
    fn default_space(&self, py: Python<'_>) -> PyResult<String> {
        py.allow_threads(|| {
            let guard = self.inner.read().expect("handle lock poisoned");
            guard.as_ref().map(conn::Inner::default_space).ok_or(())
        })
        .map_err(|()| closed_error())
    }

    /// Closes the database handle: an owner drops its socket (if hosting) and
    /// closes the store; a brokered client just drops its socket. Idempotent;
    /// further calls raise.
    fn close(&self, py: Python<'_>) -> PyResult<()> {
        let result: Result<(), String> = py.allow_threads(|| {
            let mut guard = self.inner.write().expect("handle lock poisoned");
            if let Some(connection) = guard.take() {
                connection.close().map_err(|error| error.to_string())?;
            }
            Ok(())
        });
        result.map_err(|message| PyRuntimeError::new_err(format!("close failed: {message}")))
    }
}

/// The engine/SDK version this wheel was built against.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn _stratadb(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Handle>()?;
    module.add_function(wrap_pyfunction!(version, module)?)?;
    module.add(
        "StrataNativeError",
        module.py().get_type::<StrataNativeError>(),
    )?;
    Ok(())
}
