"""
X-Ray Tracing Module for EnergyGrid.AI Compliance Copilot
Implements distributed tracing across all Lambda functions and AWS services
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime

# Import X-Ray SDK
try:
    from aws_xray_sdk.core import xray_recorder, patch_all
    from aws_xray_sdk.core.models import subsegment
    from aws_xray_sdk.core.exceptions import SegmentNotFoundException
    XRAY_AVAILABLE = True
except ImportError:
    XRAY_AVAILABLE = False
    logging.warning("X-Ray SDK not available. Tracing will be disabled.")

logger = logging.getLogger(__name__)


class XRayTracer:
    """X-Ray tracing utilities"""
    
    def __init__(self):
        self.enabled = XRAY_AVAILABLE and os.getenv('_X_AMZN_TRACE_ID') is not None
        
        if self.enabled:
            # Configure X-Ray recorder
            xray_recorder.configure(
                context_missing='LOG_ERROR',
                plugins=('EC2Plugin', 'ECSPlugin'),
                daemon_address=os.getenv('_X_AMZN_TRACE_ID', '127.0.0.1:2000'),
                use_ssl=False
            )
            
            # Patch AWS SDK calls
            patch_all()
            
            logger.info("X-Ray tracing enabled")
        else:
            logger.info("X-Ray tracing disabled")
    
    def is_enabled(self) -> bool:
        """Check if X-Ray tracing is enabled"""
        return self.enabled
    
    def create_subsegment(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Create a new subsegment"""
        if not self.enabled:
            return None
        
        try:
            subseg = xray_recorder.begin_subsegment(name)
            
            if metadata:
                for key, value in metadata.items():
                    subseg.put_metadata(key, value)
            
            return subseg
        except SegmentNotFoundException:
            logger.warning(f"Cannot create subsegment '{name}' - no active segment")
            return None
        except Exception as e:
            logger.error(f"Failed to create subsegment '{name}': {e}")
            return None
    
    def end_subsegment(self, subseg: Any):
        """End a subsegment"""
        if not self.enabled or not subseg:
            return
        
        try:
            xray_recorder.end_subsegment()
        except Exception as e:
            logger.error(f"Failed to end subsegment: {e}")
    
    def add_annotation(self, key: str, value: str):
        """Add annotation to current segment"""
        if not self.enabled:
            return
        
        try:
            xray_recorder.put_annotation(key, value)
        except Exception as e:
            logger.error(f"Failed to add annotation {key}={value}: {e}")
    
    def add_metadata(self, namespace: str, key: str, value: Any):
        """Add metadata to current segment"""
        if not self.enabled:
            return
        
        try:
            xray_recorder.put_metadata(key, value, namespace)
        except Exception as e:
            logger.error(f"Failed to add metadata {namespace}.{key}: {e}")
    
    def capture_lambda_handler(self, func: Callable) -> Callable:
        """Decorator to capture Lambda handler execution"""
        if not self.enabled:
            return func
        
        @xray_recorder.capture('lambda_handler')
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add Lambda-specific annotations
            self.add_annotation('service', 'energygrid-compliance')
            self.add_annotation('environment', os.getenv('ENVIRONMENT', 'unknown'))
            
            # Add function metadata
            function_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'unknown')
            self.add_annotation('function_name', function_name)
            
            try:
                result = func(*args, **kwargs)
                self.add_annotation('status', 'success')
                return result
            except Exception as e:
                self.add_annotation('status', 'error')
                self.add_metadata('error', 'exception', {
                    'type': type(e).__name__,
                    'message': str(e)
                })
                raise
        
        return wrapper
    
    def capture_aws_service_call(self, service_name: str, operation: str):
        """Decorator to capture AWS service calls"""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                subseg = self.create_subsegment(f"{service_name}.{operation}")
                
                if subseg:
                    subseg.put_annotation('service', service_name)
                    subseg.put_annotation('operation', operation)
                
                try:
                    result = func(*args, **kwargs)
                    if subseg:
                        subseg.put_annotation('status', 'success')
                    return result
                except Exception as e:
                    if subseg:
                        subseg.put_annotation('status', 'error')
                        subseg.put_metadata('error', {
                            'type': type(e).__name__,
                            'message': str(e)
                        })
                    raise
                finally:
                    self.end_subsegment(subseg)
            
            return wrapper
        return decorator
    
    def capture_document_processing(self, stage: str, document_id: str):
        """Decorator to capture document processing stages"""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                subseg = self.create_subsegment(f"document_processing.{stage}")
                
                if subseg:
                    subseg.put_annotation('stage', stage)
                    subseg.put_annotation('document_id', document_id)
                    subseg.put_metadata('document', {
                        'id': document_id,
                        'stage': stage,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                try:
                    result = func(*args, **kwargs)
                    if subseg:
                        subseg.put_annotation('status', 'completed')
                        if isinstance(result, (list, tuple)):
                            subseg.put_annotation('result_count', len(result))
                    return result
                except Exception as e:
                    if subseg:
                        subseg.put_annotation('status', 'failed')
                        subseg.put_metadata('error', {
                            'type': type(e).__name__,
                            'message': str(e),
                            'stage': stage,
                            'document_id': document_id
                        })
                    raise
                finally:
                    self.end_subsegment(subseg)
            
            return wrapper
        return decorator
    
    def capture_bedrock_call(self, model_id: str, operation: str):
        """Decorator to capture Bedrock API calls"""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                subseg = self.create_subsegment(f"bedrock.{operation}")
                
                if subseg:
                    subseg.put_annotation('service', 'bedrock')
                    subseg.put_annotation('model_id', model_id)
                    subseg.put_annotation('operation', operation)
                
                try:
                    result = func(*args, **kwargs)
                    if subseg:
                        subseg.put_annotation('status', 'success')
                        # Add token usage if available
                        if hasattr(result, 'get') and 'usage' in result:
                            usage = result['usage']
                            subseg.put_metadata('bedrock_usage', {
                                'input_tokens': usage.get('input_tokens', 0),
                                'output_tokens': usage.get('output_tokens', 0)
                            })
                    return result
                except Exception as e:
                    if subseg:
                        subseg.put_annotation('status', 'error')
                        subseg.put_metadata('bedrock_error', {
                            'type': type(e).__name__,
                            'message': str(e),
                            'model_id': model_id
                        })
                    raise
                finally:
                    self.end_subsegment(subseg)
            
            return wrapper
        return decorator
    
    def capture_database_operation(self, table_name: str, operation: str):
        """Decorator to capture DynamoDB operations"""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                subseg = self.create_subsegment(f"dynamodb.{operation}")
                
                if subseg:
                    subseg.put_annotation('service', 'dynamodb')
                    subseg.put_annotation('table_name', table_name)
                    subseg.put_annotation('operation', operation)
                
                try:
                    result = func(*args, **kwargs)
                    if subseg:
                        subseg.put_annotation('status', 'success')
                        if isinstance(result, (list, tuple)):
                            subseg.put_annotation('item_count', len(result))
                    return result
                except Exception as e:
                    if subseg:
                        subseg.put_annotation('status', 'error')
                        subseg.put_metadata('dynamodb_error', {
                            'type': type(e).__name__,
                            'message': str(e),
                            'table_name': table_name,
                            'operation': operation
                        })
                    raise
                finally:
                    self.end_subsegment(subseg)
            
            return wrapper
        return decorator
    
    def capture_s3_operation(self, bucket_name: str, operation: str):
        """Decorator to capture S3 operations"""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                subseg = self.create_subsegment(f"s3.{operation}")
                
                if subseg:
                    subseg.put_annotation('service', 's3')
                    subseg.put_annotation('bucket_name', bucket_name)
                    subseg.put_annotation('operation', operation)
                
                try:
                    result = func(*args, **kwargs)
                    if subseg:
                        subseg.put_annotation('status', 'success')
                    return result
                except Exception as e:
                    if subseg:
                        subseg.put_annotation('status', 'error')
                        subseg.put_metadata('s3_error', {
                            'type': type(e).__name__,
                            'message': str(e),
                            'bucket_name': bucket_name,
                            'operation': operation
                        })
                    raise
                finally:
                    self.end_subsegment(subseg)
            
            return wrapper
        return decorator


# Global tracer instance
tracer = XRayTracer()


def get_tracer() -> XRayTracer:
    """Get the global X-Ray tracer instance"""
    return tracer


# Convenience decorators
def trace_lambda_handler(func: Callable) -> Callable:
    """Decorator to trace Lambda handler"""
    return tracer.capture_lambda_handler(func)


def trace_aws_service(service_name: str, operation: str):
    """Decorator to trace AWS service calls"""
    return tracer.capture_aws_service_call(service_name, operation)


def trace_document_processing(stage: str, document_id: str):
    """Decorator to trace document processing"""
    return tracer.capture_document_processing(stage, document_id)


def trace_bedrock_call(model_id: str, operation: str = 'invoke_model'):
    """Decorator to trace Bedrock calls"""
    return tracer.capture_bedrock_call(model_id, operation)


def trace_database_operation(table_name: str, operation: str):
    """Decorator to trace database operations"""
    return tracer.capture_database_operation(table_name, operation)


def trace_s3_operation(bucket_name: str, operation: str):
    """Decorator to trace S3 operations"""
    return tracer.capture_s3_operation(bucket_name, operation)


class TracingContext:
    """Context manager for manual tracing"""
    
    def __init__(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.metadata = metadata
        self.subseg = None
    
    def __enter__(self):
        self.subseg = tracer.create_subsegment(self.name, self.metadata)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.subseg:
            if exc_type:
                self.subseg.put_annotation('status', 'error')
                self.subseg.put_metadata('error', {
                    'type': exc_type.__name__,
                    'message': str(exc_val)
                })
            else:
                self.subseg.put_annotation('status', 'success')
        
        tracer.end_subsegment(self.subseg)
    
    def add_annotation(self, key: str, value: str):
        """Add annotation to this subsegment"""
        if self.subseg:
            self.subseg.put_annotation(key, value)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to this subsegment"""
        if self.subseg:
            self.subseg.put_metadata(key, value)


def create_tracing_context(name: str, metadata: Optional[Dict[str, Any]] = None) -> TracingContext:
    """Create a tracing context manager"""
    return TracingContext(name, metadata)


# Performance monitoring utilities
class PerformanceTracker:
    """Track performance metrics with X-Ray"""
    
    def __init__(self):
        self.tracer = get_tracer()
    
    def track_processing_time(self, operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
        """Track processing time for an operation"""
        if not self.tracer.is_enabled():
            return
        
        self.tracer.add_annotation(f"{operation}_duration_ms", str(int(duration_ms)))
        
        if metadata:
            self.tracer.add_metadata('performance', f"{operation}_metrics", {
                'duration_ms': duration_ms,
                **metadata
            })
    
    def track_resource_usage(self, resource_type: str, usage_data: Dict[str, Any]):
        """Track resource usage"""
        if not self.tracer.is_enabled():
            return
        
        self.tracer.add_metadata('resource_usage', resource_type, usage_data)
    
    def track_error_rate(self, operation: str, error_count: int, total_count: int):
        """Track error rate for an operation"""
        if not self.tracer.is_enabled():
            return
        
        error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
        
        self.tracer.add_annotation(f"{operation}_error_rate", str(round(error_rate, 2)))
        self.tracer.add_metadata('error_metrics', operation, {
            'error_count': error_count,
            'total_count': total_count,
            'error_rate_percent': error_rate
        })


# Global performance tracker
performance_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """Get the global performance tracker"""
    return performance_tracker