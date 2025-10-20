# EnergyGrid.AI Application Flow Diagrams

## Production Architecture Flow

```mermaid
graph TB
    subgraph "User Interface"
        UI[Streamlit Web App]
        LOGIN[Login Page]
        DASH[Dashboard]
        UPLOAD[Upload Page]
        OBL[Obligations Page]
        TASKS[Tasks Page]
        REPORTS[Reports Page]
    end
    
    subgraph "Authentication Layer"
        COGNITO[AWS Cognito]
        JWT[JWT Tokens]
    end
    
    subgraph "API Gateway Layer"
        API[API Gateway]
        AUTH_CHECK[Authorization Check]
    end
    
    subgraph "Processing Pipeline"
        UPLOAD_LAMBDA[Upload Handler]
        ANALYZER[Analyzer Agent]
        PLANNER[Planner Agent]
        REPORTER[Reporter Agent]
        STATUS[Status Handler]
    end
    
    subgraph "AI Services"
        BEDROCK[Amazon Bedrock]
        CLAUDE[Claude 3 Sonnet]
    end
    
    subgraph "Storage"
        S3_DOCS[S3 Documents]
        S3_REPORTS[S3 Reports]
        DDB_DOCS[DynamoDB Documents]
        DDB_OBL[DynamoDB Obligations]
        DDB_TASKS[DynamoDB Tasks]
        DDB_REPORTS[DynamoDB Reports]
    end
    
    subgraph "Messaging"
        SQS_UPLOAD[Upload Queue]
        SQS_ANALYSIS[Analysis Queue]
        SQS_PLANNING[Planning Queue]
        SNS[SNS Notifications]
    end
    
    %% User Flow
    UI --> LOGIN
    LOGIN --> COGNITO
    COGNITO --> JWT
    JWT --> UI
    
    %% Navigation Flow
    UI --> DASH
    UI --> UPLOAD
    UI --> OBL
    UI --> TASKS
    UI --> REPORTS
    
    %% API Flow
    UPLOAD --> API
    OBL --> API
    TASKS --> API
    REPORTS --> API
    
    API --> AUTH_CHECK
    AUTH_CHECK --> JWT
    
    %% Processing Flow
    API --> UPLOAD_LAMBDA
    UPLOAD_LAMBDA --> S3_DOCS
    UPLOAD_LAMBDA --> SQS_UPLOAD
    UPLOAD_LAMBDA --> DDB_DOCS
    
    SQS_UPLOAD --> ANALYZER
    ANALYZER --> BEDROCK
    BEDROCK --> CLAUDE
    ANALYZER --> DDB_OBL
    ANALYZER --> SQS_ANALYSIS
    
    SQS_ANALYSIS --> PLANNER
    PLANNER --> DDB_TASKS
    PLANNER --> SQS_PLANNING
    
    SQS_PLANNING --> REPORTER
    REPORTER --> S3_REPORTS
    REPORTER --> DDB_REPORTS
    
    %% Status Updates
    ANALYZER --> STATUS
    PLANNER --> STATUS
    REPORTER --> STATUS
    STATUS --> SNS
    SNS --> UI
    
    %% Data Retrieval
    API --> DDB_DOCS
    API --> DDB_OBL
    API --> DDB_TASKS
    API --> DDB_REPORTS
    API --> S3_REPORTS
```

## Development Mode Flow (Local)

```mermaid
graph TB
    subgraph "Local Development Environment"
        DEV_UI[Streamlit App Dev]
        DEV_LOGIN[Mock Login]
        DEV_DASH[Mock Dashboard]
        DEV_UPLOAD[Mock Upload]
        DEV_OBL[Mock Obligations]
        DEV_TASKS[Mock Tasks]
        DEV_REPORTS[Mock Reports]
    end
    
    subgraph "Mock Authentication"
        MOCK_AUTH[MockAuth Class]
        DEMO_USERS[Demo User Accounts]
        SESSION[Session Manager]
    end
    
    subgraph "Mock Data"
        SAMPLE_DOCS[Sample Documents]
        SAMPLE_OBL[Sample Obligations]
        SAMPLE_TASKS[Sample Tasks]
        SAMPLE_REPORTS[Sample Reports]
    end
    
    subgraph "Simulated Processing"
        MOCK_UPLOAD[Simulated Upload]
        MOCK_PROCESS[Simulated Processing]
        PROGRESS[Progress Simulation]
    end
    
    %% Development Flow
    DEV_UI --> DEV_LOGIN
    DEV_LOGIN --> MOCK_AUTH
    MOCK_AUTH --> DEMO_USERS
    DEMO_USERS --> SESSION
    SESSION --> DEV_UI
    
    %% Navigation
    DEV_UI --> DEV_DASH
    DEV_UI --> DEV_UPLOAD
    DEV_UI --> DEV_OBL
    DEV_UI --> DEV_TASKS
    DEV_UI --> DEV_REPORTS
    
    %% Mock Data Flow
    DEV_DASH --> SAMPLE_DOCS
    DEV_OBL --> SAMPLE_OBL
    DEV_TASKS --> SAMPLE_TASKS
    DEV_REPORTS --> SAMPLE_REPORTS
    
    %% Simulated Processing
    DEV_UPLOAD --> MOCK_UPLOAD
    MOCK_UPLOAD --> MOCK_PROCESS
    MOCK_PROCESS --> PROGRESS
    PROGRESS --> DEV_UI
```

## Document Processing Workflow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant API as API Gateway
    participant Upload as Upload Lambda
    participant S3 as S3 Storage
    participant SQS as SQS Queue
    participant Analyzer as Analyzer Agent
    participant Bedrock as Amazon Bedrock
    participant DDB as DynamoDB
    participant Planner as Planner Agent
    participant Reporter as Reporter Agent
    
    User->>UI: Upload PDF Document
    UI->>API: POST /documents/upload
    API->>Upload: Process Upload
    Upload->>S3: Store PDF File
    Upload->>DDB: Save Document Metadata
    Upload->>SQS: Queue for Analysis
    Upload->>UI: Return Document ID
    UI->>User: Show Upload Success
    
    SQS->>Analyzer: Trigger Analysis
    Analyzer->>S3: Retrieve PDF
    Analyzer->>Bedrock: Extract Text & Analyze
    Bedrock->>Analyzer: Return Obligations
    Analyzer->>DDB: Store Obligations
    Analyzer->>SQS: Queue for Planning
    
    SQS->>Planner: Trigger Task Planning
    Planner->>DDB: Retrieve Obligations
    Planner->>DDB: Generate & Store Tasks
    Planner->>SQS: Queue for Reporting
    
    SQS->>Reporter: Trigger Report Generation
    Reporter->>DDB: Retrieve Data
    Reporter->>S3: Generate & Store Report
    Reporter->>DDB: Update Report Status
    
    User->>UI: Check Status
    UI->>API: GET /documents/{id}/status
    API->>DDB: Query Status
    DDB->>API: Return Status
    API->>UI: Status Response
    UI->>User: Display Progress
```

## User Authentication Flow

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    
    state "Production Auth" as ProdAuth {
        Unauthenticated --> LoginForm : Access App
        LoginForm --> CognitoAuth : Submit Credentials
        CognitoAuth --> Authenticated : Valid Credentials
        CognitoAuth --> LoginForm : Invalid Credentials
        Authenticated --> TokenCheck : Each Request
        TokenCheck --> Authenticated : Valid Token
        TokenCheck --> RefreshToken : Expired Token
        RefreshToken --> Authenticated : Success
        RefreshToken --> LoginForm : Failed
        Authenticated --> Unauthenticated : Logout
    }
    
    state "Development Auth" as DevAuth {
        Unauthenticated --> MockLogin : Access App
        MockLogin --> MockAuth : Submit Credentials
        MockAuth --> Authenticated : Valid Demo Account
        MockAuth --> MockLogin : Invalid Credentials
        Authenticated --> Unauthenticated : Logout
    }
```

## Page Navigation Flow

```mermaid
graph LR
    subgraph "Main Navigation"
        HOME[Dashboard]
        UPLOAD[Upload Documents]
        OBL[Obligations]
        TASKS[Tasks]
        REPORTS[Reports]
    end
    
    subgraph "Dashboard Features"
        METRICS[System Metrics]
        ACTIVITY[Recent Activity]
        ALERTS[Status Alerts]
    end
    
    subgraph "Upload Features"
        FILE_SELECT[File Selection]
        PROGRESS[Upload Progress]
        VALIDATION[File Validation]
    end
    
    subgraph "Obligations Features"
        OBL_LIST[Obligations List]
        OBL_FILTER[Filtering]
        OBL_DETAIL[Obligation Details]
    end
    
    subgraph "Tasks Features"
        TASK_LIST[Tasks List]
        TASK_FILTER[Task Filtering]
        TASK_ASSIGN[Task Assignment]
    end
    
    subgraph "Reports Features"
        REPORT_GEN[Report Generation]
        REPORT_LIST[Reports List]
        REPORT_DOWNLOAD[Download Reports]
    end
    
    %% Navigation Links
    HOME --> UPLOAD
    HOME --> OBL
    HOME --> TASKS
    HOME --> REPORTS
    
    %% Feature Connections
    HOME --> METRICS
    HOME --> ACTIVITY
    HOME --> ALERTS
    
    UPLOAD --> FILE_SELECT
    UPLOAD --> PROGRESS
    UPLOAD --> VALIDATION
    
    OBL --> OBL_LIST
    OBL --> OBL_FILTER
    OBL --> OBL_DETAIL
    
    TASKS --> TASK_LIST
    TASKS --> TASK_FILTER
    TASKS --> TASK_ASSIGN
    
    REPORTS --> REPORT_GEN
    REPORTS --> REPORT_LIST
    REPORTS --> REPORT_DOWNLOAD
```

## Data Flow Architecture

```mermaid
graph TD
    subgraph "Input Layer"
        PDF[PDF Documents]
        USER_INPUT[User Inputs]
    end
    
    subgraph "Processing Layer"
        TEXT_EXTRACT[Text Extraction]
        NLP[NLP Analysis]
        OBLIGATION_EXTRACT[Obligation Extraction]
        TASK_GEN[Task Generation]
        REPORT_GEN[Report Generation]
    end
    
    subgraph "Data Layer"
        DOC_META[Document Metadata]
        OBLIGATIONS[Compliance Obligations]
        TASKS[Audit Tasks]
        REPORTS[Compliance Reports]
        STATUS[Processing Status]
    end
    
    subgraph "Output Layer"
        DASHBOARD[Dashboard Views]
        TASK_LISTS[Task Lists]
        COMPLIANCE_REPORTS[PDF Reports]
        NOTIFICATIONS[Status Notifications]
    end
    
    %% Data Flow
    PDF --> TEXT_EXTRACT
    TEXT_EXTRACT --> NLP
    NLP --> OBLIGATION_EXTRACT
    OBLIGATION_EXTRACT --> OBLIGATIONS
    
    OBLIGATIONS --> TASK_GEN
    TASK_GEN --> TASKS
    
    OBLIGATIONS --> REPORT_GEN
    TASKS --> REPORT_GEN
    REPORT_GEN --> REPORTS
    
    USER_INPUT --> DOC_META
    
    %% Output Generation
    DOC_META --> DASHBOARD
    OBLIGATIONS --> DASHBOARD
    TASKS --> TASK_LISTS
    REPORTS --> COMPLIANCE_REPORTS
    STATUS --> NOTIFICATIONS
```