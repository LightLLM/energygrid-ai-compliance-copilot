"""
SNS Subscription Handler for EnergyGrid.AI Compliance Copilot
Handles SNS subscription confirmations and message processing
"""

import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SNSSubscriptionHandler:
    """Handler for SNS subscription management"""
    
    def __init__(self):
        self.sns = boto3.client('sns')
    
    def handle_sns_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SNS message from Lambda event
        
        Args:
            event: Lambda event containing SNS message
            
        Returns:
            Processing result
        """
        
        try:
            # Process each SNS record
            for record in event.get('Records', []):
                if record.get('EventSource') == 'aws:sns':
                    self.process_sns_record(record)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'SNS messages processed successfully'
                })
            }
            
        except Exception as e:
            logger.error(f"Error processing SNS messages: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to process SNS messages',
                    'message': str(e)
                })
            }
    
    def process_sns_record(self, record: Dict[str, Any]) -> None:
        """
        Process individual SNS record
        
        Args:
            record: SNS record from Lambda event
        """
        
        try:
            sns_message = record.get('Sns', {})
            message_type = sns_message.get('Type')
            
            if message_type == 'SubscriptionConfirmation':
                self.handle_subscription_confirmation(sns_message)
            elif message_type == 'Notification':
                self.handle_notification(sns_message)
            elif message_type == 'UnsubscribeConfirmation':
                self.handle_unsubscribe_confirmation(sns_message)
            else:
                logger.warning(f"Unknown SNS message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing SNS record: {str(e)}")
    
    def handle_subscription_confirmation(self, sns_message: Dict[str, Any]) -> None:
        """
        Handle SNS subscription confirmation
        
        Args:
            sns_message: SNS message data
        """
        
        try:
            topic_arn = sns_message.get('TopicArn')
            token = sns_message.get('Token')
            subscribe_url = sns_message.get('SubscribeURL')
            
            logger.info(f"Confirming subscription to topic: {topic_arn}")
            
            # Confirm subscription using token
            if token and topic_arn:
                response = self.sns.confirm_subscription(
                    TopicArn=topic_arn,
                    Token=token
                )
                
                subscription_arn = response.get('SubscriptionArn')
                logger.info(f"Subscription confirmed: {subscription_arn}")
            else:
                logger.error("Missing token or topic ARN for subscription confirmation")
                
        except ClientError as e:
            logger.error(f"AWS error confirming subscription: {str(e)}")
        except Exception as e:
            logger.error(f"Error confirming subscription: {str(e)}")
    
    def handle_notification(self, sns_message: Dict[str, Any]) -> None:
        """
        Handle SNS notification message
        
        Args:
            sns_message: SNS message data
        """
        
        try:
            subject = sns_message.get('Subject', 'No Subject')
            message = sns_message.get('Message', '')
            topic_arn = sns_message.get('TopicArn')
            message_attributes = sns_message.get('MessageAttributes', {})
            
            logger.info(f"Processing notification: {subject}")
            
            # Try to parse message as JSON
            try:
                message_data = json.loads(message)
                self.process_notification_data(message_data, message_attributes)
            except json.JSONDecodeError:
                # Handle plain text message
                self.process_plain_text_notification(subject, message, message_attributes)
                
        except Exception as e:
            logger.error(f"Error handling notification: {str(e)}")
    
    def handle_unsubscribe_confirmation(self, sns_message: Dict[str, Any]) -> None:
        """
        Handle SNS unsubscribe confirmation
        
        Args:
            sns_message: SNS message data
        """
        
        try:
            topic_arn = sns_message.get('TopicArn')
            logger.info(f"Unsubscribe confirmation for topic: {topic_arn}")
            
        except Exception as e:
            logger.error(f"Error handling unsubscribe confirmation: {str(e)}")
    
    def process_notification_data(self, 
                                message_data: Dict[str, Any], 
                                message_attributes: Dict[str, Any]) -> None:
        """
        Process structured notification data
        
        Args:
            message_data: Parsed message data
            message_attributes: SNS message attributes
        """
        
        try:
            notification_type = message_attributes.get('notification_type', {}).get('Value')
            user_id = message_attributes.get('user_id', {}).get('Value')
            
            logger.info(f"Processing {notification_type} notification for user {user_id}")
            
            # Log notification details for monitoring
            self.log_notification_metrics(notification_type, message_data)
            
            # Here you could add additional processing like:
            # - Sending emails via SES
            # - Sending SMS via SNS
            # - Storing notifications in database
            # - Triggering webhooks
            # - Updating user preferences
            
        except Exception as e:
            logger.error(f"Error processing notification data: {str(e)}")
    
    def process_plain_text_notification(self, 
                                      subject: str, 
                                      message: str, 
                                      message_attributes: Dict[str, Any]) -> None:
        """
        Process plain text notification
        
        Args:
            subject: Notification subject
            message: Notification message
            message_attributes: SNS message attributes
        """
        
        try:
            logger.info(f"Processing plain text notification: {subject}")
            
            # Log for monitoring
            self.log_notification_metrics('plain_text', {
                'subject': subject,
                'message_length': len(message)
            })
            
        except Exception as e:
            logger.error(f"Error processing plain text notification: {str(e)}")
    
    def log_notification_metrics(self, 
                               notification_type: Optional[str], 
                               message_data: Dict[str, Any]) -> None:
        """
        Log notification metrics for monitoring
        
        Args:
            notification_type: Type of notification
            message_data: Message data for metrics
        """
        
        try:
            # Log metrics that can be picked up by CloudWatch
            logger.info(f"METRIC: notification_processed type={notification_type or 'unknown'}")
            
            # You could also send custom metrics to CloudWatch here
            # cloudwatch = boto3.client('cloudwatch')
            # cloudwatch.put_metric_data(...)
            
        except Exception as e:
            logger.error(f"Error logging notification metrics: {str(e)}")
    
    def create_subscription(self, 
                          topic_arn: str, 
                          protocol: str, 
                          endpoint: str,
                          attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Create SNS subscription
        
        Args:
            topic_arn: SNS topic ARN
            protocol: Subscription protocol (email, sms, lambda, etc.)
            endpoint: Subscription endpoint
            attributes: Optional subscription attributes
            
        Returns:
            Subscription ARN if successful, None otherwise
        """
        
        try:
            response = self.sns.subscribe(
                TopicArn=topic_arn,
                Protocol=protocol,
                Endpoint=endpoint
            )
            
            subscription_arn = response.get('SubscriptionArn')
            
            # Set subscription attributes if provided
            if attributes and subscription_arn and subscription_arn != 'pending confirmation':
                for key, value in attributes.items():
                    self.sns.set_subscription_attributes(
                        SubscriptionArn=subscription_arn,
                        AttributeName=key,
                        AttributeValue=value
                    )
            
            logger.info(f"Created subscription: {subscription_arn}")
            return subscription_arn
            
        except ClientError as e:
            logger.error(f"AWS error creating subscription: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return None
    
    def delete_subscription(self, subscription_arn: str) -> bool:
        """
        Delete SNS subscription
        
        Args:
            subscription_arn: Subscription ARN to delete
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            self.sns.unsubscribe(SubscriptionArn=subscription_arn)
            logger.info(f"Deleted subscription: {subscription_arn}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS error deleting subscription: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting subscription: {str(e)}")
            return False
    
    def list_subscriptions(self, topic_arn: Optional[str] = None) -> list:
        """
        List SNS subscriptions
        
        Args:
            topic_arn: Optional topic ARN to filter by
            
        Returns:
            List of subscriptions
        """
        
        try:
            if topic_arn:
                response = self.sns.list_subscriptions_by_topic(TopicArn=topic_arn)
            else:
                response = self.sns.list_subscriptions()
            
            return response.get('Subscriptions', [])
            
        except ClientError as e:
            logger.error(f"AWS error listing subscriptions: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error listing subscriptions: {str(e)}")
            return []

# Global instance
subscription_handler = None

def get_subscription_handler():
    """Get or create the global subscription handler instance"""
    global subscription_handler
    if subscription_handler is None:
        subscription_handler = SNSSubscriptionHandler()
    return subscription_handler

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for SNS subscription management
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Processing result
    """
    
    handler = get_subscription_handler()
    return handler.handle_sns_message(event)