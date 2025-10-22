"""
Configuration settings for EnergyGrid.AI Streamlit application.
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration."""
    
    # API Configuration
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://6to1dnyqsd.execute-api.us-east-1.amazonaws.com/Stage')
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Cognito Configuration
    COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
    COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
    COGNITO_DOMAIN = os.getenv('COGNITO_DOMAIN')
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
    
    # Streamlit Configuration
    STREAMLIT_SERVER_PORT = int(os.getenv('STREAMLIT_SERVER_PORT', '8501'))
    STREAMLIT_SERVER_ADDRESS = os.getenv('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')
    
    @classmethod
    def get_cognito_config(cls) -> Dict[str, Any]:
        """Get Cognito configuration."""
        return {
            'user_pool_id': cls.COGNITO_USER_POOL_ID,
            'client_id': cls.COGNITO_CLIENT_ID,
            'region': cls.AWS_REGION,
            'domain': cls.COGNITO_DOMAIN
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.ENVIRONMENT.lower() == 'prod'
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate required configuration."""
        required_vars = [
            'API_BASE_URL',
            'COGNITO_USER_POOL_ID', 
            'COGNITO_CLIENT_ID'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            print(f"Missing required environment variables: {missing_vars}")
            return False
        
        return True