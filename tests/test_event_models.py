"""Unit tests for event models."""

import pytest
from uuid import uuid4, UUID
from pydantic import ValidationError

from src.ingestion.models.events import (
    NodeType,
    Action,
    EdgeType,
    GraphNodeEvent,
    GraphEdgeEvent,
)


class TestEnums:
    """Unit tests for Enum types."""

    def test_node_type_values(self):
        """Test NodeType enum values."""
        assert NodeType.USER == "user"
        assert NodeType.ARTICLE == "article"
        assert NodeType.PRODUCT == "product"
        assert NodeType.PRODUCT_TYPE == "product_type"
        assert NodeType.PRODUCT_GROUP == "product_group"
        assert NodeType.COLOUR_GROUP == "colour_group"
        assert NodeType.DEPARTMENT == "department"
        assert NodeType.INDEX_GROUP == "index_group"

    def test_action_values(self):
        """Test Action enum values."""
        assert Action.UPSERT == "UPSERT"
        assert Action.DELETE == "DELETE"

    def test_edge_type_values(self):
        """Test EdgeType enum values."""
        assert EdgeType.PURCHASED == "purchased"
        assert EdgeType.BELONGS_TO == "belongs_to"
        assert EdgeType.LIKES == "likes"


class TestGraphNodeEvent:
    """Unit tests for GraphNodeEvent model."""

    def test_graph_node_event_creation_minimal(self):
        """Test creating a GraphNodeEvent with minimal required fields."""
        event_id = uuid4()
        event = GraphNodeEvent(
            event_id=event_id,
            node_type=NodeType.USER,
            action=Action.UPSERT,
            label="user_123",
        )
        
        assert event.event_id == event_id
        assert event.node_type == NodeType.USER
        assert event.action == Action.UPSERT
        assert event.label == "user_123"
        assert event.data == {}

    def test_graph_node_event_creation_with_data(self):
        """Test creating a GraphNodeEvent with data payload."""
        event_id = uuid4()
        data = {"customer_id": "test123", "age": 25}
        event = GraphNodeEvent(
            event_id=event_id,
            node_type=NodeType.USER,
            action=Action.UPSERT,
            label="user_123",
            data=data,
        )
        
        assert event.event_id == event_id
        assert event.node_type == NodeType.USER
        assert event.data == data
        assert event.data["customer_id"] == "test123"
        assert event.data["age"] == 25

    def test_graph_node_event_article_type(self):
        """Test creating a GraphNodeEvent for an article node."""
        event_id = uuid4()
        event = GraphNodeEvent(
            event_id=event_id,
            node_type=NodeType.ARTICLE,
            action=Action.UPSERT,
            label="article_456",
            data={"article_id": "art456", "prod_name": "Summer Dress"},
        )
        
        assert event.node_type == NodeType.ARTICLE
        assert event.data["article_id"] == "art456"
        assert event.data["prod_name"] == "Summer Dress"

    def test_graph_node_event_delete_action(self):
        """Test creating a GraphNodeEvent with DELETE action."""
        event_id = uuid4()
        event = GraphNodeEvent(
            event_id=event_id,
            node_type=NodeType.USER,
            action=Action.DELETE,
            label="user_789",
        )
        
        assert event.action == Action.DELETE

    def test_graph_node_event_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GraphNodeEvent()
        
        error_str = str(exc_info.value)
        assert "event_id" in error_str
        assert "node_type" in error_str
        assert "action" in error_str
        assert "label" in error_str

    def test_graph_node_event_model_dump(self):
        """Test that GraphNodeEvent can be serialized to dict."""
        event_id = uuid4()
        event = GraphNodeEvent(
            event_id=event_id,
            node_type=NodeType.COLOUR_GROUP,
            action=Action.UPSERT,
            label="colour_blue",
            data={"name": "Blue"},
        )
        data = event.model_dump()
        
        assert isinstance(data["event_id"], UUID)
        assert data["node_type"] == "colour_group"
        assert data["action"] == "UPSERT"
        assert data["label"] == "colour_blue"
        assert data["data"]["name"] == "Blue"


class TestGraphEdgeEvent:
    """Unit tests for GraphEdgeEvent model."""

    def test_graph_edge_event_creation_minimal(self):
        """Test creating a GraphEdgeEvent with minimal required fields."""
        event_id = uuid4()
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.PURCHASED,
            source_node_id="user_123",
            source_node_type=NodeType.USER,
            target_node_id="article_456",
            target_node_type=NodeType.ARTICLE,
            action=Action.UPSERT,
        )
        
        assert event.event_id == event_id
        assert event.edge_type == EdgeType.PURCHASED
        assert event.source_node_id == "user_123"
        assert event.source_node_type == NodeType.USER
        assert event.target_node_id == "article_456"
        assert event.target_node_type == NodeType.ARTICLE
        assert event.action == Action.UPSERT
        assert event.data == {}

    def test_graph_edge_event_with_data(self):
        """Test creating a GraphEdgeEvent with data payload."""
        event_id = uuid4()
        data = {"purchase_date": "2024-01-01", "price": 49.99}
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.PURCHASED,
            source_node_id="user_123",
            source_node_type=NodeType.USER,
            target_node_id="article_456",
            target_node_type=NodeType.ARTICLE,
            action=Action.UPSERT,
            data=data,
        )
        
        assert event.data == data
        assert event.data["purchase_date"] == "2024-01-01"
        assert event.data["price"] == 49.99

    def test_graph_edge_event_belongs_to_edge(self):
        """Test creating a GraphEdgeEvent for belongs_to relationship."""
        event_id = uuid4()
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.BELONGS_TO,
            source_node_id="article_456",
            source_node_type=NodeType.ARTICLE,
            target_node_id="product_789",
            target_node_type=NodeType.PRODUCT,
            action=Action.UPSERT,
        )
        
        assert event.edge_type == EdgeType.BELONGS_TO
        assert event.source_node_type == NodeType.ARTICLE
        assert event.target_node_type == NodeType.PRODUCT

    def test_graph_edge_event_likes_edge(self):
        """Test creating a GraphEdgeEvent for likes relationship."""
        event_id = uuid4()
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.LIKES,
            source_node_id="user_123",
            source_node_type=NodeType.USER,
            target_node_id="colour_blue",
            target_node_type=NodeType.COLOUR_GROUP,
            action=Action.UPSERT,
        )
        
        assert event.edge_type == EdgeType.LIKES
        assert event.target_node_type == NodeType.COLOUR_GROUP

    def test_graph_edge_event_delete_action(self):
        """Test creating a GraphEdgeEvent with DELETE action."""
        event_id = uuid4()
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.PURCHASED,
            source_node_id="user_123",
            source_node_type=NodeType.USER,
            target_node_id="article_456",
            target_node_type=NodeType.ARTICLE,
            action=Action.DELETE,
        )
        
        assert event.action == Action.DELETE

    def test_graph_edge_event_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GraphEdgeEvent()
        
        error_str = str(exc_info.value)
        assert "event_id" in error_str
        assert "edge_type" in error_str
        assert "action" in error_str

    def test_graph_edge_event_model_dump(self):
        """Test that GraphEdgeEvent can be serialized to dict."""
        event_id = uuid4()
        event = GraphEdgeEvent(
            event_id=event_id,
            edge_type=EdgeType.LIKES,
            source_node_id="user_123",
            source_node_type=NodeType.USER,
            target_node_id="colour_red",
            target_node_type=NodeType.COLOUR_GROUP,
            action=Action.UPSERT,
            data={"confidence": 0.95},
        )
        data = event.model_dump()
        
        assert isinstance(data["event_id"], UUID)
        assert data["edge_type"] == "likes"
        assert data["source_node_id"] == "user_123"
        assert data["source_node_type"] == "user"
        assert data["target_node_id"] == "colour_red"
        assert data["target_node_type"] == "colour_group"
        assert data["action"] == "UPSERT"
        assert data["data"]["confidence"] == 0.95
