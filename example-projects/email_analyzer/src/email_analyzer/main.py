#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from email_analyzer.crew import EmailAnalyzer

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

from crewai.flow.flow import Flow, listen, start
from langchain_community.chat_models import ChatOpenAI

import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

def run():
    """
    Run the crew.==
    """
    email=os.getenv("USER_EMAIL")
    fromemail="noreply@uber.com"
    inputs={
        'email': email,
        'fromemail': fromemail
    }
    print("email inputs are ",inputs)
    try:
        EmailAnalyzer().crew().kickoff(inputs=inputs)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"An error occurred while running the crew: {e}")

if __name__ == "__main__":
    run()
