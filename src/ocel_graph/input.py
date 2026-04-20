from ocelescope import OCEL_FIELD, PluginInput
from pydantic import BaseModel, Field


class ObjectRoot(BaseModel):
    class Config:
        title = "Object"

    object_id: str = OCEL_FIELD(
        field_type="object_id",
        title="Object Id",
        ocel_id="ocel",
        description="The ID of the Event which is the root of the OcelGraph",
    )


class EventRoot(BaseModel):
    class Config:
        title = "Event"

    event_id: str = OCEL_FIELD(
        field_type="event_id",
        title="Event Id",
        ocel_id="ocel",
        description="The ID of the Event which is the root of the OcelGraph",
    )


class OCELGraphInput(PluginInput):
    root: ObjectRoot | EventRoot
    depth: int = Field(
        title="OCEL Graph Depth", description="The maximum depth of the ocel graph", default=3, gt=0, le=10
    )
    max_neighbours: int = Field(
        title="Maximum Neighbours", description="The maximum amount of neighbours a node can have", gt=0, default=5
    )
