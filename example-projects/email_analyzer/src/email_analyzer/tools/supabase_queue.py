"""
A PostgreSQL-based message queue implementation using Supabase.

This module provides a Python interface to interact with a message queue system implemented
in Supabase using the pg_message_queue extension. It supports standard queue operations
like enqueue, dequeue, peek, and batch processing, as well as dead-letter queue (DLQ)
functionality for handling failed messages.

The implementation uses Supabase's RPC functions to ensure atomic operations and proper
concurrency handling at the database level. Each operation is executed as a single
transaction, preventing race conditions in multi-threaded environments.

Features:
    - Basic queue operations (enqueue, dequeue, peek)
    - Batch message processing
    - Dead-letter queue (DLQ) support
    - Queue status monitoring
    - Error handling and recovery
    - Atomic operations via database functions

Requirements:
    - Supabase project with pg_message_queue extension enabled
    - Environment variables:
        - SUPABASE_URL: URL of your Supabase project
        - SUPABASE_KEY: API key for Supabase authentication

Example:
    ```python
    queue = SupabaseQueue()
    
    # Add a message to the queue
    queue.enqueue('email_queue', {
        'subject': 'Test email',
        'body': 'This is a test message'
    })
    
    # Process messages in batches
    messages = queue.process_batch('email_queue', batch_size=10)
    for msg in messages:
        try:
            process_message(msg)
        except Exception as e:
            queue.move_to_dlq('email_queue', msg, str(e))
    ```
"""

import os
import json
from typing import Optional, Any, Dict, List
from supabase import create_client, Client
import datetime


class SupabaseQueue:
    """
    A class implementing queue operations using Supabase as the backend.
    
    This class provides methods to interact with a message queue system implemented
    in Supabase. It supports standard queue operations and includes features like
    batch processing and dead-letter queues for handling failed messages.
    
    The implementation uses database functions to ensure atomic operations and
    proper concurrency handling. Each operation is executed as a single transaction,
    preventing race conditions in multi-threaded environments.
    
    Attributes:
        supabase (Client): Initialized Supabase client for database operations
    """
    
    def __init__(self):
        """
        Initialize Supabase client using environment variables.
        
        Raises:
            KeyError: If required environment variables are not set
        """
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    def process_batch(self, queue_name: str, batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process multiple messages from the queue in a batch.
        
        Args:
            queue_name: Name of the queue to process
            batch_size: Maximum number of messages to retrieve (default: 10)
            
        Returns:
            List of dequeued messages. May be empty if queue is empty.
            
        Example:
            ```python
            messages = queue.process_batch('email_queue', batch_size=5)
            for msg in messages:
                try:
                    process_email(msg)
                except Exception as e:
                    queue.move_to_dlq('email_queue', msg, str(e))
            ```
        """
        messages = []
        for _ in range(batch_size):
            message = self.dequeue(queue_name)
            if not message:
                break
            messages.append(message)
        return messages

    def get_queue_status(self, queue_name: str) -> Dict[str, bool]:
        """
        Get the current status of a queue and its associated dead-letter queue.
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Dictionary containing:
                - has_messages: True if main queue has messages
                - has_failed_messages: True if DLQ has messages
                
        Example:
            ```python
            status = queue.get_queue_status('email_queue')
            if status['has_failed_messages']:
                print("There are failed messages to process")
            ```
        """
        msg_id,main_queue = self.peek(queue_name)
        dmsg_id,dlq = self.peek(f"{queue_name}_dlq")
        return {
            'has_messages': main_queue is not None,
            'has_failed_messages': dlq is not None
        }

    def move_to_dlq(self, queue_name: str, message: Dict[str, Any], error: str):
        """
        Move a failed message to the dead-letter queue (DLQ).
        
        This method wraps the failed message with additional metadata about the failure
        and moves it to a separate queue for failed messages.
        
        Args:
            queue_name: Original queue name
            message: The failed message to move
            error: Description of the error that caused the message to fail
            
        Example:
            ```python
            try:
                process_message(msg)
            except Exception as e:
                queue.move_to_dlq('email_queue', msg, str(e))
            ```
        """
        dlq_message = {
            'original_queue': queue_name,
            'message': message,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.enqueue(f"{queue_name}_dlq", dlq_message)

    def enqueue(self, queue_name: str, message: Dict[str, Any]) -> None:
        """
        Add a message to the specified queue.
        
        This method serializes the message to JSON and adds it to the queue using
        an atomic database operation.
        
        Args:
            queue_name: Name of the queue
            message: Dictionary containing message data
            
        Raises:
            Exception: If the enqueue operation fails
            
        Example:
            ```python
            queue.enqueue('email_queue', {
                'to': 'user@example.com',
                'subject': 'Hello',
                'body': 'Message content'
            })
            ```
        """
        try:
            self.supabase.rpc(
                'enqueue',
                {
                    'queue_name': queue_name,
                    'message_payload': json.dumps(message)
                }
            ).execute()
        except Exception as e:
            print(f"Error enqueueing message: {e}")
            raise

    def dequeue(self, queue_name: str,msg_id:str=None) -> Optional[Dict[str, Any]]:
        """
        Remove and return the next message from the queue.
        
        This method attempts to retrieve and remove the next message from the queue
        in a single atomic operation.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Dictionary containing message data or None if queue is empty
            
        Note:
            If dequeuing fails, the error is logged and None is returned to allow
            for graceful error handling in batch operations.
            
        Example:
            ```python
            while True:
                message = queue.dequeue('email_queue')
                if not message:
                    break
                process_message(message)
            ```
        """
        try:
            result = self.supabase.rpc('dequeue', {'msg_id':msg_id,'queue_name': queue_name}).execute()
            #
            #print(f"dequeue result is {result}")
            if result.data:
                j=result.data
                #print(j)
                return j['msg_id'],None
            return None,None
        except Exception as e:
            print(f"Error dequeuing message: {e}")
            return None,None

    def peek(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        View the next message without removing it from the queue.
        
        This method allows inspection of the next message while leaving it in the queue.
        Useful for queue monitoring and status checks.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Dictionary containing message data or None if queue is empty
            
        Note:
            This operation does not modify the queue state and can be safely used
            for monitoring purposes.
            
        Example:
            ```python
            message = queue.peek('email_queue')
            if message:
                print(f"Next message to be processed: {message}")
            ```
        """
        try:
            result = self.supabase.rpc('peek_queue', {'queue_name': queue_name}).execute()
            #print("MM",j['msg_id'])
            if result.data:
                j=result.data
                if j['data']:
                    return j['msg_id'],json.loads(j['data'])
            return None,None
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error peeking queue: {e}",queue_name)
            return None,None

    def purge_queue(self, queue_name: str) -> None:
        """
        Remove all messages from the queue.
        
        This method completely empties a queue by deleting and recreating it.
        Use with caution as this operation cannot be undone.
        
        Args:
            queue_name: Name of the queue
            
        Raises:
            Exception: If the purge operation fails
            
        Warning:
            This operation is irreversible and will delete all messages in the queue.
            Use only when you are certain you want to clear the entire queue.
            
        Example:
            ```python
            # Clear all pending messages
            queue.purge_queue('email_queue')
            ```
        """
        try:
            self.supabase.rpc('purge_queue', {'queue_name': queue_name}).execute()
        except Exception as e:
            print(f"Error purging queue: {e}")
            raise