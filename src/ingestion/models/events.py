from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    USER = "user"
    ARTICLE = "article"
    PRODUCT = "product"
    PRODUCT_TYPE = "product_type"
    PRODUCT_GROUP = "product_group"
    COLOUR_GROUP = "colour_group"
    DEPARTMENT = "department"
    INDEX_GROUP = "index_group"


class Action(str, Enum):
    UPSERT = "UPSERT"
    DELETE = "DELETE"


class GraphNodeEvent(BaseModel):
    event_id: UUID = Field(..., description="Unique identifier for the event")
    node_type: NodeType = Field(..., description="Type of the graph node")
    data: dict[str, Any] = Field(default_factory=dict, description="Node data payload")
    action: Action = Field(..., description="Action to perform on the node")
    label: str = Field(..., description="Unique label")


class EdgeType(str, Enum):
    PURCHASED = "purchased"
    BELONGS_TO = "belongs_to"
    LIKES = "likes"


class GraphEdgeEvent(BaseModel):
    event_id: UUID = Field(..., description="Unique identifier for the event")
    edge_type: EdgeType = Field(..., description="Type of the graph edge")
    source_node_id: str = Field(..., description="ID of the source node")
    source_node_type: NodeType = Field(..., description="Type of the source node")
    target_node_id: str = Field(..., description="ID of the target node")
    target_node_type: NodeType = Field(..., description="Type of the target node")
    data: dict[str, Any] = Field(default_factory=dict, description="Edge data payload")
    action: Action = Field(..., description="Action to perform on the edge")

