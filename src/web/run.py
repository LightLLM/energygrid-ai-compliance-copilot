#!/usr/bin/env python3
"""
Startup script for EnergyGrid.AI Streamlit application.
"""

import os
import sys
import subprocess

def main():
    """Main function to start the Streamlit application."""
    
    # Set environment variables if not already set
    if not os.getenv('COGNITO_USER_POOL_ID'):
        os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_example'
    
    if not os.getenv('COGNITO_CLIENT_ID'):
        os.environ['COGNITO_CLIENT_ID'] = 'example_client_id'
    
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = 'us-east-1'
    
    if not os.getenv('API_BASE_URL'):
        os.environ['API_BASE_URL'] = 'https://api.energygrid.ai'
    
    # Start Streamlit application
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port', '8501',
            '--server.address', '0.0.0.0',
            '--server.headless', 'true'
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start Streamlit application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down Streamlit application...")
        sys.exit(0)

if __name__ == "__main__":
    main()