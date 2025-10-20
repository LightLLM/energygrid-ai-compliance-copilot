"""
Simple test for Bedrock client
"""

def test_simple():
    """Simple test that should pass"""
    assert True

def test_bedrock_import():
    """Test that we can import the Bedrock client"""
    from src.analyzer.bedrock_client import BedrockClient
    assert BedrockClient is not None