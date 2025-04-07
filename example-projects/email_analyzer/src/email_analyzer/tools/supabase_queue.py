import os
import json
from typing import Optional, Any, Dict
from supabase import create_client, Client
import datetime

class SupabaseQueue:
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    def process_batch(self, queue_name: str, batch_size: int = 10):
       messages = []
       for _ in range(batch_size):
           message = self.dequeue(queue_name)
           if not message:
               break
           messages.append(message)
       return messages

    def get_queue_status(self, queue_name: str) -> Dict[str, Any]:
       main_queue = self.peek(queue_name)
       dlq = self.peek(f"{queue_name}_dlq")
       return {
           'has_messages': main_queue is not None,
           'has_failed_messages': dlq is not None
       }

    def move_to_dlq(self, queue_name: str, message: Dict[str, Any], error: str):
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
        
        Args:
            queue_name: Name of the queue
            message: Dictionary containing message data
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

    def dequeue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Remove and return the next message from the queue.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Dictionary containing message data or None if queue is empty
        """
        try:
            result = self.supabase.rpc('dequeue', {'queue_name': queue_name}).execute()
            print(f"dequeue result is {result}")
            if result.data:
                return json.loads(result.data)
            return None
        except Exception as e:
            print(f"Error dequeuing message: {e}")
            return None

    def peek(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        View the next message without removing it from the queue.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Dictionary containing message data or None if queue is empty
        """
        try:
            result = self.supabase.rpc('peek_queue', {'queue_name': queue_name}).execute()
            if result.data:
                return json.loads(result.data)
            return None
        except Exception as e:
            print(f"Error peeking queue: {e}")
            return None

    def purge_queue(self, queue_name: str) -> None:
        """
        Remove all messages from the queue.
        
        Args:
            queue_name: Name of the queue
        """
        try:
            self.supabase.rpc('purge_queue', {'queue_name': queue_name}).execute()
        except Exception as e:
            print(f"Error purging queue: {e}")
            raise

# Usage example:
"""
queue = SupabaseQueue()

# Enqueue a message
queue.enqueue('email_queue', {
    'subject': 'Test email',
    'body': 'This is a test message'
})

# Dequeue a message
message = queue.dequeue('email_queue')
if message:
    print(f"Processing message: {message}")

# Check queue length
length = queue.get_queue_length('email_queue')
print(f"Messages in queue: {length}")
"""