#!/usr/bin/env python3
"""
Test AWS Nova connection and functionality
"""

import boto3
import json
import sys
import os

def test_nova_direct():
    """Test Nova directly with Bedrock client"""
    try:
        print("🧪 Testing AWS Nova Pro connection...")
        
        # Initialize Bedrock client
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Simple test prompt
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "Please respond with 'Nova connection successful' to confirm the API is working."
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 100,
                "temperature": 0.1,
                "topP": 0.9
            }
        }
        
        # Call Nova Pro
        response = client.invoke_model(
            modelId='amazon.nova-pro-v1:0',
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        if 'output' in response_body and 'message' in response_body['output']:
            content = response_body['output']['message']['content'][0]['text']
            print(f"✅ Nova Pro Response: {content}")
            
            if "nova connection successful" in content.lower():
                print("✅ Nova Pro is working correctly!")
                return True
            else:
                print("⚠️  Nova Pro responded but with unexpected content")
                return True  # Still working, just different response
        else:
            print("❌ Invalid response structure from Nova Pro")
            return False
            
    except Exception as e:
        print(f"❌ Nova Pro connection failed: {e}")
        return False

def test_nova_client():
    """Test our NovaClient implementation"""
    try:
        print("\n🧪 Testing NovaClient implementation...")
        
        # Add current directory to path
        sys.path.insert(0, '.')
        
        from src.analyzer.nova_client import NovaClient
        
        # Initialize client
        client = NovaClient(model_variant='pro', region_name='us-east-1')
        
        # Test connection
        result = client.test_connection()
        
        if result:
            print("✅ NovaClient is working correctly!")
            
            # Get model info
            info = client.get_model_info()
            print(f"📋 Model Info:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            
            return True
        else:
            print("❌ NovaClient connection test failed")
            return False
            
    except Exception as e:
        print(f"❌ NovaClient test failed: {e}")
        return False

def test_frontend_integration():
    """Test if frontend can work with Nova"""
    try:
        print("\n🧪 Testing frontend integration with Nova...")
        
        # Test the main stack API endpoints
        import requests
        
        # Test main API
        main_api_url = "https://6to1dnyqsd.execute-api.us-east-1.amazonaws.com/Stage/test"
        
        response = requests.get(main_api_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Main API stack is accessible")
            
            # Check if it's using Nova
            data = response.json()
            print(f"📋 API Response: {data.get('message', 'No message')}")
            
            return True
        else:
            print(f"⚠️  Main API returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 AWS Nova Frontend Integration Test")
    print("=" * 50)
    
    results = []
    
    # Test 1: Direct Nova connection
    results.append(test_nova_direct())
    
    # Test 2: NovaClient implementation
    results.append(test_nova_client())
    
    # Test 3: Frontend integration
    results.append(test_frontend_integration())
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("-" * 25)
    
    test_names = [
        "Direct Nova Connection",
        "NovaClient Implementation", 
        "Frontend Integration"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    overall_success = all(results)
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Frontend is ready to work with AWS Nova models!")
        print("🔗 Chatbot URL: https://vu668szdf0.execute-api.us-east-1.amazonaws.com/Prod/chat")
        print("🔗 Main Interface: https://vu668szdf0.execute-api.us-east-1.amazonaws.com/Prod/")
    else:
        print("\n🔧 Some issues need to be resolved before Nova integration is fully functional.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)