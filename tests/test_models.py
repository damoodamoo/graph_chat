"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.agents.models.models import User, Article, Preference, Preferences


class TestUser:
    """Unit tests for User model."""

    def test_user_creation_minimal(self):
        """Test creating a User with only required fields."""
        user = User(customer_id="test123")
        
        assert user.customer_id == "test123"
        assert user.age is None
        assert user.club_member_status is None
        assert user.fashion_news_frequency is None

    def test_user_creation_full(self):
        """Test creating a User with all fields."""
        user = User(
            customer_id="test123",
            age=25,
            club_member_status="ACTIVE",
            fashion_news_frequency="Regularly"
        )
        
        assert user.customer_id == "test123"
        assert user.age == 25
        assert user.club_member_status == "ACTIVE"
        assert user.fashion_news_frequency == "Regularly"

    def test_user_missing_required_field(self):
        """Test that missing customer_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            User()
        
        assert "customer_id" in str(exc_info.value)

    def test_user_model_dump(self):
        """Test that User can be serialized to dict."""
        user = User(customer_id="test123", age=30)
        data = user.model_dump()
        
        assert data["customer_id"] == "test123"
        assert data["age"] == 30
        assert data["club_member_status"] is None


class TestArticle:
    """Unit tests for Article model."""

    def test_article_creation_minimal(self):
        """Test creating an Article with only required fields."""
        article = Article(article_id="art123")
        
        assert article.article_id == "art123"
        assert article.product_code is None
        assert article.prod_name is None
        assert article.detail_desc is None

    def test_article_creation_full(self):
        """Test creating an Article with all fields."""
        article = Article(
            article_id="art123",
            product_code="PROD001",
            prod_name="Summer Dress",
            detail_desc="A beautiful summer dress"
        )
        
        assert article.article_id == "art123"
        assert article.product_code == "PROD001"
        assert article.prod_name == "Summer Dress"
        assert article.detail_desc == "A beautiful summer dress"

    def test_article_missing_required_field(self):
        """Test that missing article_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Article()
        
        assert "article_id" in str(exc_info.value)


class TestPreference:
    """Unit tests for Preference model."""

    def test_preference_creation_colour(self):
        """Test creating a Preference for a colour."""
        pref = Preference(item_type="colour_group", value="blue")
        
        assert pref.item_type == "colour_group"
        assert pref.value == "blue"

    def test_preference_creation_article(self):
        """Test creating a Preference for an article."""
        pref = Preference(item_type="article", value="0123456789")
        
        assert pref.item_type == "article"
        assert pref.value == "0123456789"

    def test_preference_missing_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Preference(item_type="colour_group")
        
        assert "value" in str(exc_info.value)

    def test_preference_model_dump(self):
        """Test that Preference can be serialized to dict."""
        pref = Preference(item_type="colour_group", value="red")
        data = pref.model_dump()
        
        assert data["item_type"] == "colour_group"
        assert data["value"] == "red"


class TestPreferences:
    """Unit tests for Preferences model."""

    def test_preferences_empty_list(self):
        """Test creating Preferences with empty list."""
        prefs = Preferences(prefs=[])
        
        assert prefs.prefs == []
        assert len(prefs.prefs) == 0

    def test_preferences_single_item(self):
        """Test creating Preferences with single preference."""
        pref = Preference(item_type="colour_group", value="blue")
        prefs = Preferences(prefs=[pref])
        
        assert len(prefs.prefs) == 1
        assert prefs.prefs[0].item_type == "colour_group"
        assert prefs.prefs[0].value == "blue"

    def test_preferences_multiple_items(self):
        """Test creating Preferences with multiple preferences."""
        pref1 = Preference(item_type="colour_group", value="blue")
        pref2 = Preference(item_type="article", value="0123456789")
        pref3 = Preference(item_type="colour_group", value="red")
        prefs = Preferences(prefs=[pref1, pref2, pref3])
        
        assert len(prefs.prefs) == 3
        assert prefs.prefs[0].value == "blue"
        assert prefs.prefs[1].value == "0123456789"
        assert prefs.prefs[2].value == "red"

    def test_preferences_model_dump(self):
        """Test that Preferences can be serialized to dict."""
        pref1 = Preference(item_type="colour_group", value="blue")
        pref2 = Preference(item_type="article", value="0123456789")
        prefs = Preferences(prefs=[pref1, pref2])
        data = prefs.model_dump()
        
        assert "prefs" in data
        assert len(data["prefs"]) == 2
        assert data["prefs"][0]["item_type"] == "colour_group"
        assert data["prefs"][1]["item_type"] == "article"
