import os
from dotenv import load_dotenv
from crewai import Task,Process
# Load environment variables
load_dotenv()

from textwrap import dedent
from crewai import Agent, Crew
from crewai import Task,Process
from textwrap import dedent



class MediumBlogTasks:

    def task1(self,agent,publication_name):
        task1 = Task(
            description=dedent(f"""
                ONLY fetch the latest medium publication blog for publication name {publication_name} and save output to temporary file.
                DO NOT process or store this data in any database - that will be handled by a separate task.
                Your ONLY responsibility is to fetch the data and save it to a file, then return the file name.
            """),
            agent=agent,
            async_execution=False
        )
        return task1
    
    def task2(self,agent,publication_name):
        task2 = Task(
            description=dedent(f"""
                Using ONLY the file created in the previous task, load the contents of this temporary file 
                which contains content of rss feed for medium publication blog {publication_name}.
                Then store the articles metadata and content in sqlite database.
                Do not fetch any new data from Medium.
            """),
            agent=agent,
            #context=[tasks1],  # This explicitly provides the context from task1
            async_execution=False
        )
        return task2
    
from agents import MediumBlogAgent

agent = MediumBlogAgent().create_agent1()
t=MediumBlogTasks()
input={}
input['publication_name']="neural-engineer"
tasks1 = t.task1(agent,input['publication_name'])
tasks2 = t.task2(agent,input['publication_name'])

# Create the Crew
crew = Crew(
    agents=[agent],
    tasks=[tasks1,tasks2],
    verbose=2,
    process=Process.sequential  # Tasks will run in the defined order
)

print("🤖 Starting Medium Blog AI Assistant...")
result = crew.kickoff()
    
print("\n✅ Email Assistant Results:")
print(result)