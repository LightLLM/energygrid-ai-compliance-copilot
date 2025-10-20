"""
Unit Tests for Planner Agent
Tests task generation logic, priority and timeline calculations, and error handling scenarios
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Mock AWS services before importing modules that use them
with patch('boto3.client'), patch('boto3.resource'):
    # Add src to path for imports
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'planner'))
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

    from task_planner import TaskPlanner, TaskPlannerError, TaskTemplate
    from models import (
        Obligation, Task, TaskPriority, TaskStatus, 
        ObligationCategory, ObligationSeverity, DeadlineType
    )

# Import handler separately with proper mocking
with patch('src.shared.dynamodb_helper.get_db_helper'), \
     patch('src.planner.task_planner.TaskPlanner'), \
     patch('boto3.client'), \
     patch('boto3.resource'):
    from src.planner.handler import lambda_handler, process_document_for_task_planning


class TestTaskPlannerTaskGeneration:
    """Test task generation logic from obligations"""
    
    @pytest.fixture
    def task_planner(self):
        """Task planner fixture with mocked Bedrock client"""
        with patch('boto3.client'):
            return TaskPlanner(region_name='us-east-1')
    
    @pytest.fixture
    def sample_obligations(self):
        """Sample obligations for testing task generation"""
        current_time = datetime.utcnow()
        return [
            Obligation(
                obligation_id='obl_reporting_001',
                document_id='doc_test123',
                description='Submit quarterly compliance reports to regulatory authority within 30 days of quarter end',
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=['utility companies', 'power generators'],
                extracted_text='All utility companies SHALL submit quarterly compliance reports',
                confidence_score=0.95,
                created_timestamp=current_time
            ),
            Obligation(
                obligation_id='obl_monitoring_001',
                document_id='doc_test123',
                description='Monitor grid stability parameters continuously and report deviations exceeding 5%',
                category=ObligationCategory.MONITORING,
                severity=ObligationSeverity.CRITICAL,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=['grid operators'],
                extracted_text='Utilities MUST continuously monitor grid stability parameters',
                confidence_score=0.92,
                created_timestamp=current_time
            ),
            Obligation(
                obligation_id='obl_operational_001',
                document_id='doc_test123',
                description='Implement emergency shutdown procedures within 60 seconds of critical failure',
                category=ObligationCategory.OPERATIONAL,
                severity=ObligationSeverity.CRITICAL,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=['control room operators'],
                extracted_text='Emergency shutdown procedures SHALL be implemented within 60 seconds',
                confidence_score=0.88,
                created_timestamp=current_time
            ),
            Obligation(
                obligation_id='obl_financial_001',
                document_id='doc_test123',
                description='Maintain insurance coverage of minimum $10 million for operational risks',
                category=ObligationCategory.FINANCIAL,
                severity=ObligationSeverity.MEDIUM,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=['all entities'],
                extracted_text='All entities SHALL maintain insurance coverage of minimum $10 million',
                confidence_score=0.90,
                created_timestamp=current_time
            )
        ]
    
    def test_generate_base_tasks_from_templates(self, task_planner, sample_obligations):
        """Test base task generation using predefined templates"""
        # Generate base tasks without AI enhancement
        base_tasks = task_planner._generate_base_tasks(sample_obligations)
        
        # Verify tasks were generated
        assert len(base_tasks) > 0
        
        # Group tasks by obligation
        tasks_by_obligation = {}
        for task in base_tasks:
            if task.obligation_id not in tasks_by_obligation:
                tasks_by_obligation[task.obligation_id] = []
            tasks_by_obligation[task.obligation_id].append(task)
        
        # Verify each obligation has associated tasks
        for obligation in sample_obligations:
            assert obligation.obligation_id in tasks_by_obligation
            obligation_tasks = tasks_by_obligation[obligation.obligation_id]
            assert len(obligation_tasks) > 0
            
            # Verify task properties
            for task in obligation_tasks:
                assert task.obligation_id == obligation.obligation_id
                assert task.status == TaskStatus.PENDING
                assert task.created_timestamp is not None
                assert task.due_date is not None
                assert task.title is not None and len(task.title) > 0
                assert task.description is not None and len(task.description) > 0
    
    def test_task_generation_with_different_categories(self, task_planner, sample_obligations):
        """Test task generation handles different obligation categories correctly"""
        base_tasks = task_planner._generate_base_tasks(sample_obligations)
        
        # Find tasks for each category
        reporting_tasks = [t for t in base_tasks if any(obl.obligation_id == t.obligation_id and obl.category == ObligationCategory.REPORTING for obl in sample_obligations)]
        monitoring_tasks = [t for t in base_tasks if any(obl.obligation_id == t.obligation_id and obl.category == ObligationCategory.MONITORING for obl in sample_obligations)]
        operational_tasks = [t for t in base_tasks if any(obl.obligation_id == t.obligation_id and obl.category == ObligationCategory.OPERATIONAL for obl in sample_obligations)]
        financial_tasks = [t for t in base_tasks if any(obl.obligation_id == t.obligation_id and obl.category == ObligationCategory.FINANCIAL for obl in sample_obligations)]
        
        # Verify category-specific task generation
        assert len(reporting_tasks) > 0
        assert len(monitoring_tasks) > 0
        assert len(operational_tasks) > 0
        assert len(financial_tasks) > 0
        
        # Verify reporting tasks contain appropriate keywords
        for task in reporting_tasks:
            assert any(keyword in task.title.lower() for keyword in ['report', 'prepare', 'submit'])
        
        # Verify monitoring tasks contain appropriate keywords
        for task in monitoring_tasks:
            assert any(keyword in task.title.lower() for keyword in ['monitor', 'establish', 'review'])
        
        # Verify operational tasks contain appropriate keywords
        for task in operational_tasks:
            assert any(keyword in task.title.lower() for keyword in ['implement', 'train', 'audit'])
        
        # Verify financial tasks contain appropriate keywords
        for task in financial_tasks:
            assert any(keyword in task.title.lower() for keyword in ['calculate', 'review', 'process'])
    
    def test_generate_tasks_without_ai_enhancement(self, task_planner, sample_obligations):
        """Test complete task generation without AI enhancement"""
        # Generate tasks without AI
        generated_tasks = task_planner.generate_tasks_from_obligations(
            obligations=sample_obligations,
            use_ai_enhancement=False
        )
        
        # Verify tasks were generated
        assert len(generated_tasks) > 0
        
        # Verify all tasks have required properties
        for task in generated_tasks:
            assert task.task_id is not None
            assert task.obligation_id in [obl.obligation_id for obl in sample_obligations]
            assert task.title is not None and len(task.title) > 0
            assert task.description is not None and len(task.description) > 0
            assert task.priority in [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]
            assert task.status == TaskStatus.PENDING
            assert task.due_date is not None
            assert task.created_timestamp is not None
            assert task.updated_timestamp is not None
        
        # Verify tasks are properly prioritized and scheduled
        sorted_tasks = sorted(generated_tasks, key=lambda t: (t.priority.value, t.due_date))
        assert len(sorted_tasks) == len(generated_tasks)
    
    def test_generate_tasks_with_empty_obligations(self, task_planner):
        """Test task generation with empty obligations list"""
        generated_tasks = task_planner.generate_tasks_from_obligations(
            obligations=[],
            use_ai_enhancement=False
        )
        
        assert len(generated_tasks) == 0
    
    def test_task_template_formatting(self, task_planner, sample_obligations):
        """Test task template string formatting"""
        reporting_obligation = next(obl for obl in sample_obligations if obl.category == ObligationCategory.REPORTING)
        
        # Get reporting templates
        reporting_templates = task_planner.task_templates.get('reporting', [])
        assert len(reporting_templates) > 0
        
        # Test template formatting
        template = reporting_templates[0]
        obligation_type = task_planner._extract_obligation_type(reporting_obligation.description)
        
        formatted_title = template.title_template.format(obligation_type=obligation_type)
        formatted_description = template.description_template.format(
            obligation_type=obligation_type,
            obligation_description=reporting_obligation.description[:200]
        )
        
        assert '{' not in formatted_title  # No unformatted placeholders
        assert '{' not in formatted_description  # No unformatted placeholders
        assert obligation_type in formatted_title
        assert obligation_type in formatted_description


class TestTaskPlannerPriorityAndTimeline:
    """Test priority and timeline calculation logic"""
    
    @pytest.fixture
    def task_planner(self):
        """Task planner fixture"""
        with patch('boto3.client'):
            return TaskPlanner(region_name='us-east-1')
    
    def test_severity_to_priority_mapping(self, task_planner):
        """Test mapping of obligation severity to task priority"""
        # Test all severity levels
        assert task_planner._map_severity_to_priority(ObligationSeverity.CRITICAL) == TaskPriority.HIGH
        assert task_planner._map_severity_to_priority(ObligationSeverity.HIGH) == TaskPriority.HIGH
        assert task_planner._map_severity_to_priority(ObligationSeverity.MEDIUM) == TaskPriority.MEDIUM
        assert task_planner._map_severity_to_priority(ObligationSeverity.LOW) == TaskPriority.LOW
    
    def test_priority_adjustment_by_severity(self, task_planner):
        """Test priority adjustment based on obligation severity"""
        # Critical severity should always result in HIGH priority
        assert task_planner._adjust_priority_by_severity(TaskPriority.LOW, ObligationSeverity.CRITICAL) == TaskPriority.HIGH
        assert task_planner._adjust_priority_by_severity(TaskPriority.MEDIUM, ObligationSeverity.CRITICAL) == TaskPriority.HIGH
        
        # High severity should upgrade non-HIGH priorities
        assert task_planner._adjust_priority_by_severity(TaskPriority.LOW, ObligationSeverity.HIGH) == TaskPriority.HIGH
        assert task_planner._adjust_priority_by_severity(TaskPriority.MEDIUM, ObligationSeverity.HIGH) == TaskPriority.HIGH
        assert task_planner._adjust_priority_by_severity(TaskPriority.HIGH, ObligationSeverity.HIGH) == TaskPriority.HIGH
        
        # Medium and low severity should preserve original priority
        assert task_planner._adjust_priority_by_severity(TaskPriority.MEDIUM, ObligationSeverity.MEDIUM) == TaskPriority.MEDIUM
        assert task_planner._adjust_priority_by_severity(TaskPriority.LOW, ObligationSeverity.LOW) == TaskPriority.LOW
    
    def test_due_date_calculation_by_deadline_type(self, task_planner):
        """Test due date calculation based on deadline type"""
        current_time = datetime.utcnow()
        
        # Create test obligations with different deadline types
        one_time_critical = Obligation(
            obligation_id='test_one_time',
            document_id='doc_test',
            description='One-time critical obligation',
            category=ObligationCategory.OPERATIONAL,
            severity=ObligationSeverity.CRITICAL,
            deadline_type=DeadlineType.ONE_TIME,
            applicable_entities=['test'],
            extracted_text='test',
            confidence_score=0.9,
            created_timestamp=current_time
        )
        
        one_time_low = Obligation(
            obligation_id='test_one_time_low',
            document_id='doc_test',
            description='One-time low priority obligation',
            category=ObligationCategory.OPERATIONAL,
            severity=ObligationSeverity.LOW,
            deadline_type=DeadlineType.ONE_TIME,
            applicable_entities=['test'],
            extracted_text='test',
            confidence_score=0.9,
            created_timestamp=current_time
        )
        
        recurring_obligation = Obligation(
            obligation_id='test_recurring',
            document_id='doc_test',
            description='Recurring obligation',
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.MEDIUM,
            deadline_type=DeadlineType.RECURRING,
            applicable_entities=['test'],
            extracted_text='test',
            confidence_score=0.9,
            created_timestamp=current_time
        )
        
        ongoing_obligation = Obligation(
            obligation_id='test_ongoing',
            document_id='doc_test',
            description='Ongoing obligation',
            category=ObligationCategory.MONITORING,
            severity=ObligationSeverity.MEDIUM,
            deadline_type=DeadlineType.ONGOING,
            applicable_entities=['test'],
            extracted_text='test',
            confidence_score=0.9,
            created_timestamp=current_time
        )
        
        # Test due date calculations
        one_time_critical_due = task_planner._calculate_due_date(one_time_critical)
        one_time_low_due = task_planner._calculate_due_date(one_time_low)
        recurring_due = task_planner._calculate_due_date(recurring_obligation)
        ongoing_due = task_planner._calculate_due_date(ongoing_obligation)
        
        # Verify due dates are in the future
        assert one_time_critical_due > current_time
        assert one_time_low_due > current_time
        assert recurring_due > current_time
        assert ongoing_due > current_time
        
        # Verify critical one-time obligations have shorter deadlines than low priority
        assert one_time_critical_due < one_time_low_due
        
        # Verify recurring obligations have reasonable quarterly deadlines
        recurring_days = (recurring_due - current_time).days
        assert 80 <= recurring_days <= 100  # Around 90 days
        
        # Verify ongoing obligations have longer implementation periods
        ongoing_days = (ongoing_due - current_time).days
        assert ongoing_days >= 60
    
    def test_due_date_calculation_with_template(self, task_planner):
        """Test due date calculation using task templates"""
        current_time = datetime.utcnow()
        
        test_obligation = Obligation(
            obligation_id='test_template',
            document_id='doc_test',
            description='Test obligation for template calculation',
            category=ObligationCategory.REPORTING,
            severity=ObligationSeverity.MEDIUM,
            deadline_type=DeadlineType.RECURRING,
            applicable_entities=['test'],
            extracted_text='test',
            confidence_score=0.9,
            created_timestamp=current_time
        )
        
        # Create test template
        test_template = TaskTemplate(
            title_template="Test Task",
            description_template="Test Description",
            priority=TaskPriority.MEDIUM,
            estimated_days=10
        )
        
        # Test normal calculation
        due_date_normal = task_planner._calculate_due_date_with_template(test_obligation, test_template)
        days_normal = (due_date_normal - current_time).days
        assert days_normal == 10
        
        # Test critical severity adjustment (30% faster)
        test_obligation.severity = ObligationSeverity.CRITICAL
        due_date_critical = task_planner._calculate_due_date_with_template(test_obligation, test_template)
        days_critical = (due_date_critical - current_time).days
        assert days_critical == 7  # 70% of 10 days
        
        # Test low severity adjustment (30% longer)
        test_obligation.severity = ObligationSeverity.LOW
        due_date_low = task_planner._calculate_due_date_with_template(test_obligation, test_template)
        days_low = (due_date_low - current_time).days
        assert days_low == 13  # 130% of 10 days
    
    def test_task_prioritization_and_scheduling(self, task_planner):
        """Test task prioritization and scheduling logic"""
        current_time = datetime.utcnow()
        
        # Create tasks with different priorities and due dates
        tasks = [
            Task(
                task_id='task_low_late',
                obligation_id='obl_1',
                title='Low Priority Late Task',
                description='Description',
                priority=TaskPriority.LOW,
                due_date=current_time + timedelta(days=30),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_high_early',
                obligation_id='obl_2',
                title='High Priority Early Task',
                description='Description',
                priority=TaskPriority.HIGH,
                due_date=current_time + timedelta(days=10),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_medium_middle',
                obligation_id='obl_3',
                title='Medium Priority Middle Task',
                description='Description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=20),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        # Prioritize and schedule
        prioritized_tasks = task_planner._prioritize_and_schedule_tasks(tasks)
        
        # Verify ordering (HIGH priority first, then by due date)
        assert prioritized_tasks[0].priority == TaskPriority.HIGH
        assert prioritized_tasks[0].task_id == 'task_high_early'
        
        # Verify all tasks are included
        assert len(prioritized_tasks) == 3
        
        # Verify task IDs are preserved
        task_ids = [task.task_id for task in prioritized_tasks]
        assert 'task_low_late' in task_ids
        assert 'task_high_early' in task_ids
        assert 'task_medium_middle' in task_ids


class TestTaskPlannerAIEnhancement:
    """Test AI enhancement functionality"""
    
    @pytest.fixture
    def task_planner(self):
        """Task planner fixture with mocked Bedrock client"""
        with patch('boto3.client'):
            planner = TaskPlanner(region_name='us-east-1')
            planner.bedrock_client = Mock()
            return planner
    
    @pytest.fixture
    def sample_ai_response(self):
        """Sample AI response for task enhancement"""
        return '''
        {
            "analysis": {
                "strengths": ["Good coverage of basic requirements", "Appropriate priority assignments"],
                "gaps": ["Missing dependency analysis", "No resource allocation"],
                "risks": ["Potential scheduling conflicts", "Insufficient monitoring"]
            },
            "additional_tasks": [
                {
                    "title": "Establish Compliance Monitoring Dashboard",
                    "description": "Create a centralized dashboard to monitor all compliance obligations and task progress",
                    "priority": "high",
                    "estimated_days": 14,
                    "depends_on": [],
                    "obligation_ids": ["obl_monitoring_001"]
                },
                {
                    "title": "Conduct Risk Assessment",
                    "description": "Perform comprehensive risk assessment for all identified obligations",
                    "priority": "medium",
                    "estimated_days": 7,
                    "depends_on": [],
                    "obligation_ids": ["obl_operational_001"]
                }
            ],
            "task_modifications": [
                {
                    "task_id": "existing_task_123",
                    "suggested_changes": {
                        "title": "Enhanced Task Title",
                        "description": "Enhanced task description with more detail",
                        "priority": "high",
                        "estimated_days": 10
                    }
                }
            ],
            "sequencing_recommendations": [
                {
                    "phase": "Phase 1: Foundation",
                    "tasks": ["task_1", "task_2"],
                    "duration_estimate": "2 weeks"
                }
            ]
        }
        '''
    
    @patch('boto3.client')
    def test_ai_enhancement_success(self, mock_boto_client, task_planner, sample_ai_response):
        """Test successful AI enhancement of tasks"""
        current_time = datetime.utcnow()
        
        # Create base tasks
        base_tasks = [
            Task(
                task_id='existing_task_123',
                obligation_id='obl_test',
                title='Original Task Title',
                description='Original description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=7),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        # Create sample obligations
        obligations = [
            Obligation(
                obligation_id='obl_monitoring_001',
                document_id='doc_test',
                description='Monitor compliance requirements',
                category=ObligationCategory.MONITORING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=['test'],
                extracted_text='test',
                confidence_score=0.9,
                created_timestamp=current_time
            )
        ]
        
        # Mock Bedrock response
        mock_client = Mock()
        mock_client.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': sample_ai_response}]
            }).encode()))
        }
        task_planner.bedrock_client = mock_client
        
        # Test AI enhancement
        enhanced_tasks = task_planner._enhance_tasks_with_ai(base_tasks, obligations)
        
        # Verify additional tasks were added
        assert len(enhanced_tasks) > len(base_tasks)
        
        # Verify additional tasks have correct properties
        additional_tasks = [task for task in enhanced_tasks if task.task_id != 'existing_task_123']
        assert len(additional_tasks) >= 2  # Should have added at least 2 tasks
        
        # Verify one of the additional tasks
        dashboard_task = next((task for task in additional_tasks if 'Dashboard' in task.title), None)
        assert dashboard_task is not None
        assert dashboard_task.priority == TaskPriority.HIGH
        assert dashboard_task.obligation_id == 'obl_monitoring_001'
        
        # Verify Bedrock was called
        mock_client.invoke_model.assert_called_once()
    
    def test_ai_enhancement_failure_fallback(self, task_planner):
        """Test AI enhancement failure fallback to base tasks"""
        current_time = datetime.utcnow()
        
        base_tasks = [
            Task(
                task_id='test_task',
                obligation_id='obl_test',
                title='Test Task',
                description='Test description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=7),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        obligations = []
        
        # Mock Bedrock failure
        task_planner.bedrock_client.invoke_model.side_effect = Exception("Bedrock error")
        
        # Test AI enhancement with failure
        enhanced_tasks = task_planner._enhance_tasks_with_ai(base_tasks, obligations)
        
        # Should fallback to base tasks
        assert len(enhanced_tasks) == len(base_tasks)
        assert enhanced_tasks[0].task_id == 'test_task'
    
    def test_ai_response_parsing_edge_cases(self, task_planner):
        """Test AI response parsing with various edge cases"""
        base_tasks = []
        
        # Test with malformed JSON
        malformed_response = "This is not valid JSON {invalid"
        result = task_planner._integrate_ai_suggestions(base_tasks, malformed_response)
        assert len(result) == 0
        
        # Test with empty JSON
        empty_response = "{}"
        result = task_planner._integrate_ai_suggestions(base_tasks, empty_response)
        assert len(result) == 0
        
        # Test with partial valid JSON
        partial_response = '''
        {
            "additional_tasks": [
                {
                    "title": "Valid Task",
                    "description": "Valid description",
                    "priority": "medium",
                    "estimated_days": 5
                }
            ]
        }
        '''
        result = task_planner._integrate_ai_suggestions(base_tasks, partial_response)
        assert len(result) == 1
        assert result[0].title == "Valid Task"


class TestTaskPlannerErrorHandling:
    """Test error handling and fallback scenarios"""
    
    @pytest.fixture
    def task_planner(self):
        """Task planner fixture"""
        with patch('boto3.client'):
            return TaskPlanner(region_name='us-east-1')
    
    def test_bedrock_initialization_failure(self):
        """Test handling of Bedrock client initialization failure"""
        with patch('boto3.client') as mock_boto_client:
            mock_boto_client.side_effect = Exception("AWS credentials not found")
            
            with pytest.raises(TaskPlannerError, match="Failed to initialize Bedrock client"):
                TaskPlanner(region_name='us-east-1')
    
    def test_task_generation_with_invalid_obligations(self, task_planner):
        """Test task generation with invalid obligation data"""
        # Test with None obligations - should handle gracefully and return empty list
        result = task_planner.generate_tasks_from_obligations(None, use_ai_enhancement=False)
        assert result == []
    
    def test_bedrock_api_error_handling(self, task_planner):
        """Test Bedrock API error handling during task enhancement"""
        from botocore.exceptions import ClientError
        
        current_time = datetime.utcnow()
        base_tasks = [
            Task(
                task_id='test_task_12345',  # Make it longer to satisfy validation
                obligation_id='obl_test_12345',
                title='Test Task',
                description='Test description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=7),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        obligations = [
            Obligation(
                obligation_id='obl_test_12345',  # Make it longer to satisfy validation
                document_id='doc_test',
                description='Test obligation',
                category=ObligationCategory.OPERATIONAL,
                severity=ObligationSeverity.MEDIUM,
                deadline_type=DeadlineType.ONE_TIME,
                applicable_entities=['test'],
                extracted_text='test',
                confidence_score=0.9,
                created_timestamp=current_time
            )
        ]
        
        # Mock Bedrock client with error
        mock_client = Mock()
        throttling_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='InvokeModel'
        )
        mock_client.invoke_model.side_effect = throttling_error
        task_planner.bedrock_client = mock_client
        
        # Should fallback to base tasks without raising exception
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = task_planner._enhance_tasks_with_ai(base_tasks, obligations)
        
        # Should return base tasks as fallback
        assert len(result) == len(base_tasks)
        assert result[0].task_id == 'test_task_12345'
    
    def test_task_generation_error_propagation(self, task_planner):
        """Test error propagation in task generation"""
        # Create a non-empty obligations list to trigger the actual generation path
        current_time = datetime.utcnow()
        test_obligations = [
            Obligation(
                obligation_id='obl_error_test',
                document_id='doc_test',
                description='Test obligation for error',
                category=ObligationCategory.OPERATIONAL,
                severity=ObligationSeverity.MEDIUM,
                deadline_type=DeadlineType.ONE_TIME,
                applicable_entities=['test'],
                extracted_text='test',
                confidence_score=0.9,
                created_timestamp=current_time
            )
        ]
        
        # Mock _generate_base_tasks to raise an exception
        with patch.object(task_planner, '_generate_base_tasks') as mock_generate:
            mock_generate.side_effect = Exception("Base task generation failed")
            
            with pytest.raises(TaskPlannerError, match="Task generation failed"):
                task_planner.generate_tasks_from_obligations(test_obligations, use_ai_enhancement=False)


class TestTaskPlannerUtilityMethods:
    """Test utility methods and helper functions"""
    
    @pytest.fixture
    def task_planner(self):
        """Task planner fixture"""
        with patch('boto3.client'):
            return TaskPlanner(region_name='us-east-1')
    
    def test_extract_obligation_type(self, task_planner):
        """Test obligation type extraction from descriptions"""
        # Test with reporting keywords
        reporting_desc = "Submit quarterly compliance reports to regulatory authority"
        assert task_planner._extract_obligation_type(reporting_desc) == "Report"
        
        # Test with monitoring keywords
        monitoring_desc = "Monitor grid stability parameters continuously"
        assert task_planner._extract_obligation_type(monitoring_desc) == "Monitoring"
        
        # Test with operational keywords
        operational_desc = "Implement emergency shutdown procedures"
        assert task_planner._extract_obligation_type(operational_desc) == "Operational"
        
        # Test with financial keywords
        financial_desc = "Maintain financial reserves for operational continuity"
        assert task_planner._extract_obligation_type(financial_desc) == "Financial"
        
        # Test with no matching keywords
        generic_desc = "Some generic compliance requirement"
        assert task_planner._extract_obligation_type(generic_desc) == "Compliance"
    
    def test_task_statistics_generation(self, task_planner):
        """Test task statistics generation"""
        current_time = datetime.utcnow()
        
        tasks = [
            Task(
                task_id='task_1',
                obligation_id='obl_1',
                title='High Priority Task',
                description='Description',
                priority=TaskPriority.HIGH,
                due_date=current_time + timedelta(days=10),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_2',
                obligation_id='obl_2',
                title='Medium Priority Task',
                description='Description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=20),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_3',
                obligation_id='obl_3',
                title='Low Priority Task',
                description='Description',
                priority=TaskPriority.LOW,
                due_date=current_time + timedelta(days=30),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        stats = task_planner.get_task_statistics(tasks)
        
        # Verify statistics structure
        assert 'total_tasks' in stats
        assert 'priority_distribution' in stats
        assert 'average_days_to_due' in stats
        assert 'tasks_with_due_dates' in stats
        assert 'earliest_due_date' in stats
        assert 'latest_due_date' in stats
        
        # Verify statistics values
        assert stats['total_tasks'] == 3
        assert stats['priority_distribution']['high'] == 1
        assert stats['priority_distribution']['medium'] == 1
        assert stats['priority_distribution']['low'] == 1
        assert stats['tasks_with_due_dates'] == 3
        assert stats['average_days_to_due'] == 20.0  # (10 + 20 + 30) / 3
        
        # Verify earliest and latest due dates
        assert stats['earliest_due_date'] == current_time + timedelta(days=10)
        assert stats['latest_due_date'] == current_time + timedelta(days=30)
    
    def test_task_statistics_with_empty_list(self, task_planner):
        """Test task statistics with empty task list"""
        stats = task_planner.get_task_statistics([])
        assert stats == {}
    
    def test_task_dependencies_analysis(self, task_planner):
        """Test task dependency analysis"""
        current_time = datetime.utcnow()
        
        # Create tasks for the same obligation
        tasks = [
            Task(
                task_id='task_1',
                obligation_id='obl_same',
                title='First Task',
                description='Description',
                priority=TaskPriority.HIGH,
                due_date=current_time + timedelta(days=5),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_2',
                obligation_id='obl_same',
                title='Second Task',
                description='Description',
                priority=TaskPriority.MEDIUM,
                due_date=current_time + timedelta(days=10),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ),
            Task(
                task_id='task_3',
                obligation_id='obl_different',
                title='Different Obligation Task',
                description='Description',
                priority=TaskPriority.LOW,
                due_date=current_time + timedelta(days=15),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            )
        ]
        
        dependencies = task_planner.analyze_task_dependencies(tasks)
        
        # Verify dependency structure
        assert 'task_1' in dependencies
        assert 'task_2' in dependencies
        assert 'task_3' in dependencies
        
        # Verify dependencies within same obligation
        assert len(dependencies['task_1']) == 0  # First task has no dependencies
        assert len(dependencies['task_2']) == 1  # Second task depends on first
        assert dependencies['task_2'][0] == 'task_1'
        
        # Verify task from different obligation has no dependencies
        assert len(dependencies['task_3']) == 0


class TestPlannerHandlerIntegration:
    """Test Planner Agent Lambda handler integration"""
    
    @pytest.fixture
    def sample_sqs_event(self):
        """Sample SQS event for planner handler testing"""
        return {
            'Records': [
                {
                    'body': json.dumps({
                        'document_id': 'doc_planner_test123',
                        'stage': 'analysis_completed',
                        'obligation_count': 5,
                        'timestamp': datetime.utcnow().isoformat(),
                        'source': 'analyzer_agent'
                    })
                }
            ]
        }
    
    @patch.dict(os.environ, {
        'REPORTER_QUEUE_URL': 'https://sqs.test.com/reporter',
        'NOTIFICATION_TOPIC_ARN': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.TaskPlanner')
    @patch('boto3.client')
    def test_lambda_handler_success(
        self, mock_boto3_client, mock_task_planner_class, mock_db_helper, sample_sqs_event
    ):
        """Test successful planner lambda handler execution"""
        current_time = datetime.utcnow()
        
        # Setup database mock
        mock_db = Mock()
        mock_db.list_obligations_by_document.return_value = [
            Obligation(
                obligation_id='obl_handler_test',
                document_id='doc_planner_test123',
                description='Test obligation for handler',
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=['test'],
                extracted_text='test',
                confidence_score=0.9,
                created_timestamp=current_time
            )
        ]
        mock_db.batch_create_tasks.return_value = 3  # 3 tasks created successfully
        mock_db.get_processing_status.return_value = []
        mock_db.create_processing_status.return_value = True
        mock_db.update_processing_status.return_value = True
        mock_db_helper.return_value = mock_db
        
        # Setup task planner mock
        mock_task_planner = Mock()
        generated_tasks = [
            Task(
                task_id=f'task_handler_{i}',
                obligation_id='obl_handler_test',
                title=f'Handler Test Task {i}',
                description=f'Description {i}',
                priority=TaskPriority.HIGH,
                due_date=current_time + timedelta(days=7),
                status=TaskStatus.PENDING,
                created_timestamp=current_time,
                updated_timestamp=current_time
            ) for i in range(3)
        ]
        mock_task_planner.generate_tasks_from_obligations.return_value = generated_tasks
        mock_task_planner.get_task_statistics.return_value = {
            'total_tasks': 3,
            'priority_distribution': {'high': 3}
        }
        mock_task_planner_class.return_value = mock_task_planner
        
        # Setup SQS mock
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {'MessageId': 'test_msg'}
        mock_boto3_client.return_value = mock_sqs
        
        # Execute handler
        result = lambda_handler(sample_sqs_event, {})
        
        # Verify success response
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_records'] == 1
        assert response_body['failed_records'] == 0
        assert response_body['total_tasks_generated'] == 3
        
        # Verify database interactions
        mock_db.list_obligations_by_document.assert_called_once_with('doc_planner_test123')
        mock_db.batch_create_tasks.assert_called_once()
        
        # Verify task generation
        mock_task_planner.generate_tasks_from_obligations.assert_called_once()
        
        # Verify message sent to reporter queue
        mock_sqs.send_message.assert_called_once()
    
    @patch.dict(os.environ, {
        'REPORTER_QUEUE_URL': 'https://sqs.test.com/reporter',
        'NOTIFICATION_TOPIC_ARN': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.TaskPlanner')
    def test_lambda_handler_no_obligations(self, mock_task_planner_class, mock_db_helper, sample_sqs_event):
        """Test handler with no obligations found"""
        # Setup database mock with no obligations
        mock_db = Mock()
        mock_db.list_obligations_by_document.return_value = []
        mock_db.get_processing_status.return_value = []
        mock_db.create_processing_status.return_value = True
        mock_db.update_processing_status.return_value = True
        mock_db_helper.return_value = mock_db
        
        # Setup task planner mock
        mock_task_planner = Mock()
        mock_task_planner_class.return_value = mock_task_planner
        
        # Execute handler
        result = lambda_handler(sample_sqs_event, {})
        
        # Verify success response with no tasks generated
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_records'] == 1
        assert response_body['failed_records'] == 0
        assert response_body['total_tasks_generated'] == 0
        
        # Verify obligations were queried but no task generation occurred
        mock_db.list_obligations_by_document.assert_called_once()
        mock_task_planner.generate_tasks_from_obligations.assert_not_called()
    
    @patch.dict(os.environ, {
        'REPORTER_QUEUE_URL': 'https://sqs.test.com/reporter',
        'NOTIFICATION_TOPIC_ARN': 'arn:aws:sns:test:topic'
    })
    @patch('handler.get_db_helper')
    @patch('handler.TaskPlanner')
    def test_lambda_handler_task_generation_failure(
        self, mock_task_planner_class, mock_db_helper, sample_sqs_event
    ):
        """Test handler with task generation failure"""
        current_time = datetime.utcnow()
        
        # Setup database mock
        mock_db = Mock()
        mock_db.list_obligations_by_document.return_value = [
            Obligation(
                obligation_id='obl_failure_test',
                document_id='doc_planner_test123',
                description='Test obligation',
                category=ObligationCategory.OPERATIONAL,
                severity=ObligationSeverity.MEDIUM,
                deadline_type=DeadlineType.ONE_TIME,
                applicable_entities=['test'],
                extracted_text='test',
                confidence_score=0.9,
                created_timestamp=current_time
            )
        ]
        mock_db.get_processing_status.return_value = []
        mock_db.create_processing_status.return_value = True
        mock_db.update_processing_status.return_value = True
        mock_db_helper.return_value = mock_db
        
        # Setup task planner mock to fail
        mock_task_planner = Mock()
        mock_task_planner.generate_tasks_from_obligations.side_effect = TaskPlannerError("Task generation failed")
        mock_task_planner_class.return_value = mock_task_planner
        
        # Execute handler
        result = lambda_handler(sample_sqs_event, {})
        
        # Verify failure is handled gracefully
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_records'] == 0
        assert response_body['failed_records'] == 1
        assert response_body['total_tasks_generated'] == 0
        
        # Verify error status was updated
        mock_db.update_processing_status.assert_called()
    
    def test_process_document_for_task_planning_success(self):
        """Test successful document processing for task planning"""
        current_time = datetime.utcnow()
        
        with patch('handler.get_db_helper') as mock_db_helper, \
             patch('handler.TaskPlanner') as mock_task_planner_class:
            
            # Setup mocks
            mock_db = Mock()
            mock_db.list_obligations_by_document.return_value = [
                Obligation(
                    obligation_id='obl_process_test',
                    document_id='doc_process_test',
                    description='Process test obligation',
                    category=ObligationCategory.MONITORING,
                    severity=ObligationSeverity.HIGH,
                    deadline_type=DeadlineType.ONGOING,
                    applicable_entities=['test'],
                    extracted_text='test',
                    confidence_score=0.9,
                    created_timestamp=current_time
                )
            ]
            mock_db.batch_create_tasks.return_value = 2
            mock_db_helper.return_value = mock_db
            
            mock_task_planner = Mock()
            mock_task_planner.generate_tasks_from_obligations.return_value = [
                Task(
                    task_id='task_process_1',
                    obligation_id='obl_process_test',
                    title='Process Test Task 1',
                    description='Description 1',
                    priority=TaskPriority.HIGH,
                    due_date=current_time + timedelta(days=7),
                    status=TaskStatus.PENDING,
                    created_timestamp=current_time,
                    updated_timestamp=current_time
                ),
                Task(
                    task_id='task_process_2',
                    obligation_id='obl_process_test',
                    title='Process Test Task 2',
                    description='Description 2',
                    priority=TaskPriority.MEDIUM,
                    due_date=current_time + timedelta(days=14),
                    status=TaskStatus.PENDING,
                    created_timestamp=current_time,
                    updated_timestamp=current_time
                )
            ]
            mock_task_planner.get_task_statistics.return_value = {'total_tasks': 2}
            mock_task_planner_class.return_value = mock_task_planner
            
            # Execute
            with patch.dict(os.environ, {'USE_AI_ENHANCEMENT': 'true'}):
                result = process_document_for_task_planning('doc_process_test')
            
            # Verify
            assert result == 2  # 2 tasks generated successfully
            mock_db.list_obligations_by_document.assert_called_once_with('doc_process_test')
            mock_task_planner.generate_tasks_from_obligations.assert_called_once()
            mock_db.batch_create_tasks.assert_called_once()