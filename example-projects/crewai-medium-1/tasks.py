from crewai import Task,Process
from textwrap import dedent


class GmailAnalysisTasks:
    def fetch_analysis(self, agent):
        fetch_task = Task(
            description=dedent("""
                Use the fetch_and_queue_emails tool to fetch the most recent emails from the user's Gmail account and add to email_queue table managed in the sqlite database .
                Follow these steps:
                1. Connect to the Gmail API using the provided tool
                2. Retrieve the most recent emails
                3. Add the emails to the email_queue 
            """),
            agent=agent,
            async_execution=False
        )
        return fetch_task
    

    def fetch_and_process_email(self, agent):
        fetch_task = Task(
            description=dedent("""
                Use the fetch_and_process_email tool to fetch the most recent emails from email_queue table managed in the sqlite database as defined by the queue name email_processor_expenseagent_queue.
                Follow these steps:
                1. Connect to the sqlite database 
                2. Retrieve the most recent emails corresponding to the queue email_processor_expenseagent_queue from the email_queue database table
                3. process the retrieved email
            """),
            agent=agent,
            async_execution=False
        )
        return fetch_task