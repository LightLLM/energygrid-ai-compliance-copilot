# EnergyGrid.AI Web Interface

This is the Streamlit-based web interface for the EnergyGrid.AI Compliance Copilot system.

## Features

- **Authentication Integration**: Secure login with AWS Cognito
- **Document Upload**: Drag-and-drop PDF upload with progress tracking
- **Processing Dashboard**: Real-time status monitoring and system health
- **Obligations Management**: View and filter extracted compliance obligations
- **Tasks Management**: Track and manage audit tasks with assignment capabilities
- **Report Generation**: Create and download comprehensive compliance reports

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export COGNITO_USER_POOL_ID="your-user-pool-id"
export COGNITO_CLIENT_ID="your-client-id"
export AWS_REGION="us-east-1"
export API_BASE_URL="https://your-api-gateway-url"
```

3. Run the application:
```bash
python run.py
```

Or directly with Streamlit:
```bash
streamlit run app.py
```

## Configuration

The application can be configured through environment variables:

- `COGNITO_USER_POOL_ID`: AWS Cognito User Pool ID
- `COGNITO_CLIENT_ID`: AWS Cognito Client ID
- `AWS_REGION`: AWS region for Cognito and other services
- `API_BASE_URL`: Base URL for the EnergyGrid.AI API

## Architecture

The web interface is organized into the following components:

- `app.py`: Main application entry point
- `auth.py`: Authentication and session management
- `pages/`: Individual page modules
  - `upload.py`: Document upload interface
  - `dashboard.py`: Processing status dashboard
  - `obligations.py`: Obligations management
  - `tasks.py`: Tasks management
  - `reports.py`: Report generation and viewing

## Security

- All API calls are authenticated using JWT tokens from Cognito
- Role-based access control restricts features based on user permissions
- Session management with automatic token refresh
- Secure file upload with validation and size limits

## Usage

1. **Login**: Use your Cognito credentials to authenticate
2. **Upload Documents**: Drag and drop PDF regulatory documents
3. **Monitor Processing**: Track document processing through the dashboard
4. **Review Obligations**: View extracted compliance obligations with filtering
5. **Manage Tasks**: Assign and track audit tasks
6. **Generate Reports**: Create comprehensive compliance reports

## Development

For development, you can run the application in development mode:

```bash
streamlit run app.py --server.runOnSave true
```

This enables auto-reload when files are modified.

## Deployment

The application can be deployed using various methods:

1. **Docker**: Build a container with the application and dependencies
2. **Cloud Platforms**: Deploy to AWS ECS, Google Cloud Run, or similar
3. **Traditional Hosting**: Deploy to a server with Python and Streamlit

Make sure to configure the appropriate environment variables for your deployment environment.