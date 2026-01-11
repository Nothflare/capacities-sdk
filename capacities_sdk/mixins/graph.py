"""Graph traversal operations mixin."""

from typing import Any, Dict, List, Set

from ..models import GraphNode


class GraphMixin:
    """
    Mixin providing graph traversal operations.

    Requires on self:
        - get_object(object_id) -> Object
    """

    def trace_graph(
        self,
        start_object_id: str,
        max_depth: int = 3,
        direction: str = "both",
    ) -> List[GraphNode]:
        """
        Trace the object graph starting from a given object.

        Args:
            start_object_id: Starting object UUID
            max_depth: Maximum depth to traverse (1-3 recommended)
            direction: 'outgoing' (links from), 'incoming' (links to), or 'both'

        Returns:
            List of GraphNode instances representing the graph
        """
        if max_depth < 1 or max_depth > 10:
            raise ValueError("max_depth must be between 1 and 10")

        visited: Set[str] = set()
        result: List[GraphNode] = []
        queue: List[tuple] = [(start_object_id, 0, None)]

        while queue:
            current_id, depth, parent_id = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            obj = self.get_object(current_id)
            if not obj:
                continue

            node = GraphNode(object=obj, depth=depth, parent_id=parent_id)
            result.append(node)

            if depth >= max_depth:
                continue

            if direction in ("outgoing", "both"):
                for link_node in obj.link_nodes:
                    if link_node.target_id and link_node.target_id not in visited:
                        queue.append((link_node.target_id, depth + 1, current_id))

            if direction in ("incoming", "both") and depth == 0:
                if obj.raw_data and obj.databases:
                    pass

        return result

    def get_graph_summary(
        self, start_object_id: str, max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get a summary of the object graph.

        Args:
            start_object_id: Starting object UUID
            max_depth: Maximum depth to traverse

        Returns:
            Dict with graph statistics and structure
        """
        nodes = self.trace_graph(start_object_id, max_depth)

        adjacency = {}
        for node in nodes:
            adjacency[node.get_id()] = {
                "title": node.get_title(),
                "type": node.object.structure_id,
                "depth": node.depth,
                "links": [ln.target_id for ln in node.object.link_nodes],
            }

        type_counts = {}
        for node in nodes:
            t = node.object.structure_id
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": len(nodes),
            "max_depth_reached": max(n.depth for n in nodes) if nodes else 0,
            "type_counts": type_counts,
            "nodes": adjacency,
        }
