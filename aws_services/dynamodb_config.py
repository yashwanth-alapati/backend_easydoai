# easydo_backend/aws_services/dynamodb_config.py
import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime, timedelta
import logging
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TokenStorage:
    """DynamoDB-based token storage for OAuth tokens"""
    
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.table_name = os.getenv('TOKENS_TABLE_NAME', 'easydoai-user-tokens')
        
        # Initialize DynamoDB resource
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
            logger.info(f"Connected to DynamoDB table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            self.dynamodb = None
            self.table = None
    
    def store_tokens(self, user_id: str, service: str, tokens: Dict[str, Any]) -> bool:
        """Store OAuth tokens for a user and service"""
        if not self.table:
            logger.error("DynamoDB table not available")
            return False
            
        try:
            # Calculate expiry time
            expires_in = tokens.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Create TTL timestamp (expires_at + 7 days for cleanup)
            ttl = int((expires_at + timedelta(days=7)).timestamp())
            
            item = {
                'user_id': user_id,
                'service': service,  # 'gmail' or 'google_calendar'
                'access_token': tokens['access_token'],
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
            
            # Add refresh token if available
            if 'refresh_token' in tokens:
                item['refresh_token'] = tokens['refresh_token']
            
            # Add scope if available
            if 'scope' in tokens:
                item['scope'] = tokens['scope']
            
            # Add token type
            if 'token_type' in tokens:
                item['token_type'] = tokens['token_type']
            
            self.table.put_item(Item=item)
            logger.info(f"Stored {service} tokens for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error storing tokens for user {user_id}, service {service}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing tokens: {e}")
            return False
    
    def get_tokens(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """Retrieve tokens for a user and service"""
        if not self.table:
            logger.error("DynamoDB table not available")
            return None
            
        try:
            response = self.table.get_item(
                Key={
                    'user_id': user_id,
                    'service': service
                }
            )
            
            if 'Item' not in response:
                logger.info(f"No tokens found for user {user_id}, service {service}")
                return None
                
            tokens = response['Item']
            
            # Check if tokens are expired
            expires_at = datetime.fromisoformat(tokens['expires_at'])
            if datetime.utcnow() >= expires_at:
                logger.info(f"Tokens expired for user {user_id}, service {service}")
                # TODO: Implement token refresh logic
                return None
                
            return tokens
            
        except ClientError as e:
            logger.error(f"Error retrieving tokens for user {user_id}, service {service}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving tokens: {e}")
            return None
    
    def delete_tokens(self, user_id: str, service: str) -> bool:
        """Delete tokens for a user and service"""
        if not self.table:
            logger.error("DynamoDB table not available")
            return False
            
        try:
            self.table.delete_item(
                Key={
                    'user_id': user_id,
                    'service': service
                }
            )
            logger.info(f"Deleted {service} tokens for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting tokens for user {user_id}, service {service}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting tokens: {e}")
            return False
    
    def list_user_services(self, user_id: str) -> list:
        """List all services a user has tokens for"""
        if not self.table:
            logger.error("DynamoDB table not available")
            return []
            
        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
            )
            
            services = []
            for item in response.get('Items', []):
                # Check if tokens are still valid
                expires_at = datetime.fromisoformat(item['expires_at'])
                if datetime.utcnow() < expires_at:
                    services.append({
                        'service': item['service'],
                        'expires_at': item['expires_at'],
                        'scope': item.get('scope', '')
                    })
                    
            return services
            
        except ClientError as e:
            logger.error(f"Error listing services for user {user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing services: {e}")
            return []

# Global token storage instance
token_storage = TokenStorage()