import os
from textwrap import dedent
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatOpenAI
from tools import MediumTool
from langchain.agents import load_tools


class MediumBlogAgent:
	def __init__(self):
		self.llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
					model_name="gpt-4o-mini"
					)

	def create_agent1(self):


		agent = Agent(
		role="Medium Blog Fetcher",
		goal="Extract the latest blog content from medium blogs",
		backstory="You are a specialized web scraper expert who efficiently extracts and organizes content from Medium blogs. You understand the structure of Medium's platform and can reliably collect and store article data for further analysis.",
		tools=[MediumTool.get_data, MediumTool.store_articles_in_db],
		llm=self.llm,
		verbose=True,
		#allow_delegation=False,
		#return_direct=True

		)
		return agent

