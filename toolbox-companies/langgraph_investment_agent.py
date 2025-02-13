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
  Don't ask for confirmations from the user.
  User: 
"""

queries = [
    "What industries deal with computer manufacturing?",
    "List some companies in the computer manufacturing industry that are in the UK",
#    "Who is working at these companies?",
#    "Which companies are mentioned in the news in January 2023 with positive sentiment?",
#    "Who is working there as board members?",
]

def main():
    model = ChatVertexAI(model_name="gemini-1.5-pro")

    # Load the tools from the Toolbox server
    client = ToolboxClient("http://127.0.0.1:5000")
    tools = client.load_toolset()

    agent = create_react_agent(model, tools, checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": "thread-1"}}
    for query in queries:
        inputs = {"messages": [("user", prompt + query)]}
        response = agent.invoke(inputs, stream_mode="values", config=config)
        print(response["messages"][-1].content)

main()
