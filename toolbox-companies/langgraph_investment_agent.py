# pip install -q toolbox-langchain langchain-google-vertexai langgraph
# python langgraph_investment_agent.py

import asyncio
import os

from langgraph.prebuilt import create_react_agent
from langchain_google_vertexai import ChatVertexAI
from langgraph.checkpoint.memory import MemorySaver

from toolbox_langchain import ToolboxClient

prompt = """
  You're a helpful investment research assistant. 
  You can use the provided tools to search for companies, 
  people at companies, industries, and news articles from 2023.
  Make sure to use prior tool outputs from the conversation to filter, e.g. by location, sentiment, etc.
  or as inputs for subsequent operations. If needed use the tools that provide more detailed information 
  on articles or companies to get the information you need for filtering or sorting.
  Don't ask for confirmations from the user.
  User: 
"""

queries = [
    "What industries deal with neurological implants?",
    "List 5 companies in from those industries with their description and filter afterwards by California.",
    "Who is working at these companies?",
    "What were the news in January 2023 with positive sentiment? List top 5 articles.",
    "Summarize these articles.",
    "Which 3 companies were mentioned by these articles?"
    "Who is working there as board members?",
]

import json

def main():
    model = ChatVertexAI(model_name="gemini-2.0-flash-001")

    # Load the tools from the Toolbox server
    client = ToolboxClient("http://127.0.0.1:5000")
    tools = client.load_toolset()

    memory = MemorySaver()
    agent = create_react_agent(model, tools, checkpointer=memory)

    config = {"configurable": {"thread_id": "thread-1"}}
    for query in queries:
        inputs = {"messages": [("user", prompt + query)]}
        response = agent.invoke(inputs, stream_mode="values", config=config)
        print(query + ":\n")
#        print(response)
        print(response["messages"][-1].content)



main()
