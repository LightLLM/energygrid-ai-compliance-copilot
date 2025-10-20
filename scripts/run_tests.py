#!/usr/bin/env python3
"""
Comprehensive test runner for EnergyGrid.AI Compliance Copilot.
This script provides a unified interface for running all types of tests.
"""

import os
import sys
import subprocess
import argparse
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path


class TestRunner:
    """Comprehensive test runner for the compliance copilot."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.src_dir = self.project_root / "src"
        
        # Test categories
        self.test_categories = {
            'unit': {
                'description': 'Unit tests for individual components',
                'patterns': ['test_*.py'],
                'markers': ['unit'],
                'timeout': 300
            },
            'integration': {
                'description': 'Integration tests for API and services',
                'patterns': ['test_*integration*.py', 'test_api_*.py'],
                'markers': ['integration'],
                'timeout': 600
            },
            'e2e': {
                'description': 'End-to-end workflow tests',
                'patterns': ['test_*workflow*.py', 'e2e/test_*.py'],
                'markers': ['e2e'],
                'timeout': 1200
            },
            'performance': {
                'description': 'Performance and load tests',
                'patterns': ['performance/test_*.py', 'performance/load_test.py'],
                'markers': ['performance'],
                'timeout': 1800
            },
            'smoke': {
                'description': 'Smoke tests for deployment validation',
                'patterns': ['smoke_tests.py'],
                'markers': ['smoke'],
                'timeout': 300
            }
        }
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None, 
                   timeout: Optional[int] = None) -> Dict[str, Any]:
        """Run a command and return the result."""
        if cwd is None:
            cwd = self.project_root
        
        print(f"Running: {' '.join(command)}")
        print(f"Working directory: {cwd}")
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def install_dependencies(self) -> bool:
        """Install test dependencies."""
        print("Installing test dependencies...")
        
        # Install main requirements
        result = self.run_command([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        
        if not result['success']:
            print(f"Failed to install main requirements: {result['stderr']}")
            return False
        
        # Install test-specific dependencies
        test_deps = [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'pytest-asyncio>=0.21.0',
            'pytest-xdist>=3.0.0',  # For parallel test execution
            'moto>=4.2.0',
            'boto3>=1.26.0',
            'requests>=2.28.0',
            'locust>=2.15.0',  # For load testing
            'reportlab>=4.0.0',  # For PDF generation in tests
            'coverage>=7.0.0'
        ]
        
        result = self.run_command([
            sys.executable, '-m', 'pip', 'install'
        ] + test_deps)
        
        if not result['success']:
            print(f"Failed to install test dependencies: {result['stderr']}")
            return False
        
        print("✅ Dependencies installed successfully")
        return True
    
    def run_unit_tests(self, coverage: bool = True, parallel: bool = True) -> Dict[str, Any]:
        """Run unit tests."""
        print("\n🧪 Running unit tests...")
        
        command = [sys.executable, '-m', 'pytest']
        
        # Add test paths
        command.extend([
            'tests/',
            '-m', 'unit or not (integration or e2e or performance or smoke)',
            '-v',
            '--tb=short'
        ])
        
        # Add coverage if requested
        if coverage:
            command.extend([
                '--cov=src',
                '--cov-report=term-missing',
                '--cov-report=xml:coverage.xml',
                '--cov-report=html:htmlcov'
            ])
        
        # Add parallel execution if requested
        if parallel:
            command.extend(['-n', 'auto'])
        
        result = self.run_command(command, timeout=self.test_categories['unit']['timeout'])
        
        if result['success']:
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")
            print(result['stderr'])
        
        return result
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("\n🔗 Running integration tests...")
        
        # Check if environment is configured for integration tests
        required_env_vars = ['AWS_REGION']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Skipping integration tests. Missing environment variables: {missing_vars}")
            return {'success': True, 'skipped': True}
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'integration',
            '-v',
            '--tb=short'
        ]
        
        result = self.run_command(command, timeout=self.test_categories['integration']['timeout'])
        
        if result['success']:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            print(result['stderr'])
        
        return result
    
    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("\n🌐 Running end-to-end tests...")
        
        # Check if environment is configured for E2E tests
        required_env_vars = ['API_BASE_URL', 'JWT_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Skipping E2E tests. Missing environment variables: {missing_vars}")
            return {'success': True, 'skipped': True}
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/e2e/',
            '-v',
            '--tb=short',
            '-s'  # Don't capture output for E2E tests
        ]
        
        result = self.run_command(command, timeout=self.test_categories['e2e']['timeout'])
        
        if result['success']:
            print("✅ End-to-end tests passed")
        else:
            print("❌ End-to-end tests failed")
            print(result['stderr'])
        
        return result
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("\n⚡ Running performance tests...")
        
        # Check if environment is configured for performance tests
        required_env_vars = ['API_BASE_URL', 'JWT_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Skipping performance tests. Missing environment variables: {missing_vars}")
            return {'success': True, 'skipped': True}
        
        # Run pytest performance tests
        command = [
            sys.executable, '-m', 'pytest',
            'tests/performance/',
            '-v',
            '--tb=short'
        ]
        
        result = self.run_command(command, timeout=self.test_categories['performance']['timeout'])
        
        if result['success']:
            print("✅ Performance tests passed")
        else:
            print("❌ Performance tests failed")
            print(result['stderr'])
        
        return result
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """Run smoke tests."""
        print("\n💨 Running smoke tests...")
        
        # Check if environment is configured for smoke tests
        required_env_vars = ['ENVIRONMENT', 'AWS_REGION']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Skipping smoke tests. Missing environment variables: {missing_vars}")
            return {'success': True, 'skipped': True}
        
        command = [
            sys.executable, '-m', 'pytest',
            'tests/smoke_tests.py',
            '-v',
            '--tb=short'
        ]
        
        result = self.run_command(command, timeout=self.test_categories['smoke']['timeout'])
        
        if result['success']:
            print("✅ Smoke tests passed")
        else:
            print("❌ Smoke tests failed")
            print(result['stderr'])
        
        return result
    
    def run_load_tests(self, users: int = 10, duration: int = 60) -> Dict[str, Any]:
        """Run load tests using Locust."""
        print(f"\n🚀 Running load tests ({users} users for {duration}s)...")
        
        # Check if environment is configured for load tests
        required_env_vars = ['API_BASE_URL', 'JWT_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Skipping load tests. Missing environment variables: {missing_vars}")
            return {'success': True, 'skipped': True}
        
        # Run locust programmatically
        load_test_script = self.test_dir / 'performance' / 'load_test.py'
        
        if not load_test_script.exists():
            print("⚠️  Load test script not found")
            return {'success': False, 'error': 'Load test script not found'}
        
        command = [
            sys.executable, str(load_test_script)
        ]
        
        # Set environment variables for load test
        env = os.environ.copy()
        env['LOAD_TEST_USERS'] = str(users)
        env['LOAD_TEST_DURATION'] = str(duration)
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                env=env,
                timeout=duration + 60  # Add buffer time
            )
            
            if result.returncode == 0:
                print("✅ Load tests completed")
                return {'success': True}
            else:
                print("❌ Load tests failed")
                return {'success': False}
        
        except subprocess.TimeoutExpired:
            print("⚠️  Load tests timed out")
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"❌ Load tests failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_test_report(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Generate a comprehensive test report."""
        print("\n📊 Test Report Summary")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        for test_type, result in results.items():
            status = "✅ PASSED" if result.get('success', False) else "❌ FAILED"
            if result.get('skipped', False):
                status = "⚠️  SKIPPED"
                skipped_tests += 1
            elif result.get('success', False):
                passed_tests += 1
            else:
                failed_tests += 1
            
            total_tests += 1
            print(f"{test_type.upper():15} {status}")
        
        print("=" * 50)
        print(f"Total: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}, Skipped: {skipped_tests}")
        
        # Generate JSON report
        report_file = self.project_root / 'test-report.json'
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'skipped': skipped_tests
                },
                'results': results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: {report_file}")
    
    def run_all_tests(self, include_performance: bool = False, 
                     include_load: bool = False) -> Dict[str, Dict[str, Any]]:
        """Run all test suites."""
        print("🚀 Starting comprehensive test suite...")
        
        results = {}
        
        # Install dependencies first
        if not self.install_dependencies():
            print("❌ Failed to install dependencies")
            return {'dependency_install': {'success': False}}
        
        # Run unit tests
        results['unit'] = self.run_unit_tests()
        
        # Run integration tests
        results['integration'] = self.run_integration_tests()
        
        # Run E2E tests
        results['e2e'] = self.run_e2e_tests()
        
        # Run smoke tests
        results['smoke'] = self.run_smoke_tests()
        
        # Run performance tests if requested
        if include_performance:
            results['performance'] = self.run_performance_tests()
        
        # Run load tests if requested
        if include_load:
            results['load'] = self.run_load_tests()
        
        # Generate report
        self.generate_test_report(results)
        
        return results


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description='EnergyGrid.AI Test Runner')
    
    parser.add_argument('--type', choices=['unit', 'integration', 'e2e', 'performance', 'smoke', 'load', 'all'],
                       default='all', help='Type of tests to run')
    parser.add_argument('--coverage', action='store_true', default=True,
                       help='Generate coverage report for unit tests')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Run tests in parallel')
    parser.add_argument('--include-performance', action='store_true',
                       help='Include performance tests in "all" run')
    parser.add_argument('--include-load', action='store_true',
                       help='Include load tests in "all" run')
    parser.add_argument('--load-users', type=int, default=10,
                       help='Number of users for load testing')
    parser.add_argument('--load-duration', type=int, default=60,
                       help='Duration of load testing in seconds')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.type == 'unit':
        result = runner.run_unit_tests(coverage=args.coverage, parallel=args.parallel)
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'integration':
        result = runner.run_integration_tests()
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'e2e':
        result = runner.run_e2e_tests()
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'performance':
        result = runner.run_performance_tests()
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'smoke':
        result = runner.run_smoke_tests()
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'load':
        result = runner.run_load_tests(users=args.load_users, duration=args.load_duration)
        sys.exit(0 if result['success'] else 1)
    
    elif args.type == 'all':
        results = runner.run_all_tests(
            include_performance=args.include_performance,
            include_load=args.include_load
        )
        
        # Exit with error if any critical tests failed
        critical_failures = [
            name for name, result in results.items()
            if name in ['unit', 'integration'] and not result.get('success', False) and not result.get('skipped', False)
        ]
        
        sys.exit(1 if critical_failures else 0)


if __name__ == '__main__':
    main()