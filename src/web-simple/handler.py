"""
Simple web interface for EnergyGrid.AI running on AWS Lambda
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Simple web interface handler that returns HTML
    """
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EnergyGrid.AI Compliance Copilot</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 3em;
                margin: 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .status-card {
                background: rgba(255, 255, 255, 0.2);
                padding: 20px;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .status-card h3 {
                margin-top: 0;
                color: #fff;
            }
            .status-success {
                border-left: 5px solid #4CAF50;
            }
            .status-info {
                border-left: 5px solid #2196F3;
            }
            .test-button {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin: 10px;
                transition: background 0.3s;
            }
            .test-button:hover {
                background: #45a049;
            }
            .api-response {
                background: rgba(0, 0, 0, 0.3);
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                font-family: monospace;
                white-space: pre-wrap;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ EnergyGrid.AI Compliance Copilot</h1>
                <p>AI-Powered Compliance Management System</p>
                <p><strong>🚀 Successfully Running on AWS!</strong></p>
            </div>
            
            <div class="status-grid">
                <div class="status-card status-success">
                    <h3>✅ API Gateway</h3>
                    <p><strong>Status:</strong> Active</p>
                    <p><strong>Endpoint:</strong> https://6to1dnyqsd.execute-api.us-east-1.amazonaws.com/Stage</p>
                    <button class="test-button" onclick="testAPI()">Test API</button>
                </div>
                
                <div class="status-card status-success">
                    <h3>✅ Lambda Functions</h3>
                    <p><strong>Status:</strong> Active</p>
                    <p><strong>Runtime:</strong> Python 3.13</p>
                    <p><strong>Memory:</strong> 512 MB</p>
                </div>
                
                <div class="status-card status-success">
                    <h3>✅ DynamoDB</h3>
                    <p><strong>Status:</strong> Active</p>
                    <p><strong>Table:</strong> dev-energygrid-documents</p>
                    <p><strong>Mode:</strong> Pay-per-request</p>
                </div>
                
                <div class="status-card status-success">
                    <h3>✅ S3 Storage</h3>
                    <p><strong>Status:</strong> Active</p>
                    <p><strong>Bucket:</strong> dev-energygrid-documents-242203354298</p>
                    <p><strong>Region:</strong> us-east-1</p>
                </div>
                
                <div class="status-card status-info">
                    <h3>🤖 AI Agents</h3>
                    <p><strong>Analyzer:</strong> Ready (Claude 3 Sonnet)</p>
                    <p><strong>Planner:</strong> Ready</p>
                    <p><strong>Reporter:</strong> Ready</p>
                </div>
                
                <div class="status-card status-info">
                    <h3>📊 Monitoring</h3>
                    <p><strong>CloudWatch:</strong> Active</p>
                    <p><strong>X-Ray Tracing:</strong> Enabled</p>
                    <p><strong>Logs:</strong> Available</p>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🧪 API Test Results</h3>
                <div id="api-response" class="api-response"></div>
            </div>
            
            <div class="status-card">
                <h3>📤 Document Upload</h3>
                <p>Upload regulatory documents for AI analysis:</p>
                <input type="file" id="fileInput" accept=".pdf" style="margin: 10px 0;">
                <button class="test-button" onclick="uploadDocument()">Upload & Analyze</button>
                <div id="upload-status" class="api-response"></div>
            </div>
            
            <div class="status-card">
                <h3>🔗 Quick Links</h3>
                <p>
                    <a href="https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?stackId=arn%3Aaws%3Acloudformation%3Aus-east-1%3A242203354298%3Astack%2Fenergygrid-compliance-copilot-dev" 
                       target="_blank" style="color: #fff; text-decoration: underline;">
                       📊 CloudFormation Stack
                    </a> |
                    <a href="https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/dev-energygrid-test" 
                       target="_blank" style="color: #fff; text-decoration: underline;">
                       ⚡ Lambda Functions
                    </a> |
                    <a href="https://console.aws.amazon.com/dynamodb/home?region=us-east-1#tables:selected=dev-energygrid-documents" 
                       target="_blank" style="color: #fff; text-decoration: underline;">
                       🗄️ DynamoDB Tables
                    </a>
                </p>
            </div>
        </div>
        
        <script>
            async function testAPI() {
                const responseDiv = document.getElementById('api-response');
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Testing API...';
                
                try {
                    const response = await fetch('https://6to1dnyqsd.execute-api.us-east-1.amazonaws.com/Stage/test');
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = 'Error: ' + error.message;
                }
            }
            
            async function uploadDocument() {
                const fileInput = document.getElementById('fileInput');
                const statusDiv = document.getElementById('upload-status');
                
                if (!fileInput.files[0]) {
                    alert('Please select a PDF file first');
                    return;
                }
                
                statusDiv.style.display = 'block';
                statusDiv.textContent = 'Uploading document...';
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    const response = await fetch('https://6to1dnyqsd.execute-api.us-east-1.amazonaws.com/Stage/documents/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    statusDiv.textContent = JSON.stringify(result, null, 2);
                    
                    if (response.ok) {
                        statusDiv.textContent += '\\n\\n✅ Document uploaded successfully! Processing will begin automatically.';
                    }
                } catch (error) {
                    statusDiv.textContent = 'Upload Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': html_content
    }