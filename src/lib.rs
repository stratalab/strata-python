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
//! Data-plane only: built without the `hub` (network) and `inference` (model
//! runtime) executor features, so the wheel is lean and needs no toolchain to
//! install.

use std::path::PathBuf;
use std::sync::Mutex;

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use strata_executor::{Command, Executor, ExecutorError};

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

/// One open Strata database, wrapping a single executor handle.
///
/// The executor is `&mut self` per call; the `Mutex` serializes calls on one
/// handle while the GIL is released for the engine's duration, so other
/// Python threads run meanwhile. A durable database holds an exclusive
/// process lock — a second `open_durable` on the same path surfaces the
/// engine's lock error.
#[pyclass]
struct Handle {
    inner: Mutex<Option<Executor>>,
}

#[pymethods]
impl Handle {
    /// Opens a durable database at `path`, creating it if absent.
    #[staticmethod]
    fn open_durable(path: String) -> PyResult<Self> {
        let executor = Executor::open_durable_local(PathBuf::from(path)).map_err(native_error)?;
        Ok(Self {
            inner: Mutex::new(Some(executor)),
        })
    }

    /// Opens a volatile in-memory database (nothing persists).
    #[staticmethod]
    fn open_cache() -> PyResult<Self> {
        let executor = Executor::open_cache().map_err(native_error)?;
        Ok(Self {
            inner: Mutex::new(Some(executor)),
        })
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
        let command: Command = serde_json::from_str(command_json)
            .map_err(|error| PyValueError::new_err(format!("invalid command: {error}")))?;
        let mut guard = self.inner.lock().expect("handle mutex poisoned");
        let executor = guard.as_mut().ok_or_else(closed_error)?;
        let outcome = py.allow_threads(|| executor.execute(command));
        match outcome {
            Ok(output) => serde_json::to_string(&output).map_err(|error| {
                PyRuntimeError::new_err(format!("envelope serialization failed: {error}"))
            }),
            Err(error) => Err(native_error(error)),
        }
    }

    /// Sets the session default branch and/or space used when a command omits
    /// its own. Raises `ValueError` on an invalid name.
    #[pyo3(signature = (branch=None, space=None))]
    fn set_scope(&self, branch: Option<String>, space: Option<String>) -> PyResult<()> {
        let mut guard = self.inner.lock().expect("handle mutex poisoned");
        let executor = guard.as_mut().ok_or_else(closed_error)?;
        if let Some(branch) = branch {
            executor
                .set_default_branch(branch)
                .map_err(|error| PyValueError::new_err(format!("invalid branch: {error}")))?;
        }
        if let Some(space) = space {
            executor
                .set_default_space(space)
                .map_err(|error| PyValueError::new_err(format!("invalid space: {error}")))?;
        }
        Ok(())
    }

    /// Returns the session default branch.
    fn default_branch(&self) -> PyResult<String> {
        let guard = self.inner.lock().expect("handle mutex poisoned");
        let executor = guard.as_ref().ok_or_else(closed_error)?;
        Ok(executor.default_branch().to_owned())
    }

    /// Returns the session default product space.
    fn default_space(&self) -> PyResult<String> {
        let guard = self.inner.lock().expect("handle mutex poisoned");
        let executor = guard.as_ref().ok_or_else(closed_error)?;
        Ok(executor.default_space().to_owned())
    }

    /// Closes the database handle. Idempotent; further calls raise.
    fn close(&self) -> PyResult<()> {
        let mut guard = self.inner.lock().expect("handle mutex poisoned");
        if let Some(mut executor) = guard.take() {
            executor
                .close()
                .map_err(|error| PyRuntimeError::new_err(format!("close failed: {error}")))?;
        }
        Ok(())
    }
}

/// The offline agent usage guide, embedded from the vendored IDL at build time.
#[pyfunction]
fn agents_guide() -> &'static str {
    include_str!("../idl/v1/agents-guide.md")
}

/// The engine/SDK version this wheel was built against.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn _stratadb(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Handle>()?;
    module.add_function(wrap_pyfunction!(agents_guide, module)?)?;
    module.add_function(wrap_pyfunction!(version, module)?)?;
    module.add(
        "StrataNativeError",
        module.py().get_type::<StrataNativeError>(),
    )?;
    Ok(())
}
