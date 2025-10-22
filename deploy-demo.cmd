@echo off
echo.
echo ========================================
echo   EnergyGrid.AI Demo Deployment
echo   Perfect for Judges and Reviewers
echo ========================================
echo.

REM Set environment
set ENVIRONMENT=demo
set STACK_NAME=energygrid-demo-web

echo 🚀 Deploying demo web interface...
echo Environment: %ENVIRONMENT%
echo Stack: %STACK_NAME%
echo.

REM Deploy the demo stack
aws cloudformation deploy ^
    --template-file demo-template.yaml ^
    --stack-name %STACK_NAME% ^
    --parameter-overrides Environment=%ENVIRONMENT% ^
    --capabilities CAPABILITY_IAM ^
    --region us-east-1

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Deployment failed!
    pause
    exit /b 1
)

echo.
echo ✅ Deployment successful!
echo.

REM Get the demo URL
echo 🔍 Getting demo URL...
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name %STACK_NAME% --query "Stacks[0].Outputs[?OutputKey=='DemoWebURL'].OutputValue" --output text --region us-east-1') do set DEMO_URL=%%i

echo.
echo ========================================
echo   🎯 DEMO READY FOR JUDGES!
echo ========================================
echo.
echo 🌐 Demo URL: %DEMO_URL%
echo.
echo 📋 Share this URL with judges for evaluation:
echo    %DEMO_URL%
echo.
echo ✨ Features available for testing:
echo    • AI Document Analysis
echo    • Document Upload Simulation  
echo    • Compliance Obligations View
echo    • Task Management Demo
echo    • Report Generation
echo    • System Health Check
echo.
echo 🎯 No login required - Perfect for judges!
echo ⚡ Loads instantly on any device
echo 📱 Mobile-friendly interface
echo.

REM Open in browser
echo 🌐 Opening demo in browser...
start "" "%DEMO_URL%"

echo.
echo Press any key to exit...
pause >nul