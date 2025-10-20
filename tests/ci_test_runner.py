#!/usr/bin/env python3
"""
Continuous Integration test runner for EnergyGrid.AI Compliance Copilot.
This script is designed to run in CI/CD environments with proper error handling and reporting.
"""

import os
import sys
import json
import time
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class TestResult:
    """Test result data structure."""
    name: str
    success: bool
    duration: float
    output: str
    error: Optional[str] = None
    skipped: bool = False
    coverage: Optional[float] = None


@dataclass
class CITestReport:
    """CI test report data structure."""
    timestamp: float
    environment: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration: float
    coverage_percentage: Optional[float]
    results: List[TestResult]


class CITestRunner:
    """CI-specific test runner with enhanced reporting and error handling."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.environment = os.getenv('ENVIRONMENT', 'ci')
        self.results: List[TestResult] = []
        self.start_time = time.time()
    
    def run_command(self, command: List[str], timeout: int = 300) -> TestResult:
        """Run a command and capture detailed results."""
        cmd_name = ' '.join(command[:2])  # Use first two parts as name
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            return TestResult(
                name=cmd_name,
                success=result.returncode == 0,
                duration=duration,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None
            )
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                name=cmd_name,
                success=False,
                duration=duration,
                output="",
                error=f"Command timed out after {timeout} seconds"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=cmd_name,
                success=False,
                duration=duration,
                output="",
                error=str(e)
            )
    
    def install_dependencies(self) -> TestResult:
        """Install all required dependencies."""
        print("📦 Installing dependencies...")
        
        # Install main requirements
        result = self.run_command([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], timeout=600)
        
        if not result.success:
            return result
        
        # Install test dependencies
        test_deps = [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'pytest-asyncio>=0.21.0',
            'pytest-xdist>=3.0.0',
            'pytest-html>=3.1.0',
            'pytest-json-report>=1.5.0',
            'moto>=4.2.0',
            'boto3>=1.26.0',
            'requests>=2.28.0',
            'locust>=2.15.0',
            'reportlab>=4.0.0',
            'coverage>=7.0.0',
            'bandit>=1.7.0',
            'safety>=2.3.0'
        ]
        
        dep_result = self.run_command([
            sys.executable, '-m', 'pip', 'install'
        ] + test_deps, timeout=600)
        
        if dep_result.success:
            print("✅ Dependencies installed successfully")
        else:
            print("❌ Failed to install dependencies")
        
        return dep_result
    
    def run_security_scan(self) -> TestResult:
        """Run security scanning with Bandit."""
        print("🔒 Running security scan...")
        
        result = self.run_command([
            'bandit', '-r', 'src/', '-f', 'json', '-o', 'bandit-report.json'
        ], timeout=120)
        
        # Bandit returns non-zero for findings, but we want to continue
        # Check if the report was generated
        report_path = self.project_root / 'bandit-report.json'
        if report_path.exists():
            result.success = True  # Report generated successfully
            print("✅ Security scan completed")
        else:
            print("⚠️  Security scan had issues")
        
        return result
    
    def run_dependency_check(self) -> TestResult:
        """Run dependency vulnerability check with Safety."""
        print("🛡️  Checking dependency vulnerabilities...")
        
        result = self.run_command([
            'safety', 'check', '--json', '--output', 'safety-report.json'
        ], timeout=120)
        
        # Safety returns non-zero for vulnerabilities, but we want to continue
        report_path = self.project_root / 'safety-report.json'
        if report_path.exists():
            result.success = True  # Report generated successfully
            print("✅ Dependency check completed")
        else:
            print("⚠️  Dependency check had issues")
        
        return result
    
    def run_unit_tests(self) -> TestResult:
        """Run unit tests with coverage."""
        print("🧪 Running unit tests...")
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'unit or not (integration or e2e or performance or smoke)',
            '-v',
            '--tb=short',
            '--cov=src',
            '--cov-report=term-missing',
            '--cov-report=xml:coverage.xml',
            '--cov-report=html:htmlcov',
            '--cov-fail-under=70',  # Minimum coverage threshold
            '--json-report',
            '--json-report-file=unit-test-report.json',
            '--html=unit-test-report.html',
            '--self-contained-html'
        ]
        
        # Add parallel execution in CI
        if os.getenv('CI'):
            command.extend(['-n', 'auto'])
        
        result = self.run_command(command, timeout=600)
        
        # Extract coverage from output
        coverage = self._extract_coverage_from_output(result.output)
        result.coverage = coverage
        
        if result.success:
            print(f"✅ Unit tests passed (Coverage: {coverage:.1f}%)")
        else:
            print("❌ Unit tests failed")
        
        return result
    
    def run_integration_tests(self) -> TestResult:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        # Check if AWS credentials are available
        if not os.getenv('AWS_ACCESS_KEY_ID'):
            print("⚠️  Skipping integration tests (no AWS credentials)")
            return TestResult(
                name="integration tests",
                success=True,
                duration=0.0,
                output="Skipped - no AWS credentials",
                skipped=True
            )
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'integration',
            '-v',
            '--tb=short',
            '--json-report',
            '--json-report-file=integration-test-report.json'
        ]
        
        result = self.run_command(command, timeout=900)
        
        if result.skipped:
            print("⚠️  Integration tests skipped")
        elif result.success:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
        
        return result
    
    def run_smoke_tests(self) -> TestResult:
        """Run smoke tests."""
        print("💨 Running smoke tests...")
        
        # Check if environment is configured for smoke tests
        if not os.getenv('ENVIRONMENT') or not os.getenv('AWS_REGION'):
            print("⚠️  Skipping smoke tests (environment not configured)")
            return TestResult(
                name="smoke tests",
                success=True,
                duration=0.0,
                output="Skipped - environment not configured",
                skipped=True
            )
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/smoke_tests.py',
            '-v',
            '--tb=short',
            '--json-report',
            '--json-report-file=smoke-test-report.json'
        ]
        
        result = self.run_command(command, timeout=300)
        
        if result.skipped:
            print("⚠️  Smoke tests skipped")
        elif result.success:
            print("✅ Smoke tests passed")
        else:
            print("❌ Smoke tests failed")
        
        return result
    
    def run_e2e_tests(self) -> TestResult:
        """Run end-to-end tests."""
        print("🌐 Running end-to-end tests...")
        
        # Check if API configuration is available
        if not os.getenv('API_BASE_URL') or not os.getenv('JWT_TOKEN'):
            print("⚠️  Skipping E2E tests (API not configured)")
            return TestResult(
                name="e2e tests",
                success=True,
                duration=0.0,
                output="Skipped - API not configured",
                skipped=True
            )
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/e2e/',
            '-v',
            '--tb=short',
            '-s',  # Don't capture output for E2E tests
            '--json-report',
            '--json-report-file=e2e-test-report.json'
        ]
        
        result = self.run_command(command, timeout=1800)
        
        if result.skipped:
            print("⚠️  E2E tests skipped")
        elif result.success:
            print("✅ E2E tests passed")
        else:
            print("❌ E2E tests failed")
        
        return result
    
    def validate_sam_template(self) -> TestResult:
        """Validate SAM template."""
        print("📋 Validating SAM template...")
        
        result = self.run_command(['sam', 'validate', '--lint'], timeout=60)
        
        if result.success:
            print("✅ SAM template is valid")
        else:
            print("❌ SAM template validation failed")
        
        return result
    
    def build_sam_application(self) -> TestResult:
        """Build SAM application."""
        print("🔨 Building SAM application...")
        
        result = self.run_command([
            'sam', 'build', '--cached', '--parallel'
        ], timeout=600)
        
        if result.success:
            print("✅ SAM application built successfully")
        else:
            print("❌ SAM build failed")
        
        return result
    
    def _extract_coverage_from_output(self, output: str) -> Optional[float]:
        """Extract coverage percentage from pytest output."""
        lines = output.split('\n')
        for line in lines:
            if 'TOTAL' in line and '%' in line:
                try:
                    # Look for percentage in the line
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            return float(part[:-1])
                except (ValueError, IndexError):
                    continue
        return None
    
    def generate_ci_report(self) -> CITestReport:
        """Generate comprehensive CI test report."""
        total_duration = time.time() - self.start_time
        
        passed = sum(1 for r in self.results if r.success and not r.skipped)
        failed = sum(1 for r in self.results if not r.success and not r.skipped)
        skipped = sum(1 for r in self.results if r.skipped)
        
        # Get coverage from unit test result
        coverage = None
        for result in self.results:
            if result.coverage is not None:
                coverage = result.coverage
                break
        
        return CITestReport(
            timestamp=self.start_time,
            environment=self.environment,
            total_tests=len(self.results),
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            total_duration=total_duration,
            coverage_percentage=coverage,
            results=self.results
        )
    
    def save_report(self, report: CITestReport):
        """Save CI test report to file."""
        report_file = self.project_root / 'ci-test-report.json'
        
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        print(f"📄 CI test report saved to: {report_file}")
    
    def print_summary(self, report: CITestReport):
        """Print test summary."""
        print("\n" + "="*60)
        print("🚀 CI TEST SUMMARY")
        print("="*60)
        
        for result in report.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            if result.skipped:
                status = "⚠️  SKIP"
            
            duration_str = f"{result.duration:.1f}s"
            print(f"{result.name:25} {status:8} {duration_str:>8}")
        
        print("="*60)
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed:      {report.passed_tests}")
        print(f"Failed:      {report.failed_tests}")
        print(f"Skipped:     {report.skipped_tests}")
        print(f"Duration:    {report.total_duration:.1f}s")
        
        if report.coverage_percentage is not None:
            print(f"Coverage:    {report.coverage_percentage:.1f}%")
        
        print("="*60)
        
        # Print failure details
        failed_results = [r for r in report.results if not r.success and not r.skipped]
        if failed_results:
            print("\n❌ FAILURE DETAILS:")
            for result in failed_results:
                print(f"\n{result.name}:")
                if result.error:
                    print(f"Error: {result.error}")
                if result.output:
                    # Print last few lines of output
                    lines = result.output.split('\n')[-10:]
                    print("Output (last 10 lines):")
                    for line in lines:
                        print(f"  {line}")
    
    def run_all_tests(self) -> int:
        """Run all CI tests and return exit code."""
        print("🚀 Starting CI test suite...")
        print(f"Environment: {self.environment}")
        print(f"Project root: {self.project_root}")
        
        # Test sequence
        test_sequence = [
            ("Install Dependencies", self.install_dependencies),
            ("Security Scan", self.run_security_scan),
            ("Dependency Check", self.run_dependency_check),
            ("Validate SAM Template", self.validate_sam_template),
            ("Build SAM Application", self.build_sam_application),
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("Smoke Tests", self.run_smoke_tests),
            ("E2E Tests", self.run_e2e_tests)
        ]
        
        # Run tests
        for test_name, test_func in test_sequence:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            self.results.append(result)
            
            # Stop on critical failures (but not skips)
            if not result.success and not result.skipped:
                if test_name in ["Install Dependencies", "Unit Tests"]:
                    print(f"💥 Critical failure in {test_name}, stopping CI run")
                    break
        
        # Generate and save report
        report = self.generate_ci_report()
        self.save_report(report)
        self.print_summary(report)
        
        # Determine exit code
        critical_failures = [
            r for r in self.results 
            if not r.success and not r.skipped and r.name in ["Install Dependencies", "Unit Tests"]
        ]
        
        if critical_failures:
            print("\n💥 CI run failed due to critical failures")
            return 1
        elif report.failed_tests > 0:
            print("\n⚠️  CI run completed with some failures")
            return 1
        else:
            print("\n✅ CI run completed successfully")
            return 0


def main():
    """Main entry point for CI test runner."""
    runner = CITestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()