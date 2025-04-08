# Define Tools for CrewAI

import json
import os
from crewai import Agent, Task
#from langchain.tools import tool
from langchain_core.tools import BaseTool, StructuredTool, Tool
from email_analyzer.tools.gmail_utils_supabase import save_processed_email,fetch_emails,push_unique_emails_to_queues,fetch_and_process_email, remove_email_from_queue
from textwrap import dedent
from langchain_community.chat_models import ChatOpenAI
from bs4 import BeautifulSoup
import re

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai.tools import tool

# class MyToolInput(BaseModel):
#     """Input schema for MyCustomTool."""
#     argument: str = Field(..., description="Description of the argument.")

# Define the Pydantic model for the blog
class TOutput(BaseModel):
    count: int


class EmailTools:

    # Tool to process one email per agent
    @tool("Process emails from the expense agent queue")
    def fetch_and_process_email(queue:str)->bool:
        """Processes all emails from the specified queue until queue is empty

        Args:
            queue (str): The name of the queue to process emails from
                        (e.g. "email_processor_expenseagent_queue")
        Returns:
            bool: A status message indicating success or failure"""
        
        processed_count = 0
        print("fetch_and_process_email",queue)
        summaries=[]
        try:
            while True:
                emails,msg_id = fetch_and_process_email("email_processor_expenseagent_queue")
                
                #print(msg_id)
                #continue
                if emails!=None and len(emails)>0:
                    email_id=emails["email_id"]
                    print(f"processing emails {emails['subject']}")
                    subject=emails['subject']
                    content=emails['content']
                    date1=emails['date']

                    agent2 = Agent(
                        role="Expense Manager Agent",
                        goal="Review the subject of each email if it belongs to ola or uber , review the subject and contents of the email to determine if it corresponds trip details including date , payment mode , expense ammount",
                        backstory=dedent("""\
                            As an experienced expense management specialist, I have extensive expertise in 
                            analyzing ride-sharing receipts and travel expenses. I'm trained to quickly 
                            identify and extract key information from Uber and Ola emails, including trip 
                            dates, payment details, and expense amounts. My background includes years of 
                            working with corporate expense management systems and automated receipt 
                            processing, making me highly efficient at categorizing and organizing 
                            transportation-related expenses."""),
                            llm=ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
					            model_name="gpt-4o-mini"
		                    ),
                        allow_delegation=False,
                        verbose=True,
                        return_direct=True
                    )
                    task = Task(
                        agent=agent2,
                        expected_output="json",
                        description=dedent(f"""
                            Analyze this Ola/Uber receipt email and extract key information.
                            Email details:
                            - Sender: {emails['sender']}
                            - Recipient: {emails['receiver']}
                            - Subject: "{subject}"
                            - Content: "{content}"
                            - Email Date : "{date1}"
                            - Message ID: {email_id}
                            
                            Format your response as a JSON object with:
                            {{
                                "email_id": message ID,
                                "vendor" : "ola" or "uber",
                                "subject": subject line,
                                "date": expense date (YYYY-MM-DD format),
                                "payment_mode": payment method used,
                                "expense_amount": amount in currency (e.g. "₹123.45"),
                                "expense_details": brief description of pickup/dropoff,
                                "email_date": email received date,
                                "email_recipient": recipient address,
                                "email_sender": sender address
                            }}
                            
                            Extract only factual information present in the email. If any field cannot be determined, use null.
                        """)

                    )
                    task_output = task.execute_sync()

                    if not task_output:
                        break;
                        # Accessing the task output
                    
                    summary=task_output.raw

                    # Clean the JSON string by removing trailing ``` and whitespace
                    summary = summary.strip()
                    if summary.endswith('```'):
                        summary = summary[:-3].strip()
                    if summary.startswith('```json'):
                        summary = summary[7:].strip()

                    # Parse the JSON string into a Python object
                    try:
                        json_summary = json.loads(summary)
                        summaries.append(json_summary)
                        
                        #remove_email_from_queue("email_processor_expenseagent_queue", msg_id)
                        print("processing summary is ",summary)
                        

                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON summary: {e}")
                        print(f"Raw summary: {summary}")
                        break;
                    # processed_count += 1
                    # if processed_count == 2:
                    #     break;
                        
                else:
                    
                    print("No more emails to process")
                    break;

            with open("processed_emails.json", "w") as file:
                        json.dump(summaries, file, indent=4)
            save_processed_email(summaries)
            

            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False 


    @tool("Fetch and queue unique emails from Gmail inbox")
    def fetch_and_queue_emails( email: str , from_email:str ) -> TOutput:
        """Fetches emails from the Gmail inbox and pushes unique emails to the processing queue.

        Args:
           
            email (str): A str containing email id of the user.
            from_email(str) : A str containing the email id of the sender.
        Returns:
            TOutput: An object containing the count of emails fetched and queued.

        """


        try:
            count=10
            start_date="2025-03-30"
            print("calling fetch_and_queue_emails ",count,email)
            next_page_token=None
            fcount=0
            while True:
                emails,next_page_token = fetch_emails(email=email,filter=from_email,start_date=start_date,count=count,page_token=next_page_token)
                if emails!=None and len(emails)>0:
                    print("pushing the emails to queue ",len(emails))
                    fcount=fcount+len(emails)
                    push_unique_emails_to_queues(emails, [
                        "email_processor_expenseagent_queue"
                    ])
                else:
                    break;
            
            print("completed fetching all the emails ",fcount)
            o=TOutput(count=fcount)
            return o
        except Exception as e:
            import traceback
            traceback.print_exc()

        print("completed processing emails")


