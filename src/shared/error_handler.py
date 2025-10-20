"""
Comprehensive Error Handling Module for EnergyGrid.AI Compliance Copilot
Implements retry logic, circuit breaker patterns, and error categorization
"""

import time
import random
import logging
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
from enum import Enum
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import json

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification and handling"""
    TRANSIENT = "transient"  # Temporary errors that can be retried
    PERMANENT = "permanent"  # Permanent errors that should not be retried
    THROTTLING = "throttling"  # Rate limiting errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    VALIDATION = "validation"  # Input validation errors
    RESOURCE_NOT_FOUND = "resource_not_found"  # Missing resources
    SERVICE_UNAVAILABLE = "service_unavailable"  # Service outages
    TIMEOUT = "timeout"  # Timeout errors
    UNKNOWN = "unknown"  # Unclassified errors


class RetryableError(Exception):
    """Exception that can be retried"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.TRANSIENT, retry_after: Optional[int] = None):
        self.message = message
        self.category = category
        self.retry_after = retry_after
        super().__init__(self.message)


class NonRetryableError(Exception):
    """Exception that should not be retried"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.PERMANENT):
        self.message = message
        self.category = category
        super().__init__(self.message)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker is open for service: {service_name}")


class ErrorClassifier:
    """Classifies errors into categories for appropriate handling"""
    
    @staticmethod
    def classify_aws_error(error: ClientError) -> ErrorCategory:
        """Classify AWS ClientError into appropriate category"""
        error_code = error.response.get('Error', {}).get('Code', '')
        
        # Throttling errors
        if error_code in ['ThrottlingException', 'TooManyRequestsException', 'RequestLimitExceeded', 'Throttling']:
            return ErrorCategory.THROTTLING
        
        # Authentication/Authorization errors
        if error_code in ['UnauthorizedOperation', 'AccessDenied', 'InvalidUserID.NotFound', 'TokenRefreshRequired']:
            return ErrorCategory.AUTHENTICATION
        
        # Resource not found errors
        if error_code in ['NoSuchKey', 'ResourceNotFoundException', 'NoSuchBucket', 'ItemNotFound']:
            return ErrorCategory.RESOURCE_NOT_FOUND
        
        # Validation errors
        if error_code in ['ValidationException', 'InvalidParameterValue', 'MalformedPolicyDocument']:
            return ErrorCategory.VALIDATION
        
        # Service unavailable errors
        if error_code in ['ServiceUnavailable', 'InternalError', 'ServiceException']:
            return ErrorCategory.SERVICE_UNAVAILABLE
        
        # Transient errors that can be retried
        if error_code in ['InternalServerError', 'RequestTimeout', 'ServiceFailure']:
            return ErrorCategory.TRANSIENT
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def classify_bedrock_error(error: ClientError) -> ErrorCategory:
        """Classify Bedrock-specific errors"""
        error_code = error.response.get('Error', {}).get('Code', '')
        
        if error_code == 'ThrottlingException':
            return ErrorCategory.THROTTLING
        elif error_code == 'ValidationException':
            return ErrorCategory.VALIDATION
        elif error_code == 'ModelNotReadyException':
            return ErrorCategory.SERVICE_UNAVAILABLE
        elif error_code == 'InternalServerException':
            return ErrorCategory.TRANSIENT
        elif error_code == 'AccessDeniedException':
            return ErrorCategory.AUTHENTICATION
        
        return ErrorClassifier.classify_aws_error(error)
    
    @staticmethod
    def is_retryable(category: ErrorCategory) -> bool:
        """Determine if an error category is retryable"""
        retryable_categories = {
            ErrorCategory.TRANSIENT,
            ErrorCategory.THROTTLING,
            ErrorCategory.SERVICE_UNAVAILABLE,
            ErrorCategory.TIMEOUT
        }
        return category in retryable_categories


class ExponentialBackoff:
    """Implements exponential backoff with jitter"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, multiplier: float = 2.0, jitter: bool = True):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = min(self.base_delay * (self.multiplier ** attempt), self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerError(func.__name__)
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, backoff: Optional[ExponentialBackoff] = None):
        self.max_attempts = max_attempts
        self.backoff = backoff or ExponentialBackoff()
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Classify error
                if isinstance(e, ClientError):
                    category = ErrorClassifier.classify_aws_error(e)
                elif isinstance(e, (RetryableError, NonRetryableError)):
                    category = e.category
                else:
                    category = ErrorCategory.UNKNOWN
                
                # Check if error is retryable
                if not ErrorClassifier.is_retryable(category) or attempt == self.max_attempts - 1:
                    logger.error(f"Non-retryable error or max attempts reached: {e}")
                    raise e
                
                # Calculate delay
                delay = self.backoff.calculate_delay(attempt)
                
                # Handle throttling with custom delay
                if category == ErrorCategory.THROTTLING and hasattr(e, 'retry_after'):
                    delay = max(delay, e.retry_after)
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        raise last_exception


# Global circuit breakers for different services
_circuit_breakers = {}

def get_circuit_breaker(service_name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker for service"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(**kwargs)
    return _circuit_breakers[service_name]


def with_retry(max_attempts: int = 3, backoff: Optional[ExponentialBackoff] = None):
    """Decorator for adding retry logic to functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_attempts, backoff)
            return retry_handler.retry(func, *args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(service_name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
    """Decorator for adding circuit breaker protection to functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit_breaker = get_circuit_breaker(
                service_name, 
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def handle_aws_error(error: ClientError, context: str = "") -> None:
    """Handle AWS errors with appropriate logging and classification"""
    category = ErrorClassifier.classify_aws_error(error)
    error_code = error.response.get('Error', {}).get('Code', 'Unknown')
    error_message = error.response.get('Error', {}).get('Message', str(error))
    
    log_message = f"AWS Error in {context}: {error_code} - {error_message}"
    
    if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.VALIDATION]:
        logger.error(log_message)
        raise NonRetryableError(error_message, category)
    elif category == ErrorCategory.THROTTLING:
        retry_after = error.response.get('Error', {}).get('RetryAfterSeconds', 1)
        logger.warning(f"{log_message} (retry after {retry_after}s)")
        raise RetryableError(error_message, category, retry_after)
    elif ErrorClassifier.is_retryable(category):
        logger.warning(log_message)
        raise RetryableError(error_message, category)
    else:
        logger.error(log_message)
        raise NonRetryableError(error_message, category)


def send_to_dead_letter_queue(message: Dict[str, Any], queue_url: str, error: Exception, context: str = ""):
    """Send failed message to dead letter queue"""
    try:
        sqs = boto3.client('sqs')
        
        # Add error information to message
        dlq_message = {
            'original_message': message,
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'category': getattr(error, 'category', ErrorCategory.UNKNOWN).value if hasattr(error, 'category') else ErrorCategory.UNKNOWN.value,
                'timestamp': datetime.utcnow().isoformat(),
                'context': context
            },
            'retry_count': message.get('retry_count', 0) + 1
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(dlq_message),
            MessageAttributes={
                'error_type': {
                    'StringValue': type(error).__name__,
                    'DataType': 'String'
                },
                'error_category': {
                    'StringValue': getattr(error, 'category', ErrorCategory.UNKNOWN).value if hasattr(error, 'category') else ErrorCategory.UNKNOWN.value,
                    'DataType': 'String'
                },
                'context': {
                    'StringValue': context,
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Sent message to dead letter queue: {queue_url}")
        
    except Exception as dlq_error:
        logger.error(f"Failed to send message to dead letter queue: {dlq_error}")


class ErrorMetrics:
    """Collect and publish error metrics"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    def record_error(self, service_name: str, error_type: str, error_category: str):
        """Record error metric in CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='EnergyGrid/Errors',
                MetricData=[
                    {
                        'MetricName': 'ErrorCount',
                        'Dimensions': [
                            {
                                'Name': 'Service',
                                'Value': service_name
                            },
                            {
                                'Name': 'ErrorType',
                                'Value': error_type
                            },
                            {
                                'Name': 'ErrorCategory',
                                'Value': error_category
                            }
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")
    
    def record_retry_attempt(self, service_name: str, attempt_number: int):
        """Record retry attempt metric"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='EnergyGrid/Retries',
                MetricData=[
                    {
                        'MetricName': 'RetryAttempt',
                        'Dimensions': [
                            {
                                'Name': 'Service',
                                'Value': service_name
                            }
                        ],
                        'Value': attempt_number,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to record retry metric: {e}")


# Global error metrics instance
error_metrics = ErrorMetrics()


def log_and_metric_error(error: Exception, service_name: str, context: str = ""):
    """Log error and record metrics"""
    error_type = type(error).__name__
    error_category = getattr(error, 'category', ErrorCategory.UNKNOWN).value if hasattr(error, 'category') else ErrorCategory.UNKNOWN.value
    
    logger.error(f"Error in {service_name} ({context}): {error_type} - {error}")
    error_metrics.record_error(service_name, error_type, error_category)