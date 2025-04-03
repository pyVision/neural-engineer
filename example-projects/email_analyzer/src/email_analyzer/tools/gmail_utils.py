import os
import pickle
import base64

import json
import sqlite3  # Replace rocksdb with sqlite3
import re  # Add this import for regular expressions
from bs4 import BeautifulSoup  # Add this import for BeautifulSoup

from simplegmail import Gmail
from simplegmail.query import construct_query

"""Gmail utility functions for email processing and queue management.

This module provides functionality for:
- Connecting to Gmail API
- Fetching and processing emails
- Managing email queues using SQLite
- Handling email data caching
"""

def get_gmail_service(email=None):
    """Creates and returns a Gmail API service object.
    
    Args:
        email (str, optional): The delegated email address to access. Defaults to None.
        
    Returns:
        Gmail: An authenticated Gmail service object.
    """
    creds_path = os.getenv("GMAIL_CREDENTIALS_FILE")
    gmail = Gmail(creds_file=creds_path, delegated_email=email)
    return gmail

def remove_email_from_queue(queue_name, msg_id):
    """Removes an email from the queue and updates associated counters.
    
    Args:
        queue_name (str): Name of the queue to remove email from
        msg_id (str): ID of the email message to remove
    """
    conn = sqlite3.connect("email_cache.db")
    cursor = conn.cursor()
    
    # Delete the message from the queue
    cursor.execute("DELETE FROM email_queue WHERE queue_name = ? AND msg_id = ?", 
                  (queue_name, msg_id))
    
    # Decrement the counter
    counter_key = f"{queue_name}:counter"
    cursor.execute("UPDATE counters SET counter_value = counter_value - 1 WHERE counter_key = ?", 
                  (counter_key,))
    
    conn.commit()
    conn.close()

def fetch_and_process_email(queue_name):
    """Fetches and processes the oldest email from a specified queue.
    
    Args:
        queue_name (str): Name of the queue to fetch from
        
    Returns:
        tuple: (email_data, msg_id) if email exists, (None, None) otherwise
        where email_data is the JSON-decoded email content
    """
    # Open SQLite database connection
    conn = sqlite3.connect("email_cache.db")
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_queue (
        queue_name TEXT,
        msg_id TEXT,
        counter INTEGER,
        email_data TEXT,
        PRIMARY KEY (queue_name, msg_id)
    )
    ''')
    
    # Create counters table for tracking queue positions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS counters (
        counter_key TEXT PRIMARY KEY,
        counter_value INTEGER
    )
    ''')
    
    # Get the counter key for this queue
    counter_key = f"{queue_name}:counter"
    cursor.execute("SELECT counter_value FROM counters WHERE counter_key = ?", (counter_key,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None,None
    
    # Get the oldest message (lowest counter value)
    cursor.execute("""
        SELECT msg_id, email_data, counter FROM email_queue 
        WHERE queue_name = ? 
        ORDER BY counter ASC LIMIT 1
    """, (queue_name,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None,None
    
    msg_id, email_data, counter = result
    conn.close()
    
    # Remove the email from queue
    #remove_email_from_queue(queue_name, msg_id)
    
    return json.loads(email_data),msg_id

def push_unique_emails_to_queues(emails, agent_queues):
    """Pushes unique emails to multiple agent queues in FIFO order.
    
    Args:
        emails (list): List of email dictionaries to process
        agent_queues (list): List of queue names to push emails to
        
    Returns:
        str: Status message with count of new emails pushed
    """
    new_count = 0
    
    # Open SQLite database connection
    conn = sqlite3.connect("email_cache.db")
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS emails (
        msg_id TEXT PRIMARY KEY,
        email_data TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_queue (
        queue_name TEXT,
        msg_id TEXT,
        counter INTEGER,
        email_data TEXT,
        PRIMARY KEY (queue_name, msg_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS counters (
        counter_key TEXT PRIMARY KEY,
        counter_value INTEGER
    )
    ''')
    
    for email in emails:
        msg_id = email['id']
        print("checking emails ", msg_id)
        # Check for duplicate messages
        cursor.execute("SELECT 1 FROM emails WHERE msg_id = ?", (msg_id,))
        r1 = cursor.fetchone()
        
        if r1:  # If email exists
            # Convert email to JSON for storage
            email_json = json.dumps(email)
            
            # Add to each agent's queue with FIFO ordering
            for queue in agent_queues:
                # Maintain FIFO order using counter
                counter_key = f"{queue}:counter"
                cursor.execute("SELECT counter_value FROM counters WHERE counter_key = ?", (counter_key,))
                result = cursor.fetchone()
                
                if not result:
                    counter_value = 0
                    cursor.execute("INSERT INTO counters (counter_key, counter_value) VALUES (?, ?)", 
                                  (counter_key, 1))
                else:
                    counter_value = result[0]
                    cursor.execute("UPDATE counters SET counter_value = ? WHERE counter_key = ?", 
                                  (counter_value + 1, counter_key))
                
                cursor.execute("""
                    INSERT INTO email_queue (queue_name, msg_id, counter, email_data) 
                    VALUES (?, ?, ?, ?)
                """, (queue, msg_id, counter_value, email_json))
                
            new_count += 1
    
    conn.commit()
    conn.close()
    return f"{new_count} new emails pushed to {len(agent_queues)} queues as FIFO."

def fetch_emails(email, filter, start_date, count, page_token=None):
    """Fetches and processes emails from Gmail inbox with caching.
    
    Args:
        email (str): Email address to fetch from
        filter (str): Gmail query filter
        start_date (str): Start date for fetching emails
        count (int): Maximum number of emails to fetch
        page_token (str, optional): Token for pagination
        
    Returns:
        tuple: (emails_list, next_page_token) or (None, None) on error
        where emails_list contains processed email dictionaries
    """
    try:
        emails = []
        # Initialize database connection and create tables
        conn = sqlite3.connect("email_cache.db")
        cursor = conn.cursor()
        
        # Set up database tables for caching
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            msg_id TEXT PRIMARY KEY,
            email_data TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkpoints (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')

        # Process checkpoint date
        pstart_date = start_date
        start_date = None
        
        try:
            # Retrieve last checkpoint
            cursor.execute("SELECT value FROM checkpoints WHERE key = ?", ('last_fetch_checkpoint',))
            result = cursor.fetchone()
            if result:
                start_date = result[0]
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
            cursor.execute("SELECT email_data FROM emails WHERE msg_id = ?", (msg_id,))
            result = cursor.fetchone()
            
            if not result:  # If not in cache, process the message
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
                cursor.execute("INSERT INTO emails (msg_id, email_data) VALUES (?, ?)", 
                              (msg_id, email_json))
                emails.append(mf)
            else:  # If in cache, use cached version
                mf = json.loads(result[0])
                emails.append(mf)

        # Update checkpoint with current date
        from datetime import datetime
        current_date = datetime.now().strftime('%Y/%m/%d')
        cursor.execute("INSERT OR REPLACE INTO checkpoints (key, value) VALUES (?, ?)", 
                      ('last_fetch_checkpoint', current_date))
        
        conn.commit()
        conn.close()
        return emails, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None




