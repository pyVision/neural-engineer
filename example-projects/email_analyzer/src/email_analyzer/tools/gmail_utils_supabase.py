import os
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client
from simplegmail import Gmail
from simplegmail.query import construct_query
from .supabase_queue import SupabaseQueue

"""Gmail utility functions for email processing and queue management with Supabase.

This module provides functionality for:
- Connecting to Gmail API
- Fetching and processing emails
- Managing email queues using Supabase
- Handling email data caching
"""

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Initialize queue manager
queue_manager = SupabaseQueue()


def get_gmail_service(email=None):
    """Creates and returns a Gmail API service object."""
    creds_path = os.getenv("GMAIL_CREDENTIALS_FILE")
    gmail = Gmail(creds_file=creds_path, delegated_email=email)
    return gmail

def remove_email_from_queue(queue_name, msg_id):
    """Removes an email from the queue."""
    try:
        # Get the message from queue
        message = queue_manager.dequeue(queue_name)
        if message and message.get('msg_id') == msg_id:
            return True
        return False
    except Exception as e:
        print(f"Error removing email from queue: {e}")
        return False

def fetch_and_process_email(queue_name):
    """Fetches and processes the oldest email from a specified queue."""
    try:
        # Get message from queue
        msg_id,message = queue_manager.peek(queue_name)
        if not message:
            return None, None
        d1=message["email_data"]
        d1["email_id"]=message.get("msg_id")
        return d1, msg_id
        
    except Exception as e:
        print(f"Error fetching email from queue: {e}")
        return None, None


def save_processed_email(emails):
    """Saves processed email data to the database."""
    try:
        # Save processed email data
        for email in emails:
            msg_id=email['email_id']
            email_json = email

            supabase.table('processed_emails').insert({'msg_id': msg_id, 'email_data': email_json}).execute()
        return True
    except Exception as e:
        print(f"Error saving processed email: {e}")
        return False

    

def push_unique_emails_to_queues(emails, agent_queues):
    """Pushes unique emails to multiple agent queues."""
    new_count = 0
    
    try:
        for email in emails:
            msg_id = email['id']
            print("checking emails ", msg_id)
            
            # Check for duplicate messages
            result = supabase.table('emails').select('msg_id').eq('msg_id', msg_id).execute()
            
            if result.data:  # If email exists
                email_json = json.dumps(email)
                email['email_id'] = msg_id
                # Add to each agent's queue
                for queue in agent_queues:
                    message_payload = {
                        #'msg_id': msg_id,
                        'email_data': email,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Use queue manager to enqueue message
                    queue_manager.enqueue(queue, message_payload)
                
                new_count += 1
        
        return f"{new_count} new emails pushed to {len(agent_queues)} queues."
    
    except Exception as e:
        print(f"Error pushing emails to queues: {e}")
        return f"Error: {str(e)}"

def fetch_emails(email, filter, start_date, count, page_token=None):
    """Fetches and processes emails from Gmail inbox with caching."""
    try:
        emails = []
        
        # Process checkpoint date
        pstart_date = start_date
        start_date = None
        
        try:
            # Retrieve last checkpoint
            result = supabase.table('checkpoints').select('value').eq('key', 'last_fetch_checkpoint').execute()
            if result.data:
                start_date = result.data[0]['value']
                print(f"Using checkpoint date: {start_date}")
        except Exception as e:
            print(f"Error retrieving checkpoint: {e}")

        # Initialize Gmail service
        gmail = get_gmail_service(email=email)
        
        # Set up query parameters
        if start_date:
            pstart_date = start_date

        query_params_1 = {
            "after": pstart_date,
            "sender": filter,
        }        
        
        # Fetch messages from Gmail
        query1 = construct_query(query_params_1)
        messages = gmail.get_messages(query=query1, attachments="ignore", user_id=email)

        # Process each message
        for message in messages:
            msg_id = message.id
            
            # Check cache first
            result = supabase.table('emails').select('email_data').eq('msg_id', msg_id).execute()
            
            if not result.data:  # If not in cache, process the message
                # Extract message headers
                headers = message.headers
                subject = headers.get("Subject", 'No Subject')
                sender = headers.get("From", 'Unknown')
                receiver = headers.get("To", 'Unknown')
                date = headers.get("Date", 'Unknown')

                # Extract and clean message content
                try:
                    soup = BeautifulSoup(message.html, 'html.parser')
                    text_content = soup.get_text(separator=' ', strip=True)
                    text_content = re.sub(r'\n+', ' ', text_content) 
                except Exception as e:
                    text_content = message.plain

                # Create message format structure
                mf = {
                    'id': msg_id,
                    'subject': subject,
                    'sender': sender,
                    'receiver': receiver,
                    'body': message.html,
                    'content': text_content,
                    'date': date,
                    'threadId': message.thread_id
                }
                
                # Cache the processed email
                email_json = json.dumps(mf)
                supabase.table('emails').insert({'msg_id': msg_id, 'email_data': email_json}).execute()
                emails.append(mf)
            else:  # If in cache, use cached version
                mf = json.loads(result.data[0]['email_data'])
                emails.append(mf)

        # Update checkpoint with current date
        current_date = datetime.now().strftime('%Y/%m/%d')
        supabase.table('checkpoints').upsert({'key': 'last_fetch_checkpoint', 'value': current_date}).execute()
        
        return emails, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None