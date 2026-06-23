from ocelescope import Graph, GraphEdge, GraphNode, LayoutConfig, Resource, generate_color_map
from pydantic import BaseModel


class EventNode(BaseModel):
    id: str
    activity: str


class ObjectNode(BaseModel):
    id: str
    object_type: str


class Relation(BaseModel):
    qualifier: str
    source: str
    target: str
    object_type: str | None = None


class OCELGraph(Resource):
    label = "Ocel Graph"
    description = "A Ocel graph"

    events: list[EventNode] = []
    objects: list[ObjectNode] = []
    relations: list[Relation] = []

    @property
    def event_ids(self) -> list[str]:
        return [event.id for event in self.events]

    @property
    def object_ids(self) -> list[str]:
        return [object.id for object in self.objects]

    def visualize(self) -> Graph:
        color_map = generate_color_map(list(set([object.object_type for object in self.objects])))

        def node_width(label: str) -> float:
            return max(90.0, len(label) * 8.0 + 24.0)

        object_nodes = [
            GraphNode(
                id=object_node.id,
                shape="rectangle",
                label=object_node.id,
                color=color_map[object_node.object_type],
                width=node_width(object_node.id),
                height=40,
            )
            for object_node in self.objects
        ]

        event_nodes = [
            GraphNode(
                id=event.id,
                shape="rectangle",
                label=event.id,
                color="#f1f3f5",
                border_color="#adb5bd",
                width=node_width(event.id),
                height=40,
            )
            for event in self.events
        ]

        edges = [
            GraphEdge(
                source=edge.source,
                target=edge.target,
                label=edge.qualifier,
                color=color_map[edge.object_type] if edge.object_type else None,
            )
            for edge in self.relations
        ]

        return Graph(
            type="graph",
            nodes=object_nodes + event_nodes,
            edges=edges,
            layout_config=LayoutConfig(
                elk_options={
                    "elk.algorithm": "layered",
                    "elk.direction": "RIGHT",
                    "elk.edgeRouting": "SPLINES",
                    "elk.spacing.nodeNode": "60",
                    "elk.layered.spacing.nodeNodeBetweenLayers": "120",
                }
            ),
        )
