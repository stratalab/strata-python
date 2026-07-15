"""Generated from the Strata IDL — do not edit by hand.

Regenerate with ``python tools/generate.py``. The CI drift guard fails if this
file is stale.
"""

from __future__ import annotations

from typing import Any

from .. import _wire
from . import models


class Commands:
    """One typed method per data-plane command, over the core wire."""

    __slots__ = ("_core",)

    def __init__(self, core: Any):
        self._core = core

    def admin_config(self):
        """Read sanitized configuration facts.

        Errors: failed_precondition.engine.runtime_closed
        """
        cmd = {'type': 'config_get'}
        data = self._core.data(cmd)
        return models.AdminConfig.from_wire(data)

    def admin_config_key(self, key):
        """Read one sanitized configuration value by key.

        Errors: failed_precondition.engine.runtime_closed, invalid_argument.engine.config_key
        """
        cmd = {'type': 'configure_get_key'}
        cmd['key'] = key
        data = self._core.data(cmd)
        return (None if data is None else data)

    def admin_describe(self, *, branch=None):
        """Read a compact description of the database.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name
        """
        cmd = {'type': 'describe'}
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.AdminDescribe.from_wire(data)

    def admin_health(self, *, branch=None):
        """Read control-plane health facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name
        """
        cmd = {'type': 'health'}
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.AdminHealth.from_wire(data)

    def admin_info(self, *, branch=None):
        """Read database identity and a catalog summary.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name
        """
        cmd = {'type': 'info'}
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.AdminDatabaseInfo.from_wire(data)

    def admin_metrics(self, *, branch=None):
        """Read lightweight database metrics.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name
        """
        cmd = {'type': 'metrics'}
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.AdminMetrics.from_wire(data)

    def admin_ping(self):
        """Check that the database handle is live.

        Errors: failed_precondition.engine.runtime_closed
        """
        cmd = {'type': 'ping'}
        data = self._core.data(cmd)
        return _wire.Record({'version': data['version']})

    def arrow_export(self, primitive, format, path, *, collection=None, event_type=None, graph=None, limit=None, prefix=None, branch=None, space=None):
        """Export a product primitive to an Arrow-compatible file.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.executor.arrow_feature_disabled, invalid_argument.executor.arrow_format, invalid_argument.executor.arrow_empty_export, invalid_argument.executor.arrow_value_column, invalid_argument.executor.arrow_vector_key, invalid_argument.executor.arrow_graph, invalid_argument.executor.arrow_collection, unavailable.executor.arrow_io, internal.executor.arrow
        """
        cmd = {'type': 'arrow_export'}
        cmd['primitive'] = primitive
        cmd['format'] = format
        cmd['path'] = path
        if collection is not None:
            cmd['collection'] = collection
        if event_type is not None:
            cmd['event_type'] = event_type
        if graph is not None:
            cmd['graph'] = graph
        if limit is not None:
            cmd['limit'] = limit
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.ArrowExportResult.from_wire(data)

    def arrow_import(self, file_path, target, *, collection=None, format=None, key_column=None, value_column=None, branch=None, space=None):
        """Import an Arrow-compatible file into a product primitive.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.executor.arrow_feature_disabled, invalid_argument.executor.arrow_format, invalid_argument.executor.arrow_input_missing, invalid_argument.executor.arrow_key_column, invalid_argument.executor.arrow_value_column, invalid_argument.executor.arrow_collection, invalid_argument.executor.arrow_embedding_type, invalid_argument.executor.arrow_vector_dimension, invalid_argument.executor.arrow_json_key, invalid_argument.executor.arrow_base64, unavailable.executor.arrow_io, internal.executor.arrow
        """
        cmd = {'type': 'arrow_import'}
        cmd['file_path'] = file_path
        cmd['target'] = target
        if collection is not None:
            cmd['collection'] = collection
        if format is not None:
            cmd['format'] = format
        if key_column is not None:
            cmd['key_column'] = key_column
        if value_column is not None:
            cmd['value_column'] = value_column
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.ArrowImportResult.from_wire(data)

    def branch_create(self, branch):
        """Create a new empty root branch.

        Errors: failed_precondition.engine.runtime_closed, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved, already_exists.engine.branch
        """
        cmd = {'type': 'branch_create'}
        cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.BranchItem.from_wire(data)

    def branch_delete(self, branch):
        """Delete an active branch and release its storage claims.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved, invalid_argument.engine.branch_delete
        """
        cmd = {'type': 'branch_delete'}
        cmd['branch'] = branch
        data = self._core.data(cmd)
        return _wire.Record({'branch': models.BranchItem.from_wire(data['branch']), 'cleanup': (None if data.get('cleanup') is None else models.BranchCleanupItem.from_wire(data['cleanup'])), 'deleted': data['deleted'], 'effect': models.MutationEffect.from_wire(data['effect']), 'generation_after': (None if data.get('generation_after') is None else data['generation_after']), 'generation_before': (None if data.get('generation_before') is None else data['generation_before'])})

    def branch_fork(self, source, branch):
        """Fork a new branch from the current head of a source branch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved, already_exists.engine.branch
        """
        cmd = {'type': 'branch_fork_current'}
        cmd['source'] = source
        cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.BranchItem.from_wire(data)

    def branch_fork_at_timestamp(self, source, branch, timestamp):
        """Fork a new branch from a retained source timestamp.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved, already_exists.engine.branch, history_unavailable.engine.persistence_history
        """
        cmd = {'type': 'branch_fork_at_timestamp'}
        cmd['source'] = source
        cmd['branch'] = branch
        cmd['timestamp'] = timestamp
        data = self._core.data(cmd)
        return models.BranchItem.from_wire(data)

    def branch_fork_at_version(self, source, branch, version):
        """Fork a new branch from a retained source commit version.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved, already_exists.engine.branch, history_unavailable.engine.persistence_history
        """
        cmd = {'type': 'branch_fork_at_version'}
        cmd['source'] = source
        cmd['branch'] = branch
        cmd['version'] = version
        data = self._core.data(cmd)
        return models.BranchItem.from_wire(data)

    def branch_get(self, branch):
        """Read one branch summary by name.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.branch_name, invalid_argument.engine.branch_name_reserved
        """
        cmd = {'type': 'branch_get'}
        cmd['branch'] = branch
        data = self._core.data(cmd)
        return models.BranchItem.from_wire(data)

    def branch_list(self):
        """List active branches with their lineage facts.

        Errors: failed_precondition.engine.runtime_closed
        """
        cmd = {'type': 'branch_list'}
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.BranchItem.from_wire(_x) for _x in (data['items'] or [])]})

    def event_append(self, event_type, payload, *, branch=None, space=None):
        """Append one event to the branch event log.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.event_type, invalid_argument.engine.event_payload, invalid_argument.engine.event_payload_too_large
        """
        cmd = {'type': 'event_append'}
        cmd['event_type'] = event_type
        cmd['payload'] = payload
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'event_type': data['event_type'], 'sequence': data['sequence']})

    def event_batch_append(self, entries, *, branch=None, space=None):
        """Append multiple events in one commit.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.event_batch, invalid_argument.engine.event_type, invalid_argument.engine.event_payload, invalid_argument.engine.event_payload_too_large
        """
        cmd = {'type': 'event_batch_append'}
        cmd['entries'] = [{'event_type': _x['event_type'], 'payload': _x['payload']} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult9.from_wire(data)

    def event_count(self, *, as_of=None, branch=None, space=None):
        """Count visible events in the log.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'event_count'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'count': data['count']})

    def event_exists(self, sequence, *, branch=None, space=None):
        """Check whether an event sequence exists.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'event_exists'}
        cmd['sequence'] = sequence
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def event_get(self, sequence, *, as_of=None, branch=None, space=None):
        """Read one event by sequence number.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'event_get'}
        cmd['sequence'] = sequence
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.Maybe3.from_wire(data)

    def event_list(self, *, after_sequence=None, as_of=None, event_type=None, limit=None, branch=None, space=None):
        """List events with optional type filter and cursor.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.event_type, invalid_argument.executor.limit
        """
        cmd = {'type': 'event_list'}
        if after_sequence is not None:
            cmd['after_sequence'] = after_sequence
        if as_of is not None:
            cmd['as_of'] = as_of
        if event_type is not None:
            cmd['event_type'] = event_type
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.EventVersionedData.from_wire(_x) for _x in (data['items'] or [])]})

    def event_range(self, start_seq, direction, *, end_seq=None, event_type=None, limit=None, branch=None, space=None):
        """Read a range of events by sequence number.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.event_type, invalid_argument.executor.limit
        """
        cmd = {'type': 'event_range'}
        cmd['start_seq'] = start_seq
        cmd['direction'] = direction
        if end_seq is not None:
            cmd['end_seq'] = end_seq
        if event_type is not None:
            cmd['event_type'] = event_type
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.EventVersionedData.from_wire(_x) for _x in (data['items'] or [])]})

    def event_range_time(self, start_ts, direction, *, end_ts=None, event_type=None, limit=None, branch=None, space=None):
        """Read a range of events by occurrence time.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.event_type, invalid_argument.executor.limit
        """
        cmd = {'type': 'event_range_by_time'}
        cmd['start_ts'] = start_ts
        cmd['direction'] = direction
        if end_ts is not None:
            cmd['end_ts'] = end_ts
        if event_type is not None:
            cmd['event_type'] = event_type
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.EventVersionedData.from_wire(_x) for _x in (data['items'] or [])]})

    def event_types(self, *, as_of=None, branch=None, space=None):
        """List distinct event types in the log.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'event_list_types'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [_x for _x in (data['items'] or [])]})

    def event_verify_chain(self, *, branch=None, space=None):
        """Verify event log density and hash linkage.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'event_verify_chain'}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.EventChainVerification.from_wire(data)

    def graph_analytics_bfs(self, graph, start, *, as_of=None, budget=None, direction=None, edge_types=None, max_depth=None, max_nodes=None, branch=None, space=None):
        """Run a bounded breadth-first traversal.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type, not_found.engine.graph_node, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_bfs'}
        cmd['graph'] = graph
        cmd['start'] = start
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if direction is not None:
            cmd['direction'] = direction
        if edge_types is not None:
            cmd['edge_types'] = [_x for _x in (edge_types or [])]
        if max_depth is not None:
            cmd['max_depth'] = max_depth
        if max_nodes is not None:
            cmd['max_nodes'] = max_nodes
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphBfsData.from_wire(data)

    def graph_analytics_cdlp(self, graph, *, as_of=None, budget=None, direction=None, max_iterations=None, branch=None, space=None):
        """Detect communities via label propagation.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_cdlp'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if direction is not None:
            cmd['direction'] = direction
        if max_iterations is not None:
            cmd['max_iterations'] = max_iterations
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphCdlpData.from_wire(data)

    def graph_analytics_lcc(self, graph, *, as_of=None, budget=None, branch=None, space=None):
        """Compute local clustering coefficients.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_lcc'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphLccData.from_wire(data)

    def graph_analytics_pagerank(self, graph, *, as_of=None, budget=None, damping=None, max_iterations=None, personalization=None, tolerance=None, branch=None, space=None):
        """Compute PageRank importance scores.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_pagerank_options, invalid_argument.engine.graph_personalization, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_pagerank'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if damping is not None:
            cmd['damping'] = damping
        if max_iterations is not None:
            cmd['max_iterations'] = max_iterations
        if personalization is not None:
            cmd['personalization'] = personalization
        if tolerance is not None:
            cmd['tolerance'] = tolerance
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphPagerankData.from_wire(data)

    def graph_analytics_sssp(self, graph, source, *, as_of=None, budget=None, direction=None, branch=None, space=None):
        """Compute shortest-path distances from a source.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, not_found.engine.graph_node, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_sssp'}
        cmd['graph'] = graph
        cmd['source'] = source
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if direction is not None:
            cmd['direction'] = direction
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphSsspData.from_wire(data)

    def graph_analytics_wcc(self, graph, *, as_of=None, budget=None, branch=None, space=None):
        """Compute weakly connected components.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, resource_exhausted.engine.graph_analytics_budget, invalid_argument.executor.graph_analytics_budget
        """
        cmd = {'type': 'graph_wcc'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if budget is not None:
            cmd['budget'] = {'max_edges': (None if budget.get('max_edges') is None else budget['max_edges']), 'max_nodes': (None if budget.get('max_nodes') is None else budget['max_nodes'])}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.GraphWccData.from_wire(data)

    def graph_apply_delete_policy(self, target, policy, *, branch=None, space=None):
        """Apply a delete policy to bound graph facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_binding
        """
        cmd = {'type': 'graph_apply_delete_policy'}
        cmd['target'] = {'branch': (None if target.get('branch') is None else target['branch']), 'key': target['key'], 'primitive': target['primitive'], 'space': target['space']}
        cmd['policy'] = policy
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'policy': data['policy']})

    def graph_batch_write(self, graph, operations, *, branch=None, space=None):
        """Apply graph mutations atomically.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_batch, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type, invalid_argument.engine.graph_edge_endpoint, failed_precondition.engine.graph_ontology_node_type, failed_precondition.engine.graph_ontology_edge_type
        """
        cmd = {'type': 'graph_batch_write'}
        cmd['graph'] = graph
        cmd['operations'] = [_x for _x in (operations or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'applied': data['applied'], 'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'graph': data['graph'], 'items': [models.BatchItem10.from_wire(_x) for _x in (data['items'] or [])], 'mode': models.BatchMode(data['mode']), 'status': models.BatchStatus(data['status'])})

    def graph_bindings(self, target, *, as_of=None, cursor=None, limit=None, branch=None, space=None):
        """Find graph nodes bound to an entity.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_binding
        """
        cmd = {'type': 'graph_bindings_for_entity'}
        cmd['target'] = {'branch': (None if target.get('branch') is None else target['branch']), 'key': target['key'], 'primitive': target['primitive'], 'space': target['space']}
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.GraphBindingHit.from_wire(_x) for _x in (data['items'] or [])]})

    def graph_bulk_insert(self, graph, *, chunk_size=None, edges=None, nodes=None, branch=None, space=None):
        """Bulk-load nodes and edges in chunks.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type, invalid_argument.engine.graph_edge_weight, invalid_argument.engine.graph_edge_endpoint, invalid_argument.engine.graph_properties, invalid_argument.engine.graph_properties_too_large, failed_precondition.engine.graph_negative_weight, failed_precondition.engine.graph_ontology_node_type, failed_precondition.engine.graph_ontology_edge_type
        """
        cmd = {'type': 'graph_bulk_insert'}
        cmd['graph'] = graph
        if chunk_size is not None:
            cmd['chunk_size'] = chunk_size
        if edges is not None:
            cmd['edges'] = [{'dst': _x['dst'], 'edge_type': _x['edge_type'], 'properties': (None if _x.get('properties') is None else _x['properties']), 'src': _x['src'], 'weight': (None if _x.get('weight') is None else _x['weight'])} for _x in (edges or [])]
        if nodes is not None:
            cmd['nodes'] = [{'binding': (None if _x.get('binding') is None else {'target': {'branch': (None if _x['binding']['target'].get('branch') is None else _x['binding']['target']['branch']), 'key': _x['binding']['target']['key'], 'primitive': _x['binding']['target']['primitive'], 'space': _x['binding']['target']['space']}}), 'node_id': _x['node_id'], 'object_type': (None if _x.get('object_type') is None else _x['object_type']), 'properties': (None if _x.get('properties') is None else _x['properties'])} for _x in (nodes or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'commits': data['commits'], 'edges_inserted': data['edges_inserted'], 'graph': data['graph'], 'nodes_inserted': data['nodes_inserted']})

    def graph_create(self, graph, *, branch=None, space=None):
        """Create a named graph.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, already_exists.engine.graph, invalid_argument.engine.graph_name_reserved
        """
        cmd = {'type': 'graph_create'}
        cmd['graph'] = graph
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'info': models.GraphInfoData.from_wire(data['info'])})

    def graph_delete(self, graph, *, branch=None, space=None):
        """Delete a graph and its visible data.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph
        """
        cmd = {'type': 'graph_delete'}
        cmd['graph'] = graph
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'dst': (None if data.get('dst') is None else data['dst']), 'edge_type': (None if data.get('edge_type') is None else data['edge_type']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'node_id': (None if data.get('node_id') is None else data['node_id']), 'src': (None if data.get('src') is None else data['src'])})

    def graph_edge_add(self, graph, src, edge_type, dst, *, properties=None, weight=None, branch=None, space=None):
        """Add or replace a graph edge.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type, invalid_argument.engine.graph_edge_type_reserved, invalid_argument.engine.graph_edge_weight, invalid_argument.engine.graph_edge_endpoint, invalid_argument.engine.graph_properties, invalid_argument.engine.graph_properties_too_large, failed_precondition.engine.graph_negative_weight, failed_precondition.engine.graph_ontology_edge_type, failed_precondition.engine.graph_ontology_endpoint_type
        """
        cmd = {'type': 'graph_add_edge'}
        cmd['graph'] = graph
        cmd['src'] = src
        cmd['edge_type'] = edge_type
        cmd['dst'] = dst
        if properties is not None:
            cmd['properties'] = properties
        if weight is not None:
            cmd['weight'] = weight
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'dst': data['dst'], 'edge_type': data['edge_type'], 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'src': data['src']})

    def graph_edge_get(self, graph, src, edge_type, dst, *, as_of=None, branch=None, space=None):
        """Read one graph edge.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type
        """
        cmd = {'type': 'graph_get_edge'}
        cmd['graph'] = graph
        cmd['src'] = src
        cmd['edge_type'] = edge_type
        cmd['dst'] = dst
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.Maybe5.from_wire(data)

    def graph_edge_remove(self, graph, src, edge_type, dst, *, branch=None, space=None):
        """Remove a graph edge.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type
        """
        cmd = {'type': 'graph_remove_edge'}
        cmd['graph'] = graph
        cmd['src'] = src
        cmd['edge_type'] = edge_type
        cmd['dst'] = dst
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'dst': (None if data.get('dst') is None else data['dst']), 'edge_type': (None if data.get('edge_type') is None else data['edge_type']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'node_id': (None if data.get('node_id') is None else data['node_id']), 'src': (None if data.get('src') is None else data['src'])})

    def graph_list(self, *, as_of=None, cursor=None, limit=None, branch=None, space=None):
        """List graph names.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name
        """
        cmd = {'type': 'graph_list'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [_x for _x in (data['items'] or [])]})

    def graph_meta(self, graph, *, as_of=None, branch=None, space=None):
        """Read graph metadata and counts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph
        """
        cmd = {'type': 'graph_get_meta'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else models.GraphInfoData.from_wire(data))

    def graph_neighbors(self, graph, node_id, direction, *, as_of=None, cursor=None, edge_type=None, limit=None, branch=None, space=None):
        """List a node's neighbors.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_edge_type
        """
        cmd = {'type': 'graph_neighbors'}
        cmd['graph'] = graph
        cmd['node_id'] = node_id
        cmd['direction'] = direction
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if edge_type is not None:
            cmd['edge_type'] = edge_type
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.GraphNeighborHit.from_wire(_x) for _x in (data['items'] or [])]})

    def graph_node_add(self, graph, node_id, *, binding=None, object_type=None, properties=None, branch=None, space=None):
        """Add or replace a graph node.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id, invalid_argument.engine.graph_properties, invalid_argument.engine.graph_properties_too_large, invalid_argument.engine.graph_type_hint, invalid_argument.engine.graph_binding, unsupported.engine.graph_binding_cross_branch, failed_precondition.engine.graph_ontology_node_type, failed_precondition.engine.graph_ontology_required_property
        """
        cmd = {'type': 'graph_add_node'}
        cmd['graph'] = graph
        cmd['node_id'] = node_id
        if binding is not None:
            cmd['binding'] = {'target': {'branch': (None if binding['target'].get('branch') is None else binding['target']['branch']), 'key': binding['target']['key'], 'primitive': binding['target']['primitive'], 'space': binding['target']['space']}}
        if object_type is not None:
            cmd['object_type'] = object_type
        if properties is not None:
            cmd['properties'] = properties
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'node_id': data['node_id']})

    def graph_node_get(self, graph, node_id, *, as_of=None, branch=None, space=None):
        """Read one graph node.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id
        """
        cmd = {'type': 'graph_get_node'}
        cmd['graph'] = graph
        cmd['node_id'] = node_id
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.Maybe4.from_wire(data)

    def graph_node_list(self, graph, *, as_of=None, cursor=None, limit=None, prefix=None, branch=None, space=None):
        """List graph nodes.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id
        """
        cmd = {'type': 'graph_list_nodes'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.GraphNodeDataOutput.from_wire(_x) for _x in (data['items'] or [])]})

    def graph_node_remove(self, graph, node_id, *, branch=None, space=None):
        """Remove a graph node and its edges.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_node_id
        """
        cmd = {'type': 'graph_remove_node'}
        cmd['graph'] = graph
        cmd['node_id'] = node_id
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'dst': (None if data.get('dst') is None else data['dst']), 'edge_type': (None if data.get('edge_type') is None else data['edge_type']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'node_id': (None if data.get('node_id') is None else data['node_id']), 'src': (None if data.get('src') is None else data['src'])})

    def graph_nodes_by_type(self, graph, object_type, *, as_of=None, cursor=None, limit=None, branch=None, space=None):
        """List nodes declaring an object type.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_type_name, invalid_argument.engine.graph_node_id
        """
        cmd = {'type': 'graph_nodes_by_type'}
        cmd['graph'] = graph
        cmd['object_type'] = object_type
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.GraphNodeDataOutput.from_wire(_x) for _x in (data['items'] or [])]})

    def graph_ontology_define_link_type(self, graph, name, source, target, *, cardinality=None, properties=None, branch=None, space=None):
        """Define a graph link type.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_type_name, invalid_argument.engine.graph_type_name_reserved, invalid_argument.engine.graph_property_name, failed_precondition.engine.graph_ontology_frozen
        """
        cmd = {'type': 'graph_define_link_type'}
        cmd['graph'] = graph
        cmd['name'] = name
        cmd['source'] = source
        cmd['target'] = target
        if cardinality is not None:
            cmd['cardinality'] = cardinality
        if properties is not None:
            cmd['properties'] = properties
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'kind': data['kind'], 'type_name': data['type_name']})

    def graph_ontology_define_object_type(self, graph, name, *, properties=None, branch=None, space=None):
        """Define a graph object type.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_type_name, invalid_argument.engine.graph_type_name_reserved, invalid_argument.engine.graph_property_name, failed_precondition.engine.graph_ontology_frozen
        """
        cmd = {'type': 'graph_define_object_type'}
        cmd['graph'] = graph
        cmd['name'] = name
        if properties is not None:
            cmd['properties'] = properties
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'kind': data['kind'], 'type_name': data['type_name']})

    def graph_ontology_delete_link_type(self, graph, name, *, branch=None, space=None):
        """Delete a draft link type.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_type_name, failed_precondition.engine.graph_ontology_frozen
        """
        cmd = {'type': 'graph_delete_link_type'}
        cmd['graph'] = graph
        cmd['name'] = name
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'kind': data['kind'], 'type_name': data['type_name']})

    def graph_ontology_delete_object_type(self, graph, name, *, branch=None, space=None):
        """Delete a draft object type.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, invalid_argument.engine.graph_type_name, failed_precondition.engine.graph_ontology_frozen
        """
        cmd = {'type': 'graph_delete_object_type'}
        cmd['graph'] = graph
        cmd['name'] = name
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'graph': data['graph'], 'kind': data['kind'], 'type_name': data['type_name']})

    def graph_ontology_freeze(self, graph, *, branch=None, space=None):
        """Freeze the graph ontology.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph, failed_precondition.engine.graph_ontology_freeze, failed_precondition.engine.graph_ontology_frozen
        """
        cmd = {'type': 'graph_freeze_ontology'}
        cmd['graph'] = graph
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'graph': data['graph'], 'link_types': data['link_types'], 'object_types': data['object_types']})

    def graph_ontology_get(self, graph, *, as_of=None, branch=None, space=None):
        """Read the graph ontology.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph
        """
        cmd = {'type': 'graph_get_ontology'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else models.GraphOntologyData.from_wire(data))

    def graph_ontology_summary(self, graph, *, as_of=None, branch=None, space=None):
        """Read the ontology with usage counts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph
        """
        cmd = {'type': 'graph_ontology_summary'}
        cmd['graph'] = graph
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else models.GraphOntologySummaryData.from_wire(data))

    def graph_sample(self, graph, *, count=None, branch=None, space=None):
        """Sample graph nodes.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.graph_name, not_found.engine.graph
        """
        cmd = {'type': 'graph_sample'}
        cmd['graph'] = graph
        if count is not None:
            cmd['count'] = count
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.GraphNodeDataOutput.from_wire(_x) for _x in (data['items'] or [])], 'total_count': data['total_count']})

    def json_batch_delete(self, entries, *, branch=None, space=None):
        """Delete multiple JSON documents or paths in one itemwise batch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long, invalid_argument.engine.json_path_type, invalid_argument.executor.json_batch_duplicate_key
        """
        cmd = {'type': 'json_batch_delete'}
        cmd['entries'] = [{'key': _x['key'], 'path': _x['path']} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult3.from_wire(data)

    def json_batch_exists(self, keys, *, branch=None, space=None):
        """Check existence for multiple JSON documents.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_batch_exists'}
        cmd['keys'] = [_x for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult6.from_wire(data)

    def json_batch_get(self, entries, *, branch=None, space=None):
        """Read multiple JSON values by document and path.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long
        """
        cmd = {'type': 'json_batch_get'}
        cmd['entries'] = [{'key': _x['key'], 'path': _x['path']} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult4.from_wire(data)

    def json_batch_set(self, entries, *, branch=None, space=None):
        """Set multiple JSON values in one itemwise batch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long, invalid_argument.engine.json_path_not_found, invalid_argument.engine.json_path_type, invalid_argument.engine.json_value, invalid_argument.engine.json_document_too_large, invalid_argument.engine.json_document_too_deep, invalid_argument.engine.json_array_too_large, invalid_argument.executor.json_batch_duplicate_key
        """
        cmd = {'type': 'json_batch_set'}
        cmd['entries'] = [{'key': _x['key'], 'path': _x['path'], 'value': _x['value']} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult3.from_wire(data)

    def json_count(self, *, as_of=None, prefix=None, branch=None, space=None):
        """Count visible JSON documents.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_count'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def json_delete(self, key, path, *, branch=None, space=None):
        """Delete a whole JSON document or one path inside it.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long, invalid_argument.engine.json_path_type
        """
        cmd = {'type': 'json_delete'}
        cmd['key'] = key
        cmd['path'] = path
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': data['key']})

    def json_exists(self, key, *, branch=None, space=None):
        """Check whether one JSON document exists.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_exists'}
        cmd['key'] = key
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def json_get(self, key, path, *, as_of=None, branch=None, space=None):
        """Read the current or historical JSON value at a document path.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long
        """
        cmd = {'type': 'json_get'}
        cmd['key'] = key
        cmd['path'] = path
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.MaybeJsonVersionedValue.from_wire(data)

    def json_history(self, key, *, branch=None, space=None):
        """Read retained version history for one JSON document.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_history'}
        cmd['key'] = key
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else [models.JsonHistoryItem.from_wire(_x) for _x in (data or [])])

    def json_index_create(self, name, field_path, index_type, *, branch=None, space=None):
        """Create a JSON secondary index on a field path.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_index_name, invalid_argument.engine.json_index_name_reserved, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long, already_exists.engine.json_index
        """
        cmd = {'type': 'json_create_index'}
        cmd['name'] = name
        cmd['field_path'] = field_path
        cmd['index_type'] = index_type
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.JsonIndexDefinition.from_wire(data)

    def json_index_drop(self, name, *, branch=None, space=None):
        """Drop a JSON secondary index by name.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_index_name, invalid_argument.engine.json_index_name_reserved
        """
        cmd = {'type': 'json_drop_index'}
        cmd['name'] = name
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def json_index_list(self, *, branch=None, space=None):
        """List JSON secondary indexes.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space
        """
        cmd = {'type': 'json_list_indexes'}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.JsonIndexDefinition.from_wire(_x) for _x in (data['items'] or [])]})

    def json_list(self, *, as_of=None, cursor=None, limit=None, prefix=None, branch=None, space=None):
        """List JSON document keys with optional prefix filtering.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_list'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [_x for _x in (data['items'] or [])]})

    def json_sample(self, *, count=None, prefix=None, branch=None, space=None):
        """Sample visible JSON documents.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_sample'}
        if count is not None:
            cmd['count'] = count
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.JsonSampleItem.from_wire(_x) for _x in (data['items'] or [])], 'total_count': data['total_count']})

    def json_scan(self, *, limit=None, start=None, branch=None, space=None):
        """Scan JSON documents with values and version facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id
        """
        cmd = {'type': 'json_scan'}
        if limit is not None:
            cmd['limit'] = limit
        if start is not None:
            cmd['start'] = start
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.JsonSampleItem.from_wire(_x) for _x in (data['items'] or [])]})

    def json_set(self, key, path, value, *, branch=None, space=None):
        """Set a JSON value at a document path, creating the document when missing.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.json_document_id, invalid_argument.engine.json_path, invalid_argument.engine.json_path_too_long, invalid_argument.engine.json_path_not_found, invalid_argument.engine.json_path_type, invalid_argument.engine.json_value, invalid_argument.engine.json_document_too_large, invalid_argument.engine.json_document_too_deep, invalid_argument.engine.json_array_too_large
        """
        cmd = {'type': 'json_set'}
        cmd['key'] = key
        cmd['path'] = path
        cmd['value'] = value
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': data['key']})

    def kv_batch_delete(self, keys, *, branch=None, space=None):
        """Delete multiple KV keys in one itemwise batch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key, invalid_argument.engine.kv_batch, invalid_argument.engine.kv_batch_duplicate_key, invalid_argument.executor.kv_batch_duplicate_key
        """
        cmd = {'type': 'kv_batch_delete'}
        cmd['keys'] = [_wire.b64e(_x) for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult.from_wire(data)

    def kv_batch_exists(self, keys, *, branch=None, space=None):
        """Check existence for multiple KV keys.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key, invalid_argument.engine.kv_batch
        """
        cmd = {'type': 'kv_batch_exists'}
        cmd['keys'] = [_wire.b64e(_x) for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult5.from_wire(data)

    def kv_batch_get(self, keys, *, branch=None, space=None):
        """Read multiple KV values by key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key, invalid_argument.engine.kv_batch
        """
        cmd = {'type': 'kv_batch_get'}
        cmd['keys'] = [_wire.b64e(_x) for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult2.from_wire(data)

    def kv_batch_put(self, entries, *, branch=None, space=None):
        """Store multiple KV values in one itemwise batch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key, invalid_argument.engine.kv_batch, invalid_argument.engine.kv_batch_duplicate_key, invalid_argument.executor.kv_batch_duplicate_key
        """
        cmd = {'type': 'kv_batch_put'}
        cmd['entries'] = [{'key': _wire.b64e(_x['key']), 'value': _wire.b64e(_x['value'])} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult.from_wire(data)

    def kv_count(self, *, as_of=None, prefix=None, branch=None, space=None):
        """Count visible KV keys.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_count'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if prefix is not None:
            cmd['prefix'] = _wire.b64e(prefix)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def kv_delete(self, key, *, branch=None, space=None):
        """Delete one visible KV key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_delete'}
        cmd['key'] = _wire.b64e(key)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': _wire.b64d(data['key'])})

    def kv_exists(self, key, *, branch=None, space=None):
        """Check whether one KV key exists.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_exists'}
        cmd['key'] = _wire.b64e(key)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def kv_get(self, key, *, as_of=None, branch=None, space=None):
        """Read the current or historical value for one KV key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_get'}
        cmd['key'] = _wire.b64e(key)
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.Maybe.from_wire(data)

    def kv_history(self, key, *, branch=None, space=None):
        """Read retained version history for one KV key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_history'}
        cmd['key'] = _wire.b64e(key)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else models.HistoryResult.from_wire(data))

    def kv_list(self, *, as_of=None, cursor=None, limit=None, prefix=None, branch=None, space=None):
        """List KV keys with optional prefix filtering.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_list'}
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = _wire.b64e(cursor)
        if limit is not None:
            cmd['limit'] = limit
        if prefix is not None:
            cmd['prefix'] = _wire.b64e(prefix)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else _wire.b64d(data['cursor'])), 'has_more': data['has_more'], 'items': [_wire.b64d(_x) for _x in (data['items'] or [])]})

    def kv_put(self, key, value, *, branch=None, space=None):
        """Store or replace a KV value by key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_put'}
        cmd['key'] = _wire.b64e(key)
        cmd['value'] = _wire.b64e(value)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': _wire.b64d(data['key'])})

    def kv_sample(self, *, count=None, prefix=None, branch=None, space=None):
        """Sample visible KV rows.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_sample'}
        if count is not None:
            cmd['count'] = count
        if prefix is not None:
            cmd['prefix'] = _wire.b64e(prefix)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else _wire.b64d(data['cursor'])), 'has_more': data['has_more'], 'items': [models.SampleItem.from_wire(_x) for _x in (data['items'] or [])], 'total_count': data['total_count']})

    def kv_scan(self, *, limit=None, start=None, branch=None, space=None):
        """Scan KV rows with values and version facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.kv_key
        """
        cmd = {'type': 'kv_scan'}
        if limit is not None:
            cmd['limit'] = limit
        if start is not None:
            cmd['start'] = _wire.b64e(start)
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else _wire.b64d(data['cursor'])), 'has_more': data['has_more'], 'items': [models.ScanItem.from_wire(_x) for _x in (data['items'] or [])]})

    def space_create(self, space, *, branch=None):
        """Create a product space on a branch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.product_space_reserved
        """
        cmd = {'type': 'space_create'}
        cmd['space'] = space
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'space': data['space']})

    def space_delete(self, space, *, force=None, branch=None):
        """Delete a product space from a branch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.product_space_reserved, invalid_argument.engine.space_delete_default, failed_precondition.engine.space_not_empty, invalid_argument.engine.space_delete_too_large
        """
        cmd = {'type': 'space_delete'}
        cmd['space'] = space
        if force is not None:
            cmd['force'] = force
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return _wire.Record({'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'deleted_rows': data['deleted_rows'], 'effect': models.MutationEffect.from_wire(data['effect']), 'force': data['force'], 'space': data['space']})

    def space_exists(self, space, *, branch=None):
        """Check whether a product space exists on a branch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.product_space_reserved
        """
        cmd = {'type': 'space_exists'}
        cmd['space'] = space
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return data

    def space_list(self, *, branch=None):
        """List product spaces on a branch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch
        """
        cmd = {'type': 'space_list'}
        if branch is not None:
            cmd['branch'] = branch
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [_x for _x in (data['items'] or [])]})

    def vector_batch_delete(self, collection, keys, *, branch=None, space=None):
        """Delete multiple vectors by key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_batch, invalid_argument.executor.vector_batch_duplicate_key
        """
        cmd = {'type': 'vector_batch_delete'}
        cmd['collection'] = collection
        cmd['keys'] = [_x for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult7.from_wire(data)

    def vector_batch_exists(self, collection, keys, *, branch=None, space=None):
        """Check existence for multiple vector keys.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_batch_exists'}
        cmd['collection'] = collection
        cmd['keys'] = [_x for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult6.from_wire(data)

    def vector_batch_get(self, collection, keys, *, branch=None, space=None):
        """Read multiple vectors by key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_batch
        """
        cmd = {'type': 'vector_batch_get'}
        cmd['collection'] = collection
        cmd['keys'] = [_x for _x in (keys or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult8.from_wire(data)

    def vector_batch_upsert(self, collection, entries, *, branch=None, space=None):
        """Upsert multiple vectors in one itemwise batch.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_batch, invalid_argument.engine.vector_dimension, invalid_argument.engine.vector_embedding, invalid_argument.executor.vector_dimension, invalid_argument.executor.vector_batch_duplicate_key
        """
        cmd = {'type': 'vector_batch_upsert'}
        cmd['collection'] = collection
        cmd['entries'] = [{'key': _x['key'], 'metadata': (None if _x.get('metadata') is None else _x['metadata']), 'vector': [_x for _x in (_x['vector'] or [])]} for _x in (entries or [])]
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.BatchResult7.from_wire(data)

    def vector_collection_create(self, collection, dimension, metric, *, branch=None, space=None):
        """Create a vector collection with a dimension and metric.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_dimension, invalid_argument.executor.vector_dimension
        """
        cmd = {'type': 'vector_create_collection'}
        cmd['collection'] = collection
        cmd['dimension'] = dimension
        cmd['metric'] = metric
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.VectorCollectionInfo.from_wire(_x) for _x in (data['items'] or [])]})

    def vector_collection_delete(self, collection, *, branch=None, space=None):
        """Delete a vector collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_delete_collection'}
        cmd['collection'] = collection
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def vector_collection_list(self, *, branch=None, space=None):
        """List vector collections.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_list_collections'}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.VectorCollectionInfo.from_wire(_x) for _x in (data['items'] or [])]})

    def vector_collection_stats(self, collection, *, branch=None, space=None):
        """Read facts for one vector collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_collection_stats'}
        cmd['collection'] = collection
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.VectorCollectionInfo.from_wire(_x) for _x in (data['items'] or [])]})

    def vector_count(self, collection, *, as_of=None, branch=None, space=None):
        """Count visible vectors in a collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_count'}
        cmd['collection'] = collection
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def vector_delete(self, collection, key, *, branch=None, space=None):
        """Delete one vector key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_delete'}
        cmd['collection'] = collection
        cmd['key'] = key
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'collection': data['collection'], 'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': data['key']})

    def vector_delete_all(self, collection, *, branch=None, space=None):
        """Delete all vectors in a collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_delete_all'}
        cmd['collection'] = collection
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'collection': data['collection'], 'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect'])})

    def vector_delete_by_filter(self, collection, filter, *, branch=None, space=None):
        """Delete vectors matching a metadata filter.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_filter
        """
        cmd = {'type': 'vector_delete_by_filter'}
        cmd['collection'] = collection
        cmd['filter'] = {'conditions': [{'field': _x['field'], 'op': _x['op'], 'value': _x['value']} for _x in (filter['conditions'] or [])]}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'collection': data['collection'], 'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect'])})

    def vector_exists(self, collection, key, *, branch=None, space=None):
        """Check whether one vector key exists.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_exists'}
        cmd['collection'] = collection
        cmd['key'] = key
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return data

    def vector_get(self, collection, key, *, as_of=None, branch=None, space=None):
        """Read one vector by key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_get'}
        cmd['collection'] = collection
        cmd['key'] = key
        if as_of is not None:
            cmd['as_of'] = as_of
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.Maybe2.from_wire(data)

    def vector_history(self, collection, key, *, branch=None, space=None):
        """Read retained vector history for one key.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_history'}
        cmd['collection'] = collection
        cmd['key'] = key
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return (None if data is None else models.VectorHistoryResult.from_wire(data))

    def vector_index_query(self, collection, query, k, *, as_of=None, filter=None, branch=None, space=None):
        """Search vectors and return index diagnostics.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_filter, invalid_argument.executor.vector_limit
        """
        cmd = {'type': 'vector_index_query'}
        cmd['collection'] = collection
        cmd['query'] = [_x for _x in (query or [])]
        cmd['k'] = k
        if as_of is not None:
            cmd['as_of'] = as_of
        if filter is not None:
            cmd['filter'] = {'conditions': [{'field': _x['field'], 'op': _x['op'], 'value': _x['value']} for _x in (filter['conditions'] or [])]}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return models.VectorIndexQueryResult.from_wire(data)

    def vector_keys(self, collection, *, as_of=None, cursor=None, limit=None, prefix=None, branch=None, space=None):
        """List vector keys in a collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_list_keys'}
        cmd['collection'] = collection
        if as_of is not None:
            cmd['as_of'] = as_of
        if cursor is not None:
            cmd['cursor'] = cursor
        if limit is not None:
            cmd['limit'] = limit
        if prefix is not None:
            cmd['prefix'] = prefix
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [_x for _x in (data['items'] or [])]})

    def vector_metadata_update(self, collection, key, patch, *, branch=None, space=None):
        """Patch metadata for one vector.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_metadata_patch
        """
        cmd = {'type': 'vector_update_metadata'}
        cmd['collection'] = collection
        cmd['key'] = key
        cmd['patch'] = patch
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'collection': data['collection'], 'commit': (None if data.get('commit') is None else models.CommitReceipt.from_wire(data['commit'])), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': data['key'], 'vector_revision': (None if data.get('vector_revision') is None else data['vector_revision'])})

    def vector_query(self, collection, query, k, *, as_of=None, filter=None, branch=None, space=None):
        """Search a vector collection.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_filter, invalid_argument.executor.vector_limit
        """
        cmd = {'type': 'vector_query'}
        cmd['collection'] = collection
        cmd['query'] = [_x for _x in (query or [])]
        cmd['k'] = k
        if as_of is not None:
            cmd['as_of'] = as_of
        if filter is not None:
            cmd['filter'] = {'conditions': [{'field': _x['field'], 'op': _x['op'], 'value': _x['value']} for _x in (filter['conditions'] or [])]}
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return [models.VectorMatch.from_wire(_x) for _x in (data or [])]

    def vector_sample(self, collection, *, count=None, branch=None, space=None):
        """Sample vectors with values and version facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_sample'}
        cmd['collection'] = collection
        if count is not None:
            cmd['count'] = count
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.VectorVersionedData.from_wire(_x) for _x in (data['items'] or [])], 'total_count': data['total_count']})

    def vector_scan(self, collection, *, limit=None, start=None, branch=None, space=None):
        """Scan vectors with values and version facts.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection
        """
        cmd = {'type': 'vector_scan'}
        cmd['collection'] = collection
        if limit is not None:
            cmd['limit'] = limit
        if start is not None:
            cmd['start'] = start
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'cursor': (None if data.get('cursor') is None else data['cursor']), 'has_more': data['has_more'], 'items': [models.VectorVersionedData.from_wire(_x) for _x in (data['items'] or [])]})

    def vector_upsert(self, collection, key, vector, *, metadata=None, branch=None, space=None):
        """Insert or replace one vector.

        Errors: failed_precondition.engine.runtime_closed, not_found.engine.branch, invalid_argument.engine.product_space, invalid_argument.engine.vector_collection, invalid_argument.engine.vector_key, not_found.engine.vector_collection, invalid_argument.engine.vector_dimension, invalid_argument.engine.vector_embedding, invalid_argument.engine.vector_metadata, invalid_argument.executor.vector_dimension
        """
        cmd = {'type': 'vector_upsert'}
        cmd['collection'] = collection
        cmd['key'] = key
        cmd['vector'] = [_x for _x in (vector or [])]
        if metadata is not None:
            cmd['metadata'] = metadata
        if branch is not None:
            cmd['branch'] = branch
        if space is not None:
            cmd['space'] = space
        data = self._core.data(cmd)
        return _wire.Record({'collection': data['collection'], 'commit': models.CommitReceipt.from_wire(data['commit']), 'effect': models.MutationEffect.from_wire(data['effect']), 'key': data['key'], 'vector_revision': data['vector_revision']})
