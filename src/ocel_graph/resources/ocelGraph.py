from ocelescope import Resource
from ocelescope.visualization import Graph, GraphEdge, GraphvizLayoutConfig
from ocelescope.visualization.default.graph import GraphNode
from ocelescope.visualization.util.color import generate_color_map
from pydantic import BaseModel


class EventNode(BaseModel):
    id: str
    activity_type: str


class ObjectNode(BaseModel):
    id: str
    object_type: str


class Relation(BaseModel):
    qualifier: str


class O2ORelation(Relation):
    source: str
    target: str


class E2ORelation(Relation):
    event_id: str
    object_id: str
    object_type: str


class OCELGraph(Resource):
    label = "Ocel Graph"
    description = "A Ocel graph"

    events: list[EventNode] = []
    objects: list[ObjectNode] = []
    e2o_relations: list[E2ORelation] = []
    o2o_relations: list[O2ORelation] = []

    @property
    def event_ids(self) -> list[str]:
        return [event.id for event in self.events]

    @property
    def object_ids(self) -> list[str]:
        return [object.id for object in self.objects]

    def visualize(self) -> Graph:
        color_map = generate_color_map(list(set([object.object_type for object in self.objects])))

        object_nodes = [
            GraphNode(
                id=object_node.id, shape="rectangle", label=object_node.id, color=color_map[object_node.object_type]
            )
            for object_node in self.objects
        ]

        event_nodes = [GraphNode(id=event.id, shape="rectangle", label=event.id) for event in self.events]

        e2o_edges = [
            GraphEdge(
                source=edge.event_id,
                target=edge.object_id,
                color=color_map[edge.object_type],
                label=edge.qualifier,
            )
            for edge in self.e2o_relations
        ]
        o2o_edges = [
            GraphEdge(source=edge.source, target=edge.target, label=edge.qualifier) for edge in self.o2o_relations
        ]

        return Graph(
            type="graph",
            nodes=object_nodes + event_nodes,
            edges=e2o_edges + o2o_edges,
            layout_config=GraphvizLayoutConfig(engine="neato", graphAttrs={"overlap": "prism"}),
        )
