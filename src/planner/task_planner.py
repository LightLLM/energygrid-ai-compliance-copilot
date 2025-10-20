"""
Task Planning Logic Module
Analyzes obligations for audit requirements and generates prioritized task lists
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.shared.models import (
    Obligation, Task, TaskPriority, TaskStatus, 
    ObligationCategory, ObligationSeverity, DeadlineType
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TaskPlannerError(Exception):
    """Custom exception for task planning errors"""
    pass


@dataclass
class TaskTemplate:
    """Template for generating tasks based on obligation characteristics"""
    title_template: str
    description_template: str
    priority: TaskPriority
    estimated_days: int
    category_specific: bool = False


class TaskPlanner:
    """
    Task planning logic for generating audit tasks from compliance obligations
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize task planner
        
        Args:
            region_name: AWS region for Bedrock service
        """
        self.region_name = region_name
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        self.bedrock_client = None
        self.max_tokens = 4096
        self.temperature = 0.2  # Slightly higher for creative task planning
        self.top_p = 0.9
        
        # Task templates for different obligation types
        self.task_templates = self._initialize_task_templates()
        
        self._initialize_bedrock_client()
    
    def _initialize_bedrock_client(self):
        """Initialize Bedrock runtime client"""
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name
            )
            logger.info(f"Bedrock client initialized for task planning in region {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise TaskPlannerError(f"Failed to initialize Bedrock client: {e}")
    
    def _initialize_task_templates(self) -> Dict[str, List[TaskTemplate]]:
        """Initialize task templates for different obligation categories"""
        return {
            'reporting': [
                TaskTemplate(
                    title_template="Prepare {obligation_type} Report",
                    description_template="Collect data and prepare the required {obligation_type} report as specified in the obligation: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=7
                ),
                TaskTemplate(
                    title_template="Review {obligation_type} Report Requirements",
                    description_template="Review and validate all requirements for {obligation_type} reporting to ensure compliance with: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=3
                ),
                TaskTemplate(
                    title_template="Submit {obligation_type} Report",
                    description_template="Submit the completed {obligation_type} report to the appropriate regulatory authority as required by: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=1
                )
            ],
            'monitoring': [
                TaskTemplate(
                    title_template="Establish {obligation_type} Monitoring System",
                    description_template="Set up monitoring systems and procedures to track compliance with: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=14
                ),
                TaskTemplate(
                    title_template="Conduct {obligation_type} Monitoring Review",
                    description_template="Review current monitoring practices and ensure they meet the requirements of: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=5
                ),
                TaskTemplate(
                    title_template="Update {obligation_type} Monitoring Procedures",
                    description_template="Update monitoring procedures and documentation to ensure ongoing compliance with: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=3
                )
            ],
            'operational': [
                TaskTemplate(
                    title_template="Implement {obligation_type} Operational Changes",
                    description_template="Implement necessary operational changes to comply with: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=21
                ),
                TaskTemplate(
                    title_template="Train Staff on {obligation_type} Requirements",
                    description_template="Provide training to relevant staff on new operational requirements: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=7
                ),
                TaskTemplate(
                    title_template="Audit {obligation_type} Operational Compliance",
                    description_template="Conduct internal audit to verify compliance with operational requirements: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=5
                )
            ],
            'financial': [
                TaskTemplate(
                    title_template="Calculate {obligation_type} Financial Requirements",
                    description_template="Calculate and prepare financial requirements for compliance with: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=10
                ),
                TaskTemplate(
                    title_template="Review {obligation_type} Financial Impact",
                    description_template="Review and assess the financial impact of compliance requirements: {obligation_description}",
                    priority=TaskPriority.MEDIUM,
                    estimated_days=5
                ),
                TaskTemplate(
                    title_template="Process {obligation_type} Financial Obligations",
                    description_template="Process payments, fees, or other financial obligations as required by: {obligation_description}",
                    priority=TaskPriority.HIGH,
                    estimated_days=3
                )
            ]
        }
    
    def generate_tasks_from_obligations(
        self, 
        obligations: List[Obligation],
        use_ai_enhancement: bool = True
    ) -> List[Task]:
        """
        Generate prioritized task lists from compliance obligations
        
        Args:
            obligations: List of obligations to process
            use_ai_enhancement: Whether to use Claude Sonnet for enhanced task planning
            
        Returns:
            List of generated Task objects
            
        Raises:
            TaskPlannerError: If task generation fails
        """
        # Handle None obligations gracefully
        if obligations is None:
            logger.warning("None obligations provided for task generation")
            return []
            
        logger.info(f"Starting task generation for {len(obligations)} obligations")
        
        if not obligations:
            logger.warning("No obligations provided for task generation")
            return []
        
        try:
            # Generate base tasks using templates
            base_tasks = self._generate_base_tasks(obligations)
            
            # Enhance tasks with AI if requested
            if use_ai_enhancement and self.bedrock_client:
                enhanced_tasks = self._enhance_tasks_with_ai(base_tasks, obligations)
                final_tasks = enhanced_tasks
            else:
                final_tasks = base_tasks
            
            # Prioritize and schedule tasks
            prioritized_tasks = self._prioritize_and_schedule_tasks(final_tasks)
            
            logger.info(f"Successfully generated {len(prioritized_tasks)} tasks")
            return prioritized_tasks
            
        except Exception as e:
            logger.error(f"Failed to generate tasks from obligations: {e}")
            raise TaskPlannerError(f"Task generation failed: {e}")
    
    def _generate_base_tasks(self, obligations: List[Obligation]) -> List[Task]:
        """
        Generate base tasks using predefined templates
        
        Args:
            obligations: List of obligations to process
            
        Returns:
            List of base Task objects
        """
        base_tasks = []
        current_time = datetime.utcnow()
        
        for obligation in obligations:
            category_key = obligation.category.value
            templates = self.task_templates.get(category_key, [])
            
            if not templates:
                # Create a generic task if no templates available
                task = Task(
                    task_id=Task.generate_id(),
                    obligation_id=obligation.obligation_id,
                    title=f"Address {obligation.category.value.title()} Obligation",
                    description=f"Address the compliance obligation: {obligation.description}",
                    priority=self._map_severity_to_priority(obligation.severity),
                    due_date=self._calculate_due_date(obligation),
                    status=TaskStatus.PENDING,
                    created_timestamp=current_time,
                    updated_timestamp=current_time
                )
                base_tasks.append(task)
                continue
            
            # Generate tasks from templates
            for template in templates:
                # Format template strings
                obligation_type = self._extract_obligation_type(obligation.description)
                
                title = template.title_template.format(
                    obligation_type=obligation_type
                )
                
                description = template.description_template.format(
                    obligation_type=obligation_type,
                    obligation_description=obligation.description[:200] + "..." if len(obligation.description) > 200 else obligation.description
                )
                
                # Calculate due date based on template and obligation
                due_date = self._calculate_due_date_with_template(obligation, template)
                
                task = Task(
                    task_id=Task.generate_id(),
                    obligation_id=obligation.obligation_id,
                    title=title,
                    description=description,
                    priority=self._adjust_priority_by_severity(template.priority, obligation.severity),
                    due_date=due_date,
                    status=TaskStatus.PENDING,
                    created_timestamp=current_time,
                    updated_timestamp=current_time
                )
                
                base_tasks.append(task)
        
        return base_tasks
    
    def _enhance_tasks_with_ai(
        self, 
        base_tasks: List[Task], 
        obligations: List[Obligation]
    ) -> List[Task]:
        """
        Enhance tasks using Claude Sonnet for intelligent task planning
        
        Args:
            base_tasks: Base tasks generated from templates
            obligations: Original obligations for context
            
        Returns:
            Enhanced list of Task objects
        """
        logger.info("Enhancing tasks with AI-powered planning")
        
        try:
            # Prepare context for Claude
            context = self._prepare_ai_context(base_tasks, obligations)
            
            # Build prompt for task enhancement
            prompt = self._build_task_enhancement_prompt(context)
            
            # Call Claude Sonnet
            response = self._call_claude_with_retry(prompt)
            
            # Parse and integrate AI suggestions
            enhanced_tasks = self._integrate_ai_suggestions(base_tasks, response)
            
            return enhanced_tasks
            
        except Exception as e:
            logger.warning(f"AI enhancement failed, using base tasks: {e}")
            return base_tasks
    
    def _prepare_ai_context(
        self, 
        base_tasks: List[Task], 
        obligations: List[Obligation]
    ) -> Dict[str, Any]:
        """Prepare context information for AI enhancement"""
        return {
            'obligations_summary': [
                {
                    'id': obl.obligation_id,
                    'description': obl.description,
                    'category': obl.category.value,
                    'severity': obl.severity.value,
                    'deadline_type': obl.deadline_type.value
                }
                for obl in obligations
            ],
            'base_tasks_summary': [
                {
                    'id': task.task_id,
                    'obligation_id': task.obligation_id,
                    'title': task.title,
                    'description': task.description,
                    'priority': task.priority.value,
                    'due_date': task.due_date.isoformat() if task.due_date else None
                }
                for task in base_tasks
            ]
        }
    
    def _build_task_enhancement_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Claude Sonnet task enhancement"""
        prompt = f"""You are an expert compliance task planner for energy sector organizations. Your role is to analyze compliance obligations and enhance the generated task plan to ensure comprehensive audit readiness.

CONTEXT:
You have been provided with compliance obligations and a preliminary task plan. Your job is to:
1. Review the existing tasks for completeness and effectiveness
2. Suggest additional tasks that might be needed
3. Recommend task dependencies and optimal sequencing
4. Identify potential risks or gaps in the current plan
5. Suggest resource allocation and timeline optimizations

OBLIGATIONS TO ADDRESS:
{json.dumps(context['obligations_summary'], indent=2)}

CURRENT TASK PLAN:
{json.dumps(context['base_tasks_summary'], indent=2)}

ENHANCEMENT REQUIREMENTS:
Please provide your analysis and recommendations in the following JSON format:

{{
    "analysis": {{
        "strengths": ["List of strengths in current plan"],
        "gaps": ["List of identified gaps or missing tasks"],
        "risks": ["List of potential compliance risks"]
    }},
    "additional_tasks": [
        {{
            "title": "Task title",
            "description": "Detailed task description",
            "priority": "high|medium|low",
            "estimated_days": 5,
            "depends_on": ["task_id_1", "task_id_2"],
            "obligation_ids": ["obligation_id_1"]
        }}
    ],
    "task_modifications": [
        {{
            "task_id": "existing_task_id",
            "suggested_changes": {{
                "title": "New title if needed",
                "description": "Enhanced description",
                "priority": "adjusted_priority",
                "estimated_days": 7
            }}
        }}
    ],
    "sequencing_recommendations": [
        {{
            "phase": "Phase 1: Preparation",
            "tasks": ["task_id_1", "task_id_2"],
            "duration_estimate": "2 weeks"
        }}
    ]
}}

Focus on practical, actionable recommendations that will improve compliance outcomes and audit readiness. Consider the energy sector's regulatory environment and typical audit requirements."""

        return prompt
    
    def _call_claude_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> str:
        """Call Claude Sonnet with retry logic (similar to analyzer)"""
        for attempt in range(max_retries + 1):
            try:
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                
                if 'content' in response_body and response_body['content']:
                    content = response_body['content'][0]['text']
                    logger.info(f"Successfully received task planning response from Claude (attempt {attempt + 1})")
                    return content
                else:
                    raise TaskPlannerError("Empty response from Claude Sonnet")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ThrottlingException' and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Throttling detected, retrying in {delay} seconds")
                    import time
                    time.sleep(delay)
                    continue
                else:
                    raise TaskPlannerError(f"Bedrock API error: {e}")
            
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Error calling Claude, retrying in {delay} seconds: {e}")
                    import time
                    time.sleep(delay)
                    continue
                else:
                    raise TaskPlannerError(f"Failed to call Claude after {max_retries} retries: {e}")
        
        raise TaskPlannerError(f"Failed to get response from Claude after {max_retries} retries")
    
    def _integrate_ai_suggestions(self, base_tasks: List[Task], ai_response: str) -> List[Task]:
        """Integrate AI suggestions into the task list"""
        try:
            # Extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No valid JSON found in AI response, using base tasks")
                return base_tasks
            
            json_text = ai_response[json_start:json_end]
            suggestions = json.loads(json_text)
            
            enhanced_tasks = base_tasks.copy()
            current_time = datetime.utcnow()
            
            # Add additional tasks suggested by AI
            if 'additional_tasks' in suggestions:
                for task_suggestion in suggestions['additional_tasks']:
                    try:
                        # Find the related obligation
                        obligation_ids = task_suggestion.get('obligation_ids', [])
                        obligation_id = obligation_ids[0] if obligation_ids else base_tasks[0].obligation_id
                        
                        additional_task = Task(
                            task_id=Task.generate_id(),
                            obligation_id=obligation_id,
                            title=task_suggestion['title'],
                            description=task_suggestion['description'],
                            priority=TaskPriority(task_suggestion.get('priority', 'medium')),
                            due_date=self._calculate_due_date_from_days(
                                task_suggestion.get('estimated_days', 7)
                            ),
                            status=TaskStatus.PENDING,
                            created_timestamp=current_time,
                            updated_timestamp=current_time
                        )
                        
                        enhanced_tasks.append(additional_task)
                        
                    except Exception as e:
                        logger.warning(f"Failed to create additional task: {e}")
                        continue
            
            # Apply task modifications suggested by AI
            if 'task_modifications' in suggestions:
                task_dict = {task.task_id: task for task in enhanced_tasks}
                
                for modification in suggestions['task_modifications']:
                    task_id = modification.get('task_id')
                    changes = modification.get('suggested_changes', {})
                    
                    if task_id in task_dict:
                        task = task_dict[task_id]
                        
                        if 'title' in changes:
                            task.title = changes['title']
                        if 'description' in changes:
                            task.description = changes['description']
                        if 'priority' in changes:
                            try:
                                task.priority = TaskPriority(changes['priority'])
                            except ValueError:
                                pass
                        
                        task.updated_timestamp = current_time
            
            logger.info(f"AI enhancement added {len(enhanced_tasks) - len(base_tasks)} additional tasks")
            return enhanced_tasks
            
        except Exception as e:
            logger.warning(f"Failed to integrate AI suggestions: {e}")
            return base_tasks
    
    def _prioritize_and_schedule_tasks(self, tasks: List[Task]) -> List[Task]:
        """Prioritize and schedule tasks based on dependencies and deadlines"""
        # Sort tasks by priority and due date
        priority_order = {
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1
        }
        
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                priority_order.get(t.priority, 0),
                t.due_date or datetime.max,
                t.created_timestamp
            ),
            reverse=True
        )
        
        return sorted_tasks
    
    def _extract_obligation_type(self, description: str) -> str:
        """Extract a meaningful type from obligation description"""
        # Simple keyword extraction - could be enhanced with NLP
        keywords = ['report', 'monitoring', 'operational', 'financial', 'compliance', 'audit']
        
        description_lower = description.lower()
        for keyword in keywords:
            if keyword in description_lower:
                return keyword.title()
        
        return "Compliance"
    
    def _map_severity_to_priority(self, severity: ObligationSeverity) -> TaskPriority:
        """Map obligation severity to task priority"""
        severity_priority_map = {
            ObligationSeverity.CRITICAL: TaskPriority.HIGH,
            ObligationSeverity.HIGH: TaskPriority.HIGH,
            ObligationSeverity.MEDIUM: TaskPriority.MEDIUM,
            ObligationSeverity.LOW: TaskPriority.LOW
        }
        
        return severity_priority_map.get(severity, TaskPriority.MEDIUM)
    
    def _adjust_priority_by_severity(
        self, 
        base_priority: TaskPriority, 
        severity: ObligationSeverity
    ) -> TaskPriority:
        """Adjust task priority based on obligation severity"""
        if severity == ObligationSeverity.CRITICAL:
            return TaskPriority.HIGH
        elif severity == ObligationSeverity.HIGH and base_priority != TaskPriority.HIGH:
            return TaskPriority.HIGH
        else:
            return base_priority
    
    def _calculate_due_date(self, obligation: Obligation) -> Optional[datetime]:
        """Calculate due date based on obligation characteristics"""
        base_date = datetime.utcnow()
        
        if obligation.deadline_type == DeadlineType.ONE_TIME:
            # Urgent one-time obligations get shorter deadlines
            if obligation.severity in [ObligationSeverity.CRITICAL, ObligationSeverity.HIGH]:
                return base_date + timedelta(days=30)
            else:
                return base_date + timedelta(days=60)
        
        elif obligation.deadline_type == DeadlineType.RECURRING:
            # Recurring obligations get quarterly deadlines
            return base_date + timedelta(days=90)
        
        else:  # ONGOING
            # Ongoing obligations get longer implementation periods
            if obligation.severity == ObligationSeverity.CRITICAL:
                return base_date + timedelta(days=60)
            else:
                return base_date + timedelta(days=120)
    
    def _calculate_due_date_with_template(
        self, 
        obligation: Obligation, 
        template: TaskTemplate
    ) -> Optional[datetime]:
        """Calculate due date using template estimated days"""
        base_date = datetime.utcnow()
        
        # Adjust estimated days based on obligation severity
        days = template.estimated_days
        if obligation.severity == ObligationSeverity.CRITICAL:
            days = max(1, int(days * 0.7))  # 30% faster for critical
        elif obligation.severity == ObligationSeverity.LOW:
            days = int(days * 1.3)  # 30% longer for low priority
        
        return base_date + timedelta(days=days)
    
    def _calculate_due_date_from_days(self, estimated_days: int) -> Optional[datetime]:
        """Calculate due date from estimated days"""
        return datetime.utcnow() + timedelta(days=estimated_days)
    
    def analyze_task_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Analyze potential dependencies between tasks
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary mapping task IDs to lists of dependency task IDs
        """
        dependencies = {}
        
        # Group tasks by obligation
        obligation_tasks = {}
        for task in tasks:
            if task.obligation_id not in obligation_tasks:
                obligation_tasks[task.obligation_id] = []
            obligation_tasks[task.obligation_id].append(task)
        
        # Identify dependencies within obligation groups
        for obligation_id, task_group in obligation_tasks.items():
            # Sort by priority and estimated completion
            sorted_tasks = sorted(
                task_group,
                key=lambda t: (t.priority.value, t.due_date or datetime.max)
            )
            
            # Create simple sequential dependencies
            for i, task in enumerate(sorted_tasks):
                if i > 0:
                    # Task depends on previous task in sequence
                    dependencies[task.task_id] = [sorted_tasks[i-1].task_id]
                else:
                    dependencies[task.task_id] = []
        
        return dependencies
    
    def get_task_statistics(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Generate statistics about the generated tasks
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary with task statistics
        """
        if not tasks:
            return {}
        
        priority_counts = {}
        category_counts = {}
        
        for task in tasks:
            # Count by priority
            priority = task.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        total_tasks = len(tasks)
        avg_days_to_due = 0
        
        due_date_tasks = [t for t in tasks if t.due_date]
        if due_date_tasks:
            total_days = sum(
                (task.due_date - datetime.utcnow()).days 
                for task in due_date_tasks
            )
            avg_days_to_due = total_days / len(due_date_tasks)
        
        return {
            'total_tasks': total_tasks,
            'priority_distribution': priority_counts,
            'average_days_to_due': round(avg_days_to_due, 1),
            'tasks_with_due_dates': len(due_date_tasks),
            'earliest_due_date': min(
                (t.due_date for t in due_date_tasks), 
                default=None
            ),
            'latest_due_date': max(
                (t.due_date for t in due_date_tasks), 
                default=None
            )
        }


# Convenience function for simple task generation
def generate_tasks_from_obligations(
    obligations: List[Obligation],
    use_ai_enhancement: bool = True,
    region_name: str = 'us-east-1'
) -> List[Task]:
    """
    Simple function to generate tasks from obligations
    
    Args:
        obligations: List of obligations to process
        use_ai_enhancement: Whether to use AI enhancement
        region_name: AWS region for Bedrock
        
    Returns:
        List of generated Task objects
        
    Raises:
        TaskPlannerError: If task generation fails
    """
    planner = TaskPlanner(region_name=region_name)
    return planner.generate_tasks_from_obligations(obligations, use_ai_enhancement)