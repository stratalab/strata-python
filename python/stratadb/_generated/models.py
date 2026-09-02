"""Generated from the Strata IDL — do not edit by hand.

Regenerate with ``python tools/generate.py``. The CI drift guard fails if this
file is stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

from .. import _wire

@dataclass
class AdminCapabilities:
    """Capability flags in describe output."""
    arrow: bool
    event: bool
    graph_core: bool
    inference: bool
    json: bool
    kv: bool
    vector: bool
    vector_index: bool

    @classmethod
    def from_wire(cls, d: dict) -> "AdminCapabilities":
        return cls(
            arrow=d['arrow'],
            event=d['event'],
            graph_core=d['graph_core'],
            inference=d['inference'],
            json=d['json'],
            kv=d['kv'],
            vector=d['vector'],
            vector_index=d['vector_index'],
        )


@dataclass
class AdminConfig:
    """Sanitized config output."""
    created: bool
    default_branch: str
    durable: bool
    target: "AdminOpenTarget"

    @classmethod
    def from_wire(cls, d: dict) -> "AdminConfig":
        return cls(
            created=d['created'],
            default_branch=d['default_branch'],
            durable=d['durable'],
            target=AdminOpenTarget(d['target']),
        )


class AdminControlStatus(str, Enum):
    """Control-plane status exposed in admin health outputs."""
    HEALTHY = 'healthy'
    MISSING = 'missing'
    CORRUPT = 'corrupt'
    UNAVAILABLE = 'unavailable'


@dataclass
class AdminDatabaseInfo:
    """Database information output."""
    branch_count: int
    created: bool
    default_branch: str
    durable: bool
    memory_budget: "AdminMemoryBudget"
    open: bool
    space_count: int
    target: "AdminOpenTarget"
    version: str

    @classmethod
    def from_wire(cls, d: dict) -> "AdminDatabaseInfo":
        return cls(
            branch_count=d['branch_count'],
            created=d['created'],
            default_branch=d['default_branch'],
            durable=d['durable'],
            memory_budget=AdminMemoryBudget.from_wire(d['memory_budget']),
            open=d['open'],
            space_count=d['space_count'],
            target=AdminOpenTarget(d['target']),
            version=d['version'],
        )


@dataclass
class AdminDescribe:
    """Database describe output."""
    branch: str
    branches: List[str]
    capabilities: "AdminCapabilities"
    config: "AdminConfig"
    default_branch: str
    primitives: "AdminPrimitives"
    spaces: List[str]
    target: "AdminOpenTarget"
    version: str

    @classmethod
    def from_wire(cls, d: dict) -> "AdminDescribe":
        return cls(
            branch=d['branch'],
            branches=[_x for _x in (d['branches'] or [])],
            capabilities=AdminCapabilities.from_wire(d['capabilities']),
            config=AdminConfig.from_wire(d['config']),
            default_branch=d['default_branch'],
            primitives=AdminPrimitives.from_wire(d['primitives']),
            spaces=[_x for _x in (d['spaces'] or [])],
            target=AdminOpenTarget(d['target']),
            version=d['version'],
        )


@dataclass
class AdminGraph:
    """Graph summary in describe output."""
    edge_count: int
    name: str
    node_count: int

    @classmethod
    def from_wire(cls, d: dict) -> "AdminGraph":
        return cls(
            edge_count=d['edge_count'],
            name=d['name'],
            node_count=d['node_count'],
        )


@dataclass
class AdminHealth:
    """Health output."""
    branch_catalog: "AdminControlStatus"
    branch_count: int
    default_branch: str
    identity: "AdminControlStatus"
    registry: "AdminControlStatus"
    status: "AdminHealthStatus"
    space_catalog: Optional["AdminControlStatus"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "AdminHealth":
        return cls(
            branch_catalog=AdminControlStatus(d['branch_catalog']),
            branch_count=d['branch_count'],
            default_branch=d['default_branch'],
            identity=AdminControlStatus(d['identity']),
            registry=AdminControlStatus(d['registry']),
            status=AdminHealthStatus(d['status']),
            space_catalog=(None if d.get('space_catalog') is None else AdminControlStatus(d['space_catalog'])),
        )


class AdminHealthStatus(str, Enum):
    """Health status exposed in admin outputs."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'


@dataclass
class AdminIpcClient:
    """One connected IPC client, as reported by `ipc_status`. Display identity"""
    access: "SessionAccess"
    protocol: int
    name: Optional[str] = None
    pid: Optional[int] = None
    version: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "AdminIpcClient":
        return cls(
            access=SessionAccess(d['access']),
            protocol=d['protocol'],
            name=(None if d.get('name') is None else d['name']),
            pid=(None if d.get('pid') is None else d['pid']),
            version=(None if d.get('version') is None else d['version']),
        )


@dataclass
class AdminIpcStatus:
    """Multi-process IPC status output."""
    client_count: int
    hosting: bool
    is_owner: bool
    clients: Optional[List["AdminIpcClient"]] = None
    owner_pid: Optional[int] = None
    socket_path: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "AdminIpcStatus":
        return cls(
            client_count=d['client_count'],
            hosting=d['hosting'],
            is_owner=d['is_owner'],
            clients=(None if d.get('clients') is None else [AdminIpcClient.from_wire(_x) for _x in (d['clients'] or [])]),
            owner_pid=(None if d.get('owner_pid') is None else d['owner_pid']),
            socket_path=(None if d.get('socket_path') is None else d['socket_path']),
        )


@dataclass
class AdminIpcStop:
    """Multi-process IPC stop output."""
    stopped: bool

    @classmethod
    def from_wire(cls, d: dict) -> "AdminIpcStop":
        return cls(
            stopped=d['stopped'],
        )


@dataclass
class AdminMemoryBudget:
    """Storage memory budget provenance and total for `admin.info`."""
    source: "AdminMemoryBudgetSource"
    total_bytes: int
    usable_host_bytes: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "AdminMemoryBudget":
        return cls(
            source=AdminMemoryBudgetSource(d['source']),
            total_bytes=d['total_bytes'],
            usable_host_bytes=(None if d.get('usable_host_bytes') is None else d['usable_host_bytes']),
        )


class AdminMemoryBudgetSource(str, Enum):
    """How an opened database's storage memory budget was chosen."""
    EXPLICIT = 'explicit'
    DERIVED_FROM_HOST = 'derived_from_host'
    FIXED_DEFAULT = 'fixed_default'


@dataclass
class AdminMetrics:
    """Metrics output."""
    branch_count: int
    control_status: "AdminHealthStatus"
    durable: bool
    open: bool
    space_count: int
    target: "AdminOpenTarget"

    @classmethod
    def from_wire(cls, d: dict) -> "AdminMetrics":
        return cls(
            branch_count=d['branch_count'],
            control_status=AdminHealthStatus(d['control_status']),
            durable=d['durable'],
            open=d['open'],
            space_count=d['space_count'],
            target=AdminOpenTarget(d['target']),
        )


class AdminOpenTarget(str, Enum):
    """Database open target exposed in admin outputs."""
    CACHE = 'cache'
    DURABLE_LOCAL = 'durable_local'


@dataclass
class AdminPrimitives:
    """Primitive summaries in describe output."""
    event_count: int
    graphs: List["AdminGraph"]
    json_count: int
    kv_count: int
    vector_collections: List["AdminVectorCollection"]

    @classmethod
    def from_wire(cls, d: dict) -> "AdminPrimitives":
        return cls(
            event_count=d['event_count'],
            graphs=[AdminGraph.from_wire(_x) for _x in (d['graphs'] or [])],
            json_count=d['json_count'],
            kv_count=d['kv_count'],
            vector_collections=[AdminVectorCollection.from_wire(_x) for _x in (d['vector_collections'] or [])],
        )


@dataclass
class AdminVectorCollection:
    """Vector collection summary in describe output."""
    count: int
    dimension: int
    metric: "VectorDistanceMetric"
    name: str

    @classmethod
    def from_wire(cls, d: dict) -> "AdminVectorCollection":
        return cls(
            count=d['count'],
            dimension=d['dimension'],
            metric=VectorDistanceMetric(d['metric']),
            name=d['name'],
        )


class ArrowExportPrimitive(str, Enum):
    """Product primitive selected by Arrow export."""
    KV = 'kv'
    JSON = 'json'
    EVENT = 'event'
    VECTOR = 'vector'
    GRAPH = 'graph'


@dataclass
class ArrowExportResult:
    """Arrow export summary."""
    format: "ArrowFileFormat"
    paths: List[str]
    primitive: "ArrowExportPrimitive"
    row_count: int
    size_bytes: int

    @classmethod
    def from_wire(cls, d: dict) -> "ArrowExportResult":
        return cls(
            format=ArrowFileFormat(d['format']),
            paths=[_x for _x in (d['paths'] or [])],
            primitive=ArrowExportPrimitive(d['primitive']),
            row_count=d['row_count'],
            size_bytes=d['size_bytes'],
        )


class ArrowFileFormat(str, Enum):
    """Arrow file format selected for import/export."""
    PARQUET = 'parquet'
    CSV = 'csv'
    JSONL = 'jsonl'


@dataclass
class ArrowImportResult:
    """Arrow import summary."""
    batches_processed: int
    file_path: str
    rows_imported: int
    rows_skipped: int
    target: "ArrowImportTarget"

    @classmethod
    def from_wire(cls, d: dict) -> "ArrowImportResult":
        return cls(
            batches_processed=d['batches_processed'],
            file_path=d['file_path'],
            rows_imported=d['rows_imported'],
            rows_skipped=d['rows_skipped'],
            target=ArrowImportTarget(d['target']),
        )


class ArrowImportTarget(str, Enum):
    """Product primitive targeted by Arrow import."""
    KV = 'kv'
    JSON = 'json'
    VECTOR = 'vector'
    GRAPH = 'graph'
    EVENT = 'event'


@dataclass
class BatchEventEntry:
    """One event batch append entry."""
    event_type: str
    payload: Any

    @classmethod
    def from_wire(cls, d: dict) -> "BatchEventEntry":
        return cls(
            event_type=d['event_type'],
            payload=d['payload'],
        )


@dataclass
class BatchExistsItemResult:
    """Positional batch existence result payload."""
    exists: bool
    key: bytes

    @classmethod
    def from_wire(cls, d: dict) -> "BatchExistsItemResult":
        return cls(
            exists=d['exists'],
            key=_wire.b64d(d['key']),
        )


@dataclass
class BatchExistsPresence:
    """Positional batch-existence item: whether the key at this position exists."""
    exists: bool

    @classmethod
    def from_wire(cls, d: dict) -> "BatchExistsPresence":
        return cls(
            exists=d['exists'],
        )


@dataclass
class BatchGetItemResult:
    """Positional batch read result payload."""
    found: bool
    key: bytes
    timestamp: Optional[int] = None
    value: Optional[bytes] = None
    version: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchGetItemResult":
        return cls(
            found=d['found'],
            key=_wire.b64d(d['key']),
            timestamp=(None if d.get('timestamp') is None else d['timestamp']),
            value=(None if d.get('value') is None else _wire.b64d(d['value'])),
            version=(None if d.get('version') is None else d['version']),
        )


@dataclass
class BatchItem:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["BatchItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else BatchItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem10:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["GraphBatchItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem10":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else GraphBatchItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem2:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["BatchGetItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem2":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else BatchGetItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem3:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["JsonBatchItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem3":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else JsonBatchItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem4:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["JsonBatchGetItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem4":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else JsonBatchGetItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem5:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["BatchExistsItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem5":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else BatchExistsItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem6:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["BatchExistsPresence"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem6":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else BatchExistsPresence.from_wire(d['result'])),
        )


@dataclass
class BatchItem7:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["VectorBatchItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem7":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else VectorBatchItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem8:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["VectorBatchGetItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem8":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else VectorBatchGetItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItem9:
    """Shared positional item wrapper for all public batch responses."""
    applied: bool
    index: int
    status: "BatchItemStatus"
    commit: Optional["CommitReceipt"] = None
    effect: Optional["MutationEffect"] = None
    error: Optional["ErrorStatus"] = None
    result: Optional["EventBatchAppendItemResult"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItem9":
        return cls(
            applied=d['applied'],
            index=d['index'],
            status=BatchItemStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
            effect=(None if d.get('effect') is None else MutationEffect.from_wire(d['effect'])),
            error=(None if d.get('error') is None else ErrorStatus.from_wire(d['error'])),
            result=(None if d.get('result') is None else EventBatchAppendItemResult.from_wire(d['result'])),
        )


@dataclass
class BatchItemResult:
    """Positional batch write result payload."""
    key: bytes

    @classmethod
    def from_wire(cls, d: dict) -> "BatchItemResult":
        return cls(
            key=_wire.b64d(d['key']),
        )


class BatchItemStatus(str, Enum):
    """Normalized positional item status within a batch response."""
    OK = 'ok'
    MISS = 'miss'
    ERROR = 'error'


@dataclass
class BatchJsonDeleteEntry:
    """Entry for a batch JSON delete."""
    key: str
    path: str

    @classmethod
    def from_wire(cls, d: dict) -> "BatchJsonDeleteEntry":
        return cls(
            key=d['key'],
            path=d['path'],
        )


@dataclass
class BatchJsonEntry:
    """Entry for a batch JSON set."""
    key: str
    path: str
    value: Any

    @classmethod
    def from_wire(cls, d: dict) -> "BatchJsonEntry":
        return cls(
            key=d['key'],
            path=d['path'],
            value=d['value'],
        )


@dataclass
class BatchJsonGetEntry:
    """Entry for a batch JSON get."""
    key: str
    path: str

    @classmethod
    def from_wire(cls, d: dict) -> "BatchJsonGetEntry":
        return cls(
            key=d['key'],
            path=d['path'],
        )


@dataclass
class BatchKvEntry:
    """Entry for a batch KV write."""
    key: bytes
    value: bytes

    @classmethod
    def from_wire(cls, d: dict) -> "BatchKvEntry":
        return cls(
            key=_wire.b64d(d['key']),
            value=_wire.b64d(d['value']),
        )


class BatchMode(str, Enum):
    """Batch execution semantics."""
    ATOMIC = 'atomic'
    ITEMWISE = 'itemwise'


@dataclass
class BatchResult:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult":
        return cls(
            applied=d['applied'],
            items=[BatchItem.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult2:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem2"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult2":
        return cls(
            applied=d['applied'],
            items=[BatchItem2.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult3:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem3"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult3":
        return cls(
            applied=d['applied'],
            items=[BatchItem3.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult4:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem4"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult4":
        return cls(
            applied=d['applied'],
            items=[BatchItem4.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult5:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem5"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult5":
        return cls(
            applied=d['applied'],
            items=[BatchItem5.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult6:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem6"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult6":
        return cls(
            applied=d['applied'],
            items=[BatchItem6.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult7:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem7"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult7":
        return cls(
            applied=d['applied'],
            items=[BatchItem7.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult8:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem8"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult8":
        return cls(
            applied=d['applied'],
            items=[BatchItem8.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


@dataclass
class BatchResult9:
    """Shared batch response wrapper for all public batch commands."""
    applied: bool
    items: List["BatchItem9"]
    mode: "BatchMode"
    status: "BatchStatus"
    commit: Optional["CommitReceipt"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchResult9":
        return cls(
            applied=d['applied'],
            items=[BatchItem9.from_wire(_x) for _x in (d['items'] or [])],
            mode=BatchMode(d['mode']),
            status=BatchStatus(d['status']),
            commit=(None if d.get('commit') is None else CommitReceipt.from_wire(d['commit'])),
        )


class BatchStatus(str, Enum):
    """Normalized batch-level outcome status."""
    OK = 'ok'
    PARTIAL = 'partial'
    ERROR = 'error'


@dataclass
class BatchVectorEntry:
    """One vector batch upsert entry."""
    key: str
    vector: List[float]
    metadata: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BatchVectorEntry":
        return cls(
            key=d['key'],
            vector=[_x for _x in (d['vector'] or [])],
            metadata=(None if d.get('metadata') is None else d['metadata']),
        )


@dataclass
class BranchCleanupItem:
    """Cleanup facts for branch deletion."""
    protected_tables: int
    releasable_tables: int
    removed_refs: int

    @classmethod
    def from_wire(cls, d: dict) -> "BranchCleanupItem":
        return cls(
            protected_tables=d['protected_tables'],
            releasable_tables=d['releasable_tables'],
            removed_refs=d['removed_refs'],
        )


@dataclass
class BranchComparisonItem:
    """The result of comparing two branches, exposed through the command boundary."""
    branch_a: str
    branch_b: str
    spaces: List["SpaceComparisonItem"]

    @classmethod
    def from_wire(cls, d: dict) -> "BranchComparisonItem":
        return cls(
            branch_a=d['branch_a'],
            branch_b=d['branch_b'],
            spaces=[SpaceComparisonItem.from_wire(_x) for _x in (d['spaces'] or [])],
        )


@dataclass
class BranchItem:
    """Branch summary exposed through the command boundary."""
    branch_id: str
    generation: int
    name: str
    state_revision: int
    status: "BranchStatus"
    created_at: Optional[int] = None
    deleted_at: Optional[int] = None
    merge_parent: Optional["BranchMergeItem"] = None
    parent: Optional["BranchParentItem"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BranchItem":
        return cls(
            branch_id=d['branch_id'],
            generation=d['generation'],
            name=d['name'],
            state_revision=d['state_revision'],
            status=BranchStatus(d['status']),
            created_at=(None if d.get('created_at') is None else d['created_at']),
            deleted_at=(None if d.get('deleted_at') is None else d['deleted_at']),
            merge_parent=(None if d.get('merge_parent') is None else BranchMergeItem.from_wire(d['merge_parent'])),
            parent=(None if d.get('parent') is None else BranchParentItem.from_wire(d['parent'])),
        )


@dataclass
class BranchMergeItem:
    """Promotion (merge) lineage exposed through the command boundary: the source"""
    merged_at: int
    source_branch_id: str
    source_generation: int
    source_name: str
    merged_timestamp: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BranchMergeItem":
        return cls(
            merged_at=d['merged_at'],
            source_branch_id=d['source_branch_id'],
            source_generation=d['source_generation'],
            source_name=d['source_name'],
            merged_timestamp=(None if d.get('merged_timestamp') is None else d['merged_timestamp']),
        )


@dataclass
class BranchParentItem:
    """Fork parent facts exposed through the command boundary."""
    branch_id: str
    fork_version: int
    generation: int
    name: str
    fork_timestamp: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BranchParentItem":
        return cls(
            branch_id=d['branch_id'],
            fork_version=d['fork_version'],
            generation=d['generation'],
            name=d['name'],
            fork_timestamp=(None if d.get('fork_timestamp') is None else d['fork_timestamp']),
        )


@dataclass
class BranchPreviewItem:
    """The result of previewing a promotion of `source` into `target`, exposed"""
    branch_point: int
    conflicts: List["PreviewConflictItem"]
    source: str
    strategy: "PromotionStrategy"
    target: str
    capabilities_covered: Optional[List["ComparedCapability"]] = None
    capabilities_unsupported: Optional[List["ComparedCapability"]] = None
    derived_state: Optional[List["DerivedStateReportItem"]] = None
    spaces_covered: Optional[List[str]] = None

    @classmethod
    def from_wire(cls, d: dict) -> "BranchPreviewItem":
        return cls(
            branch_point=d['branch_point'],
            conflicts=[PreviewConflictItem.from_wire(_x) for _x in (d['conflicts'] or [])],
            source=d['source'],
            strategy=PromotionStrategy(d['strategy']),
            target=d['target'],
            capabilities_covered=(None if d.get('capabilities_covered') is None else [ComparedCapability(_x) for _x in (d['capabilities_covered'] or [])]),
            capabilities_unsupported=(None if d.get('capabilities_unsupported') is None else [ComparedCapability(_x) for _x in (d['capabilities_unsupported'] or [])]),
            derived_state=(None if d.get('derived_state') is None else [DerivedStateReportItem.from_wire(_x) for _x in (d['derived_state'] or [])]),
            spaces_covered=(None if d.get('spaces_covered') is None else [_x for _x in (d['spaces_covered'] or [])]),
        )


class BranchStatus(str, Enum):
    """Branch status exposed through the command boundary."""
    ACTIVE = 'active'
    DELETED = 'deleted'


class CommitDurability(str, Enum):
    """Per-commit durability, as storage attested it at acknowledgement time."""
    NOT_DURABLE = 'not_durable'
    STANDARD = 'standard'
    ALWAYS = 'always'
    UNCERTAIN = 'uncertain'


class CommitOutcomeStatus(str, Enum):
    """V1 commit outcome status."""
    NOT_APPLICABLE = 'not_applicable'
    NOT_STARTED = 'not_started'
    DEFINITELY_NOT_COMMITTED = 'definitely_not_committed'
    MAYBE_COMMITTED = 'maybe_committed'
    COMMITTED_POST_COMMIT_FAILED = 'committed_post_commit_failed'


@dataclass
class CommitReceipt:
    """Commit facts returned by mutating operations."""
    delete_count: int
    durability: "CommitDurability"
    put_count: int
    timestamp: int
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "CommitReceipt":
        return cls(
            delete_count=d['delete_count'],
            durability=CommitDurability(d['durability']),
            put_count=d['put_count'],
            timestamp=d['timestamp'],
            version=d['version'],
        )


class ComparedCapability(str, Enum):
    """The data capability a branch comparison entry belongs to."""
    KEY_VALUE = 'key_value'
    JSON = 'json'
    VECTOR = 'vector'
    VECTOR_COLLECTION = 'vector_collection'
    EVENT = 'event'
    GRAPH_METADATA = 'graph_metadata'
    GRAPH_NODE = 'graph_node'
    GRAPH_EDGE = 'graph_edge'
    GRAPH_ONTOLOGY = 'graph_ontology'


@dataclass
class ComparedEntityItem:
    """One entity that differs between two branches, exposed through the command"""
    identity: bytes
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "ComparedEntityItem":
        return cls(
            identity=_wire.b64d(d['identity']),
            version=d['version'],
        )


class ConflictKind(str, Enum):
    """How two branches diverged on one entity since their branch point."""
    VALUE_DIVERGENCE = 'value_divergence'
    MODIFY_DELETE_DIVERGENCE = 'modify_delete_divergence'
    INCOMPATIBLE_COLLECTION = 'incompatible_collection'


class ConflictStrategyResult(str, Enum):
    """What the selected strategy did with a conflict."""
    REFUSED = 'refused'
    SOURCE_WINS = 'source_wins'


class DerivedStateDisposition(str, Enum):
    """Whether a capability's derived-state rows remain correct after a promotion or"""
    CURRENT = 'current'
    REBUILD_REQUIRED = 'rebuild_required'


@dataclass
class DerivedStateReportItem:
    """One capability's derived-state disposition after a promotion or preview."""
    capability: "ComparedCapability"
    disposition: "DerivedStateDisposition"

    @classmethod
    def from_wire(cls, d: dict) -> "DerivedStateReportItem":
        return cls(
            capability=ComparedCapability(d['capability']),
            disposition=DerivedStateDisposition(d['disposition']),
        )


class ErrorClass(str, Enum):
    """V1 public error class."""
    NOT_FOUND = 'not_found'
    ALREADY_EXISTS = 'already_exists'
    INVALID_ARGUMENT = 'invalid_argument'
    FAILED_PRECONDITION = 'failed_precondition'
    ACCESS_DENIED = 'access_denied'
    CONFLICT = 'conflict'
    AMBIGUOUS_COMMIT = 'ambiguous_commit'
    HISTORY_UNAVAILABLE = 'history_unavailable'
    UNSUPPORTED = 'unsupported'
    RESOURCE_EXHAUSTED = 'resource_exhausted'
    UNAVAILABLE = 'unavailable'
    IO = 'io'
    CORRUPTION = 'corruption'
    SERIALIZATION = 'serialization'
    INTERNAL = 'internal'


@dataclass
class ErrorDetail:
    """Redacted structured error detail."""
    key: str
    value: str

    @classmethod
    def from_wire(cls, d: dict) -> "ErrorDetail":
        return cls(
            key=d['key'],
            value=d['value'],
        )


@dataclass
class ErrorStatus:
    """Public V1 executor error status."""
    class_: "ErrorClass"
    code: str
    commit_outcome: "CommitOutcomeStatus"
    docs_url: str
    message: str
    reference_id: str
    retry_policy: "RetryPolicy"
    retryable: bool
    suggested_fix: str
    details: Optional[List["ErrorDetail"]] = None
    hints: Optional[List[str]] = None
    trace_id: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "ErrorStatus":
        return cls(
            class_=ErrorClass(d['class']),
            code=d['code'],
            commit_outcome=CommitOutcomeStatus(d['commit_outcome']),
            docs_url=d['docs_url'],
            message=d['message'],
            reference_id=d['reference_id'],
            retry_policy=RetryPolicy(d['retry_policy']),
            retryable=d['retryable'],
            suggested_fix=d['suggested_fix'],
            details=(None if d.get('details') is None else [ErrorDetail.from_wire(_x) for _x in (d['details'] or [])]),
            hints=(None if d.get('hints') is None else [_x for _x in (d['hints'] or [])]),
            trace_id=(None if d.get('trace_id') is None else d['trace_id']),
        )


@dataclass
class EventBatchAppendItemResult:
    """Positional event batch append result payload."""
    event_type: Optional[str] = None
    sequence: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "EventBatchAppendItemResult":
        return cls(
            event_type=(None if d.get('event_type') is None else d['event_type']),
            sequence=(None if d.get('sequence') is None else d['sequence']),
        )


@dataclass
class EventChainVerification:
    """Event hash-chain verification result."""
    length: int
    valid: bool
    error: Optional[str] = None
    first_invalid: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "EventChainVerification":
        return cls(
            length=d['length'],
            valid=d['valid'],
            error=(None if d.get('error') is None else d['error']),
            first_invalid=(None if d.get('first_invalid') is None else d['first_invalid']),
        )


@dataclass
class EventData:
    """Event record payload and chain facts."""
    event_type: str
    hash: str
    payload: Any
    previous_hash: str
    sequence: int
    timestamp: int

    @classmethod
    def from_wire(cls, d: dict) -> "EventData":
        return cls(
            event_type=d['event_type'],
            hash=d['hash'],
            payload=d['payload'],
            previous_hash=d['previous_hash'],
            sequence=d['sequence'],
            timestamp=d['timestamp'],
        )


class EventRangeDirection(str, Enum):
    """Event range direction exposed through the command boundary."""
    FORWARD = 'forward'
    REVERSE = 'reverse'


@dataclass
class EventVersionedData:
    """Event record with commit metadata."""
    event: "EventData"
    timestamp: int
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "EventVersionedData":
        return cls(
            event=EventData.from_wire(d['event']),
            timestamp=d['timestamp'],
            version=d['version'],
        )


@dataclass
class GraphAnalyticsBudget:
    """Optional size bounds for one graph analytics snapshot (input form)."""
    max_edges: Optional[int] = None
    max_nodes: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphAnalyticsBudget":
        return cls(
            max_edges=(None if d.get('max_edges') is None else d['max_edges']),
            max_nodes=(None if d.get('max_nodes') is None else d['max_nodes']),
        )


@dataclass
class GraphBatchItemResult:
    """Positional graph batch write result payload."""
    operation: str
    operation_index: int
    created: Optional[bool] = None
    deleted: Optional[bool] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBatchItemResult":
        return cls(
            operation=d['operation'],
            operation_index=d['operation_index'],
            created=(None if d.get('created') is None else d['created']),
            deleted=(None if d.get('deleted') is None else d['deleted']),
        )


@dataclass
class GraphBfsData:
    """Breadth-first-search result (wire form)."""
    depths: _wire.Record
    edges: List["GraphBfsEdgeData"]
    graph: str
    start: str
    truncated: bool
    visited: List[str]

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBfsData":
        return cls(
            depths=d['depths'],
            edges=[GraphBfsEdgeData.from_wire(_x) for _x in (d['edges'] or [])],
            graph=d['graph'],
            start=d['start'],
            truncated=d['truncated'],
            visited=[_x for _x in (d['visited'] or [])],
        )


@dataclass
class GraphBfsEdgeData:
    """One traversal step recorded by a breadth-first search (wire form)."""
    dst: str
    edge_type: str
    src: str
    weight: float

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBfsEdgeData":
        return cls(
            dst=d['dst'],
            edge_type=d['edge_type'],
            src=d['src'],
            weight=d['weight'],
        )


@dataclass
class GraphBindingHit:
    """Serializable graph entity binding hit."""
    binding: "GraphEntityBinding"
    graph: str
    node_id: str
    timestamp: int
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBindingHit":
        return cls(
            binding=GraphEntityBinding.from_wire(d['binding']),
            graph=d['graph'],
            node_id=d['node_id'],
            timestamp=d['timestamp'],
            version=d['version'],
        )


class GraphBindingPrimitive(str, Enum):
    """Product primitive kind used by graph entity bindings."""
    KV = 'kv'
    JSON = 'json'
    VECTOR = 'vector'
    EVENT = 'event'
    GRAPH = 'graph'


@dataclass
class GraphBindingTarget:
    """Typed product identity attached to a graph node."""
    key: str
    primitive: "GraphBindingPrimitive"
    space: str
    branch: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBindingTarget":
        return cls(
            key=d['key'],
            primitive=GraphBindingPrimitive(d['primitive']),
            space=d['space'],
            branch=(None if d.get('branch') is None else d['branch']),
        )


@dataclass
class GraphBulkEdge:
    """One edge in a bulk ingest (input form)."""
    dst: str
    edge_type: str
    src: str
    properties: Optional[Any] = None
    weight: Optional[float] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBulkEdge":
        return cls(
            dst=d['dst'],
            edge_type=d['edge_type'],
            src=d['src'],
            properties=(None if d.get('properties') is None else d['properties']),
            weight=(None if d.get('weight') is None else d['weight']),
        )


@dataclass
class GraphBulkNode:
    """One node in a bulk ingest (input form)."""
    node_id: str
    binding: Optional["GraphEntityBinding"] = None
    object_type: Optional[str] = None
    properties: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphBulkNode":
        return cls(
            node_id=d['node_id'],
            binding=(None if d.get('binding') is None else GraphEntityBinding.from_wire(d['binding'])),
            object_type=(None if d.get('object_type') is None else d['object_type']),
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphCdlpData:
    """Community-detection result (wire form). Every node maps to its"""
    graph: str
    labels: _wire.Record

    @classmethod
    def from_wire(cls, d: dict) -> "GraphCdlpData":
        return cls(
            graph=d['graph'],
            labels=d['labels'],
        )


class GraphDeletePolicy(str, Enum):
    """Explicit policy for graph facts bound to a deleted entity."""
    CASCADE = 'cascade'
    DETACH = 'detach'
    KEEP_DANGLING = 'keep_dangling'


class GraphDirection(str, Enum):
    """Graph neighbor traversal direction."""
    OUTGOING = 'outgoing'
    INCOMING = 'incoming'
    BOTH = 'both'


@dataclass
class GraphEdgeData:
    """Graph edge input payload."""
    properties: Optional[Any] = None
    weight: Optional[float] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphEdgeData":
        return cls(
            properties=(None if d.get('properties') is None else d['properties']),
            weight=(None if d.get('weight') is None else d['weight']),
        )


@dataclass
class GraphEdgeDataOutput:
    """Serializable graph edge output."""
    dst: str
    edge_type: str
    graph: str
    src: str
    timestamp: int
    version: int
    weight: float
    properties: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphEdgeDataOutput":
        return cls(
            dst=d['dst'],
            edge_type=d['edge_type'],
            graph=d['graph'],
            src=d['src'],
            timestamp=d['timestamp'],
            version=d['version'],
            weight=d['weight'],
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphEntityBinding:
    """Node-to-entity binding."""
    target: "GraphBindingTarget"

    @classmethod
    def from_wire(cls, d: dict) -> "GraphEntityBinding":
        return cls(
            target=GraphBindingTarget.from_wire(d['target']),
        )


@dataclass
class GraphInfoData:
    """Serializable graph metadata."""
    created_timestamp: int
    created_version: int
    edge_count: int
    graph: str
    node_count: int
    updated_timestamp: int
    updated_version: int

    @classmethod
    def from_wire(cls, d: dict) -> "GraphInfoData":
        return cls(
            created_timestamp=d['created_timestamp'],
            created_version=d['created_version'],
            edge_count=d['edge_count'],
            graph=d['graph'],
            node_count=d['node_count'],
            updated_timestamp=d['updated_timestamp'],
            updated_version=d['updated_version'],
        )


@dataclass
class GraphLccData:
    """Local-clustering-coefficient result (wire form)."""
    coefficients: _wire.Record
    graph: str

    @classmethod
    def from_wire(cls, d: dict) -> "GraphLccData":
        return cls(
            coefficients=d['coefficients'],
            graph=d['graph'],
        )


@dataclass
class GraphLinkTypeDefData:
    """A declared link type (wire form). `cardinality` is a recorded hint."""
    name: str
    source: str
    target: str
    cardinality: Optional[str] = None
    properties: Optional[_wire.Record] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphLinkTypeDefData":
        return cls(
            name=d['name'],
            source=d['source'],
            target=d['target'],
            cardinality=(None if d.get('cardinality') is None else d['cardinality']),
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphLinkTypeSummaryData:
    """One link type with its visible edge count (wire form)."""
    edge_count: int
    name: str
    source: str
    target: str
    cardinality: Optional[str] = None
    properties: Optional[_wire.Record] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphLinkTypeSummaryData":
        return cls(
            edge_count=d['edge_count'],
            name=d['name'],
            source=d['source'],
            target=d['target'],
            cardinality=(None if d.get('cardinality') is None else d['cardinality']),
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphNeighborHit:
    """Serializable graph neighbor hit."""
    direction: "GraphDirection"
    dst: str
    edge: "GraphEdgeDataOutput"
    edge_type: str
    graph: str
    node: "GraphNodeDataOutput"
    node_id: str
    src: str
    target_status: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphNeighborHit":
        return cls(
            direction=GraphDirection(d['direction']),
            dst=d['dst'],
            edge=GraphEdgeDataOutput.from_wire(d['edge']),
            edge_type=d['edge_type'],
            graph=d['graph'],
            node=GraphNodeDataOutput.from_wire(d['node']),
            node_id=d['node_id'],
            src=d['src'],
            target_status=(None if d.get('target_status') is None else d['target_status']),
        )


@dataclass
class GraphNodeData:
    """Graph node input payload."""
    binding: Optional["GraphEntityBinding"] = None
    object_type: Optional[str] = None
    properties: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphNodeData":
        return cls(
            binding=(None if d.get('binding') is None else GraphEntityBinding.from_wire(d['binding'])),
            object_type=(None if d.get('object_type') is None else d['object_type']),
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphNodeDataOutput:
    """Serializable graph node output."""
    graph: str
    node_id: str
    timestamp: int
    version: int
    binding: Optional["GraphEntityBinding"] = None
    object_type: Optional[str] = None
    properties: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphNodeDataOutput":
        return cls(
            graph=d['graph'],
            node_id=d['node_id'],
            timestamp=d['timestamp'],
            version=d['version'],
            binding=(None if d.get('binding') is None else GraphEntityBinding.from_wire(d['binding'])),
            object_type=(None if d.get('object_type') is None else d['object_type']),
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphObjectTypeDefData:
    """A declared object type (wire form)."""
    name: str
    properties: Optional[_wire.Record] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphObjectTypeDefData":
        return cls(
            name=d['name'],
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphObjectTypeSummaryData:
    """One object type with its visible node count (wire form)."""
    name: str
    node_count: int
    properties: Optional[_wire.Record] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphObjectTypeSummaryData":
        return cls(
            name=d['name'],
            node_count=d['node_count'],
            properties=(None if d.get('properties') is None else d['properties']),
        )


@dataclass
class GraphOntologyData:
    """A graph's ontology: status plus every declared type (wire form)."""
    graph: str
    status: str
    timestamp: int
    version: int
    link_types: Optional[List["GraphLinkTypeDefData"]] = None
    object_types: Optional[List["GraphObjectTypeDefData"]] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphOntologyData":
        return cls(
            graph=d['graph'],
            status=d['status'],
            timestamp=d['timestamp'],
            version=d['version'],
            link_types=(None if d.get('link_types') is None else [GraphLinkTypeDefData.from_wire(_x) for _x in (d['link_types'] or [])]),
            object_types=(None if d.get('object_types') is None else [GraphObjectTypeDefData.from_wire(_x) for _x in (d['object_types'] or [])]),
        )


@dataclass
class GraphOntologySummaryData:
    """The ontology with per-type usage counts (wire form)."""
    graph: str
    status: str
    timestamp: int
    version: int
    link_types: Optional[List["GraphLinkTypeSummaryData"]] = None
    object_types: Optional[List["GraphObjectTypeSummaryData"]] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphOntologySummaryData":
        return cls(
            graph=d['graph'],
            status=d['status'],
            timestamp=d['timestamp'],
            version=d['version'],
            link_types=(None if d.get('link_types') is None else [GraphLinkTypeSummaryData.from_wire(_x) for _x in (d['link_types'] or [])]),
            object_types=(None if d.get('object_types') is None else [GraphObjectTypeSummaryData.from_wire(_x) for _x in (d['object_types'] or [])]),
        )


@dataclass
class GraphPagerankData:
    """`PageRank` result (wire form)."""
    graph: str
    iterations: int
    personalized: bool
    ranks: _wire.Record

    @classmethod
    def from_wire(cls, d: dict) -> "GraphPagerankData":
        return cls(
            graph=d['graph'],
            iterations=d['iterations'],
            personalized=d['personalized'],
            ranks=d['ranks'],
        )


@dataclass
class GraphPropertyDef:
    """One declared property on a graph object or link type (wire form)."""
    required: Optional[bool] = None
    value_type: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "GraphPropertyDef":
        return cls(
            required=(None if d.get('required') is None else d['required']),
            value_type=(None if d.get('value_type') is None else d['value_type']),
        )


@dataclass
class GraphSsspData:
    """Shortest-path result (wire form). Unreachable nodes are omitted."""
    direction: "GraphDirection"
    distances: _wire.Record
    graph: str
    source: str

    @classmethod
    def from_wire(cls, d: dict) -> "GraphSsspData":
        return cls(
            direction=GraphDirection(d['direction']),
            distances=d['distances'],
            graph=d['graph'],
            source=d['source'],
        )


@dataclass
class GraphWccData:
    """Weakly-connected-components result (wire form). Every node maps to"""
    component_count: int
    components: _wire.Record
    graph: str

    @classmethod
    def from_wire(cls, d: dict) -> "GraphWccData":
        return cls(
            component_count=d['component_count'],
            components=d['components'],
            graph=d['graph'],
        )


@dataclass
class HistoryItem:
    """Version-history item."""
    timestamp: int
    tombstone: bool
    version: int
    value: Optional[bytes] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HistoryItem":
        return cls(
            timestamp=d['timestamp'],
            tombstone=d['tombstone'],
            version=d['version'],
            value=(None if d.get('value') is None else _wire.b64d(d['value'])),
        )


@dataclass
class HistoryResult:
    """Version-history result for one key."""
    items: List["HistoryItem"]

    @classmethod
    def from_wire(cls, d: dict) -> "HistoryResult":
        return cls(
            items=[HistoryItem.from_wire(_x) for _x in (d['items'] or [])],
        )


@dataclass
class HubBranchHighlight:
    """One branch highlight on a hub dataset card."""
    is_default: bool
    name: str

    @classmethod
    def from_wire(cls, d: dict) -> "HubBranchHighlight":
        return cls(
            is_default=d['is_default'],
            name=d['name'],
        )


@dataclass
class HubCloneProgress:
    """Machine-readable clone progress emitted by `strata clone --progress jsonl`."""
    dataset: str
    stage: "HubCloneProgressStage"
    branch: Optional[str] = None
    bytes: Optional[int] = None
    index: Optional[int] = None
    manifest_hash: Optional[str] = None
    object_count: Optional[int] = None
    total_bytes: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HubCloneProgress":
        return cls(
            dataset=d['dataset'],
            stage=HubCloneProgressStage(d['stage']),
            branch=(None if d.get('branch') is None else d['branch']),
            bytes=(None if d.get('bytes') is None else d['bytes']),
            index=(None if d.get('index') is None else d['index']),
            manifest_hash=(None if d.get('manifest_hash') is None else d['manifest_hash']),
            object_count=(None if d.get('object_count') is None else d['object_count']),
            total_bytes=(None if d.get('total_bytes') is None else d['total_bytes']),
        )


class HubCloneProgressStage(str, Enum):
    """Clone progress stage."""
    RESOLVED = 'resolved'
    MANIFEST_FETCHED = 'manifest_fetched'
    OBJECT_FETCHED = 'object_fetched'
    IMPORTING = 'importing'
    DONE = 'done'
    UNKNOWN = 'unknown'


@dataclass
class HubDatasetCard:
    """Full dataset card returned by `hub.get_dataset`."""
    capability_registry_version: int
    clone_command: str
    created: str
    default_branch: str
    description: str
    downloads: int
    engine_version_required: str
    format_version: str
    last_updated: str
    license: str
    manifest_hash: str
    name: str
    owner: str
    primitives: List[str]
    readme: str
    size_bytes: int
    summary_excerpt: str
    tags: List[str]
    tasks: List[str]
    badge: Optional[str] = None
    citation: Optional[str] = None
    frontmatter_extras: Optional[_wire.Record] = None
    provenance: Optional["HubProvenance"] = None
    quick_start_snippets: Optional[_wire.Record] = None
    sample_preview: Optional[Any] = None
    schema: Optional[Any] = None
    strata_features: Optional["HubStrataFeatures"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HubDatasetCard":
        return cls(
            capability_registry_version=d['capability_registry_version'],
            clone_command=d['clone_command'],
            created=d['created'],
            default_branch=d['default_branch'],
            description=d['description'],
            downloads=d['downloads'],
            engine_version_required=d['engine_version_required'],
            format_version=d['format_version'],
            last_updated=d['last_updated'],
            license=d['license'],
            manifest_hash=d['manifest_hash'],
            name=d['name'],
            owner=d['owner'],
            primitives=[_x for _x in (d['primitives'] or [])],
            readme=d['readme'],
            size_bytes=d['size_bytes'],
            summary_excerpt=d['summary_excerpt'],
            tags=[_x for _x in (d['tags'] or [])],
            tasks=[_x for _x in (d['tasks'] or [])],
            badge=(None if d.get('badge') is None else d['badge']),
            citation=(None if d.get('citation') is None else d['citation']),
            frontmatter_extras=(None if d.get('frontmatter_extras') is None else d['frontmatter_extras']),
            provenance=(None if d.get('provenance') is None else HubProvenance.from_wire(d['provenance'])),
            quick_start_snippets=(None if d.get('quick_start_snippets') is None else d['quick_start_snippets']),
            sample_preview=(None if d.get('sample_preview') is None else d['sample_preview']),
            schema=(None if d.get('schema') is None else d['schema']),
            strata_features=(None if d.get('strata_features') is None else HubStrataFeatures.from_wire(d['strata_features'])),
        )


@dataclass
class HubDatasetPage:
    """Paginated dataset-list output returned by `hub.list_datasets`."""
    items: List["HubDatasetSummary"]
    limit: int
    offset: int
    total: int

    @classmethod
    def from_wire(cls, d: dict) -> "HubDatasetPage":
        return cls(
            items=[HubDatasetSummary.from_wire(_x) for _x in (d['items'] or [])],
            limit=d['limit'],
            offset=d['offset'],
            total=d['total'],
        )


class HubDatasetSort(str, Enum):
    """Dataset-list sort key accepted by StrataHub V1."""
    DOWNLOADS = 'downloads'
    RECENT = 'recent'
    NAME = 'name'
    SIZE = 'size'


@dataclass
class HubDatasetSummary:
    """One dataset summary returned by `hub.list_datasets`."""
    default_branch: str
    description: str
    downloads: int
    last_updated: str
    license: str
    name: str
    primitives: List[str]
    size_bytes: int
    tags: List[str]
    tasks: List[str]
    badge: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HubDatasetSummary":
        return cls(
            default_branch=d['default_branch'],
            description=d['description'],
            downloads=d['downloads'],
            last_updated=d['last_updated'],
            license=d['license'],
            name=d['name'],
            primitives=[_x for _x in (d['primitives'] or [])],
            size_bytes=d['size_bytes'],
            tags=[_x for _x in (d['tags'] or [])],
            tasks=[_x for _x in (d['tasks'] or [])],
            badge=(None if d.get('badge') is None else d['badge']),
        )


@dataclass
class HubInfo:
    """Hub capability advertisement returned by `hub.info`."""
    hash_algorithm: str
    max_dataset_size_bytes: int
    max_manifest_size_bytes: int
    max_object_size_bytes: int
    protocol_version: str
    server_implementation: str
    server_version: str
    supported_object_content_types: List[str]
    telemetry_endpoint_enabled: bool

    @classmethod
    def from_wire(cls, d: dict) -> "HubInfo":
        return cls(
            hash_algorithm=d['hash_algorithm'],
            max_dataset_size_bytes=d['max_dataset_size_bytes'],
            max_manifest_size_bytes=d['max_manifest_size_bytes'],
            max_object_size_bytes=d['max_object_size_bytes'],
            protocol_version=d['protocol_version'],
            server_implementation=d['server_implementation'],
            server_version=d['server_version'],
            supported_object_content_types=[_x for _x in (d['supported_object_content_types'] or [])],
            telemetry_endpoint_enabled=d['telemetry_endpoint_enabled'],
        )


@dataclass
class HubProvenance:
    """Dataset provenance metadata on a hub dataset card."""
    curator: str
    source: str
    license_text_url: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HubProvenance":
        return cls(
            curator=d['curator'],
            source=d['source'],
            license_text_url=(None if d.get('license_text_url') is None else d['license_text_url']),
        )


@dataclass
class HubRefEntry:
    """One live hub ref."""
    branch: str
    last_updated: str
    manifest_hash: str

    @classmethod
    def from_wire(cls, d: dict) -> "HubRefEntry":
        return cls(
            branch=d['branch'],
            last_updated=d['last_updated'],
            manifest_hash=d['manifest_hash'],
        )


@dataclass
class HubRefList:
    """Ref listing returned by `hub.list_refs`."""
    dataset: str
    default_branch: str
    refs: List["HubRefEntry"]

    @classmethod
    def from_wire(cls, d: dict) -> "HubRefList":
        return cls(
            dataset=d['dataset'],
            default_branch=d['default_branch'],
            refs=[HubRefEntry.from_wire(_x) for _x in (d['refs'] or [])],
        )


@dataclass
class HubStrataFeatures:
    """Strata-specific feature highlights on a hub dataset card."""
    branches: List["HubBranchHighlight"]
    multi_primitive_demos: List[str]
    time_travel_highlights: List[str]
    example_notebook: Optional[str] = None

    @classmethod
    def from_wire(cls, d: dict) -> "HubStrataFeatures":
        return cls(
            branches=[HubBranchHighlight.from_wire(_x) for _x in (d['branches'] or [])],
            multi_primitive_demos=[_x for _x in (d['multi_primitive_demos'] or [])],
            time_travel_highlights=[_x for _x in (d['time_travel_highlights'] or [])],
            example_notebook=(None if d.get('example_notebook') is None else d['example_notebook']),
        )


@dataclass
class HubYankedEntry:
    """One yanked hub ref."""
    branch: str
    dataset: str
    manifest_hash: str
    reason: str
    yanked_at: str

    @classmethod
    def from_wire(cls, d: dict) -> "HubYankedEntry":
        return cls(
            branch=d['branch'],
            dataset=d['dataset'],
            manifest_hash=d['manifest_hash'],
            reason=d['reason'],
            yanked_at=d['yanked_at'],
        )


@dataclass
class HubYankedList:
    """Hub yank deny-list returned by `hub.list_yanked`."""
    generated_at: str
    items: List["HubYankedEntry"]
    total: int

    @classmethod
    def from_wire(cls, d: dict) -> "HubYankedList":
        return cls(
            generated_at=d['generated_at'],
            items=[HubYankedEntry.from_wire(_x) for _x in (d['items'] or [])],
            total=d['total'],
        )


@dataclass
class JsonBatchGetItemResult:
    """Positional JSON batch read result payload."""
    found: bool
    value: Any
    document_version: Optional[int] = None
    timestamp: Optional[int] = None
    version: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "JsonBatchGetItemResult":
        return cls(
            found=d['found'],
            value=d['value'],
            document_version=(None if d.get('document_version') is None else d['document_version']),
            timestamp=(None if d.get('timestamp') is None else d['timestamp']),
            version=(None if d.get('version') is None else d['version']),
        )


@dataclass
class JsonBatchItemResult:
    """Positional JSON batch write/delete result payload."""
    document_version: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "JsonBatchItemResult":
        return cls(
            document_version=(None if d.get('document_version') is None else d['document_version']),
        )


@dataclass
class JsonHistoryItem:
    """JSON version-history item."""
    timestamp: int
    tombstone: bool
    version: int
    document_version: Optional[int] = None
    value: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "JsonHistoryItem":
        return cls(
            timestamp=d['timestamp'],
            tombstone=d['tombstone'],
            version=d['version'],
            document_version=(None if d.get('document_version') is None else d['document_version']),
            value=(None if d.get('value') is None else d['value']),
        )


@dataclass
class JsonIndexDefinition:
    """JSON secondary index definition exposed through the command boundary."""
    created_timestamp: int
    created_version: int
    field_path: str
    index_type: "JsonIndexType"
    name: str
    space: str

    @classmethod
    def from_wire(cls, d: dict) -> "JsonIndexDefinition":
        return cls(
            created_timestamp=d['created_timestamp'],
            created_version=d['created_version'],
            field_path=d['field_path'],
            index_type=JsonIndexType(d['index_type']),
            name=d['name'],
            space=d['space'],
        )


class JsonIndexType(str, Enum):
    """JSON secondary index kind exposed through the command boundary."""
    NUMERIC = 'numeric'
    TAG = 'tag'
    TEXT = 'text'


@dataclass
class JsonSampleItem:
    """Sampled JSON document."""
    document_version: int
    key: str
    timestamp: int
    value: Any
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "JsonSampleItem":
        return cls(
            document_version=d['document_version'],
            key=d['key'],
            timestamp=d['timestamp'],
            value=d['value'],
            version=d['version'],
        )


@dataclass
class JsonVersionedValue:
    """Stored JSON value with commit metadata."""
    document_version: int
    timestamp: int
    value: Any
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "JsonVersionedValue":
        return cls(
            document_version=d['document_version'],
            timestamp=d['timestamp'],
            value=d['value'],
            version=d['version'],
        )


@dataclass
class Maybe:
    """Point-read envelope shared by every capability's single-record `get`."""
    found: bool
    value: Optional["VersionedValue"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "Maybe":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else VersionedValue.from_wire(d['value'])),
        )


@dataclass
class Maybe2:
    """Point-read envelope shared by every capability's single-record `get`."""
    found: bool
    value: Optional["VectorVersionedData"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "Maybe2":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else VectorVersionedData.from_wire(d['value'])),
        )


@dataclass
class Maybe3:
    """Point-read envelope shared by every capability's single-record `get`."""
    found: bool
    value: Optional["EventVersionedData"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "Maybe3":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else EventVersionedData.from_wire(d['value'])),
        )


@dataclass
class Maybe4:
    """Point-read envelope shared by every capability's single-record `get`."""
    found: bool
    value: Optional["GraphNodeDataOutput"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "Maybe4":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else GraphNodeDataOutput.from_wire(d['value'])),
        )


@dataclass
class Maybe5:
    """Point-read envelope shared by every capability's single-record `get`."""
    found: bool
    value: Optional["GraphEdgeDataOutput"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "Maybe5":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else GraphEdgeDataOutput.from_wire(d['value'])),
        )


@dataclass
class MaybeJsonValue:
    """JSON point-read result that distinguishes absence from a stored JSON null."""
    found: bool
    value: Any

    @classmethod
    def from_wire(cls, d: dict) -> "MaybeJsonValue":
        return cls(
            found=d['found'],
            value=d['value'],
        )


@dataclass
class MaybeJsonVersionedValue:
    """JSON versioned point-read result that distinguishes absence from a stored JSON null."""
    found: bool
    value: Optional["JsonVersionedValue"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "MaybeJsonVersionedValue":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else JsonVersionedValue.from_wire(d['value'])),
        )


@dataclass
class MutationEffect:
    """Normalized mutation effect facts."""
    affected_count: int
    applied: bool
    kind: "MutationEffectKind"
    matched: bool

    @classmethod
    def from_wire(cls, d: dict) -> "MutationEffect":
        return cls(
            affected_count=d['affected_count'],
            applied=d['applied'],
            kind=MutationEffectKind(d['kind']),
            matched=d['matched'],
        )


class MutationEffectKind(str, Enum):
    """High-level mutation effect for idempotent and conditional operations."""
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'
    UNCHANGED = 'unchanged'
    NOT_FOUND = 'not_found'


@dataclass
class PreviewConflictItem:
    """One conflicting entity a promotion encountered, exposed through the command"""
    capability: "ComparedCapability"
    identity: bytes
    kind: "ConflictKind"
    space: str
    strategy_result: "ConflictStrategyResult"
    source_value: Optional[bytes] = None
    target_value: Optional[bytes] = None

    @classmethod
    def from_wire(cls, d: dict) -> "PreviewConflictItem":
        return cls(
            capability=ComparedCapability(d['capability']),
            identity=_wire.b64d(d['identity']),
            kind=ConflictKind(d['kind']),
            space=d['space'],
            strategy_result=ConflictStrategyResult(d['strategy_result']),
            source_value=(None if d.get('source_value') is None else _wire.b64d(d['source_value'])),
            target_value=(None if d.get('target_value') is None else _wire.b64d(d['target_value'])),
        )


@dataclass
class PromotedEntityItem:
    """One entity a promotion applied to the target branch, exposed through the"""
    capability: "ComparedCapability"
    identity: bytes
    space: str
    value: Optional[bytes] = None

    @classmethod
    def from_wire(cls, d: dict) -> "PromotedEntityItem":
        return cls(
            capability=ComparedCapability(d['capability']),
            identity=_wire.b64d(d['identity']),
            space=d['space'],
            value=(None if d.get('value') is None else _wire.b64d(d['value'])),
        )


@dataclass
class PromotionOutcomeItem:
    """The result of promoting one branch into another, exposed through the command"""
    applied: List["PromotedEntityItem"]
    branch_point: int
    conflicts: List["PreviewConflictItem"]
    deleted: List["PromotedEntityItem"]
    source: str
    strategy: "PromotionStrategy"
    target: str
    capabilities_covered: Optional[List["ComparedCapability"]] = None
    capabilities_unsupported: Optional[List["ComparedCapability"]] = None
    derived_state: Optional[List["DerivedStateReportItem"]] = None
    spaces_covered: Optional[List[str]] = None
    target_timestamp: Optional[int] = None
    target_version: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "PromotionOutcomeItem":
        return cls(
            applied=[PromotedEntityItem.from_wire(_x) for _x in (d['applied'] or [])],
            branch_point=d['branch_point'],
            conflicts=[PreviewConflictItem.from_wire(_x) for _x in (d['conflicts'] or [])],
            deleted=[PromotedEntityItem.from_wire(_x) for _x in (d['deleted'] or [])],
            source=d['source'],
            strategy=PromotionStrategy(d['strategy']),
            target=d['target'],
            capabilities_covered=(None if d.get('capabilities_covered') is None else [ComparedCapability(_x) for _x in (d['capabilities_covered'] or [])]),
            capabilities_unsupported=(None if d.get('capabilities_unsupported') is None else [ComparedCapability(_x) for _x in (d['capabilities_unsupported'] or [])]),
            derived_state=(None if d.get('derived_state') is None else [DerivedStateReportItem.from_wire(_x) for _x in (d['derived_state'] or [])]),
            spaces_covered=(None if d.get('spaces_covered') is None else [_x for _x in (d['spaces_covered'] or [])]),
            target_timestamp=(None if d.get('target_timestamp') is None else d['target_timestamp']),
            target_version=(None if d.get('target_version') is None else d['target_version']),
        )


class PromotionStrategy(str, Enum):
    """The conflict-resolution strategy for a promotion, exposed through the command"""
    STRICT = 'strict'
    SOURCE_WINS = 'source_wins'


@dataclass
class RemoteOriginFrontierInfo:
    """One fetched branch in the recorded base frontier."""
    base: str
    branch: str
    local_version: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "RemoteOriginFrontierInfo":
        return cls(
            base=d['base'],
            branch=d['branch'],
            local_version=(None if d.get('local_version') is None else d['local_version']),
        )


@dataclass
class RemoteOriginInfo:
    """Serialized view of a database's recorded remote origin."""
    base_frontier: List["RemoteOriginFrontierInfo"]
    branch: str
    dataset: str
    fetched_at_micros: int
    manifest_hash: str
    remote_url: str

    @classmethod
    def from_wire(cls, d: dict) -> "RemoteOriginInfo":
        return cls(
            base_frontier=[RemoteOriginFrontierInfo.from_wire(_x) for _x in (d['base_frontier'] or [])],
            branch=d['branch'],
            dataset=d['dataset'],
            fetched_at_micros=d['fetched_at_micros'],
            manifest_hash=d['manifest_hash'],
            remote_url=d['remote_url'],
        )


class RetryPolicy(str, Enum):
    """V1 retry policy."""
    NEVER = 'never'
    AFTER_STATE_CHANGE = 'after_state_change'
    SAME_REQUEST = 'same_request'
    IDEMPOTENT_ONLY = 'idempotent_only'
    UNKNOWN = 'unknown'


@dataclass
class SampleItem:
    """Sampled KV item."""
    key: bytes
    timestamp: int
    value: bytes
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "SampleItem":
        return cls(
            key=_wire.b64d(d['key']),
            timestamp=d['timestamp'],
            value=_wire.b64d(d['value']),
            version=d['version'],
        )


@dataclass
class ScanItem:
    """KV scan item."""
    key: bytes
    timestamp: int
    value: bytes
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "ScanItem":
        return cls(
            key=_wire.b64d(d['key']),
            timestamp=d['timestamp'],
            value=_wire.b64d(d['value']),
            version=d['version'],
        )


class SessionAccess(str, Enum):
    """The access a session declares at hello. The owner's dispatch gate rejects"""
    READ = 'read'
    READ_WRITE = 'read_write'


@dataclass
class SpaceComparisonItem:
    """The differing entities for one capability within one space. `added` are"""
    added: List["ComparedEntityItem"]
    capability: "ComparedCapability"
    modified: List["ComparedEntityItem"]
    removed: List["ComparedEntityItem"]
    space: str

    @classmethod
    def from_wire(cls, d: dict) -> "SpaceComparisonItem":
        return cls(
            added=[ComparedEntityItem.from_wire(_x) for _x in (d['added'] or [])],
            capability=ComparedCapability(d['capability']),
            modified=[ComparedEntityItem.from_wire(_x) for _x in (d['modified'] or [])],
            removed=[ComparedEntityItem.from_wire(_x) for _x in (d['removed'] or [])],
            space=d['space'],
        )


@dataclass
class VectorBatchGetItemResult:
    """Positional vector batch read result payload."""
    found: bool
    value: Optional["VectorVersionedData"] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorBatchGetItemResult":
        return cls(
            found=d['found'],
            value=(None if d.get('value') is None else VectorVersionedData.from_wire(d['value'])),
        )


@dataclass
class VectorBatchItemResult:
    """Positional vector batch write/delete result payload."""
    vector_revision: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorBatchItemResult":
        return cls(
            vector_revision=(None if d.get('vector_revision') is None else d['vector_revision']),
        )


@dataclass
class VectorCollectionInfo:
    """Vector collection facts."""
    count: int
    dimension: int
    metric: "VectorDistanceMetric"
    name: str

    @classmethod
    def from_wire(cls, d: dict) -> "VectorCollectionInfo":
        return cls(
            count=d['count'],
            dimension=d['dimension'],
            metric=VectorDistanceMetric(d['metric']),
            name=d['name'],
        )


@dataclass
class VectorData:
    """Vector value payload."""
    embedding: List[float]
    metadata: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorData":
        return cls(
            embedding=[_x for _x in (d['embedding'] or [])],
            metadata=(None if d.get('metadata') is None else d['metadata']),
        )


class VectorDistanceMetric(str, Enum):
    """Vector distance metric exposed through the command boundary."""
    COSINE = 'cosine'
    EUCLIDEAN = 'euclidean'
    DOT_PRODUCT = 'dot_product'


class VectorFilterOp(str, Enum):
    """Vector metadata filter operation."""
    EQ = 'eq'


@dataclass
class VectorHistoryItem:
    """Vector history item."""
    key: str
    timestamp: int
    tombstone: bool
    version: int
    data: Optional["VectorData"] = None
    vector_revision: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorHistoryItem":
        return cls(
            key=d['key'],
            timestamp=d['timestamp'],
            tombstone=d['tombstone'],
            version=d['version'],
            data=(None if d.get('data') is None else VectorData.from_wire(d['data'])),
            vector_revision=(None if d.get('vector_revision') is None else d['vector_revision']),
        )


@dataclass
class VectorHistoryResult:
    """Vector history result for one key."""
    items: List["VectorHistoryItem"]

    @classmethod
    def from_wire(cls, d: dict) -> "VectorHistoryResult":
        return cls(
            items=[VectorHistoryItem.from_wire(_x) for _x in (d['items'] or [])],
        )


@dataclass
class VectorIndexArtifactSource:
    """One vector index artifact diagnostic."""
    artifact_id: str
    searched: bool
    status: str

    @classmethod
    def from_wire(cls, d: dict) -> "VectorIndexArtifactSource":
        return cls(
            artifact_id=d['artifact_id'],
            searched=d['searched'],
            status=d['status'],
        )


@dataclass
class VectorIndexDiagnostics:
    """Vector index planner diagnostics."""
    active_delta_count: int
    active_delta_seal_threshold: int
    active_delta_source_count: int
    artifact_sources: List["VectorIndexArtifactSource"]
    collection: str
    collection_exact_threshold: int
    derived_bytes: int
    exact_fallback_count: int
    exact_source_count: int
    filtered_underfill_fallback: bool
    flat_source_count: int
    hnsw_graph_builds: int
    hnsw_memory_budget_bytes: int
    hnsw_source_count: int
    indexed_source_count: int
    indexed_vector_count: int
    last_query_used_index: bool
    manifest_inherited_ref_count: int
    manifest_owned_ref_count: int
    manifest_ref_count: int
    manifest_status: str
    overfetch_factor: int
    policy_mode: str
    resolved_index_kind_summary: str
    source_candidate_limit: int
    source_flat_threshold: int
    source_hnsw_threshold: int
    last_query_fallback_reason: Optional[str] = None
    manifest_generation: Optional[int] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorIndexDiagnostics":
        return cls(
            active_delta_count=d['active_delta_count'],
            active_delta_seal_threshold=d['active_delta_seal_threshold'],
            active_delta_source_count=d['active_delta_source_count'],
            artifact_sources=[VectorIndexArtifactSource.from_wire(_x) for _x in (d['artifact_sources'] or [])],
            collection=d['collection'],
            collection_exact_threshold=d['collection_exact_threshold'],
            derived_bytes=d['derived_bytes'],
            exact_fallback_count=d['exact_fallback_count'],
            exact_source_count=d['exact_source_count'],
            filtered_underfill_fallback=d['filtered_underfill_fallback'],
            flat_source_count=d['flat_source_count'],
            hnsw_graph_builds=d['hnsw_graph_builds'],
            hnsw_memory_budget_bytes=d['hnsw_memory_budget_bytes'],
            hnsw_source_count=d['hnsw_source_count'],
            indexed_source_count=d['indexed_source_count'],
            indexed_vector_count=d['indexed_vector_count'],
            last_query_used_index=d['last_query_used_index'],
            manifest_inherited_ref_count=d['manifest_inherited_ref_count'],
            manifest_owned_ref_count=d['manifest_owned_ref_count'],
            manifest_ref_count=d['manifest_ref_count'],
            manifest_status=d['manifest_status'],
            overfetch_factor=d['overfetch_factor'],
            policy_mode=d['policy_mode'],
            resolved_index_kind_summary=d['resolved_index_kind_summary'],
            source_candidate_limit=d['source_candidate_limit'],
            source_flat_threshold=d['source_flat_threshold'],
            source_hnsw_threshold=d['source_hnsw_threshold'],
            last_query_fallback_reason=(None if d.get('last_query_fallback_reason') is None else d['last_query_fallback_reason']),
            manifest_generation=(None if d.get('manifest_generation') is None else d['manifest_generation']),
        )


@dataclass
class VectorIndexQueryResult:
    """Vector index search output."""
    diagnostics: "VectorIndexDiagnostics"
    matches: List["VectorMatch"]

    @classmethod
    def from_wire(cls, d: dict) -> "VectorIndexQueryResult":
        return cls(
            diagnostics=VectorIndexDiagnostics.from_wire(d['diagnostics']),
            matches=[VectorMatch.from_wire(_x) for _x in (d['matches'] or [])],
        )


@dataclass
class VectorMatch:
    """One vector search match."""
    key: str
    score: float
    metadata: Optional[Any] = None

    @classmethod
    def from_wire(cls, d: dict) -> "VectorMatch":
        return cls(
            key=d['key'],
            score=d['score'],
            metadata=(None if d.get('metadata') is None else d['metadata']),
        )


@dataclass
class VectorVersionedData:
    """Vector value with commit metadata."""
    data: "VectorData"
    key: str
    timestamp: int
    vector_revision: int
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "VectorVersionedData":
        return cls(
            data=VectorData.from_wire(d['data']),
            key=d['key'],
            timestamp=d['timestamp'],
            vector_revision=d['vector_revision'],
            version=d['version'],
        )


@dataclass
class VersionedValue:
    """Stored value with commit metadata."""
    timestamp: int
    value: bytes
    version: int

    @classmethod
    def from_wire(cls, d: dict) -> "VersionedValue":
        return cls(
            timestamp=d['timestamp'],
            value=_wire.b64d(d['value']),
            version=d['version'],
        )
