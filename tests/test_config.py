"""Tests for the centralized configuration."""

import os
import pytest


def test_user_id_default():
    """Test that USER_ID has the correct default value."""
    from src.config import USER_ID, DEFAULT_USER_ID
    
    # If no environment variable is set, should use default
    if not os.getenv("USER_ID"):
        assert USER_ID == DEFAULT_USER_ID
        assert len(USER_ID) == 64  # SHA256 hex string length


def test_user_id_can_be_imported():
    """Test that USER_ID can be imported from config."""
    from src.config import USER_ID
    
    assert USER_ID is not None
    assert isinstance(USER_ID, str)
    assert len(USER_ID) > 0


def test_config_exports():
    """Test that config module exports expected values."""
    import src.config as config
    
    assert hasattr(config, 'USER_ID')
    assert hasattr(config, 'DEFAULT_USER_ID')
