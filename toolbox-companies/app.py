import os

import inspect
from typing import Callable, TypeVar

from dotenv import load_dotenv

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from toolbox_langchain import ToolboxClient


# Utility function to get a Streamlit callback handler with context
# Define a function to wrap and add context to Streamlit's integration with LangGraph
def get_streamlit_cb(parent_container: DeltaGenerator) -> BaseCallbackHandler:
    """
    Creates a Streamlit callback handler that integrates fully with any LangChain ChatLLM integration,
    updating the provided Streamlit container with outputs such as tokens, model responses,
    and intermediate steps. This function ensures that all callback methods run within
    the Streamlit execution context, fixing the NoSessionContext() error commonly encountered
    in Streamlit callbacks.

    Args:
        parent_container (DeltaGenerator): The Streamlit container where the text will be rendered
                                           during the LLM interaction.
    Returns:
        BaseCallbackHandler: An instance of StreamlitCallbackHandler configured for full integration
                             with ChatLLM, enabling dynamic updates in the Streamlit app.
    """

    # Define a type variable for generic type hinting in the decorator, ensuring the original
    # function and wrapped function maintain the same return type.
    fn_return_type = TypeVar('fn_return_type')

    # Decorator function to add Streamlit's execution context to a function
    def add_streamlit_context(fn: Callable[..., fn_return_type]) -> Callable[..., fn_return_type]:
        """
        Decorator to ensure that the decorated function runs within the Streamlit execution context.
        This is necessary for interacting with Streamlit components from within callback functions
        and prevents the NoSessionContext() error by adding the correct session context.

        Args:
            fn (Callable[..., fn_return_type]): The function to be decorated, typically a callback method.
        Returns:
            Callable[..., fn_return_type]: The decorated function that includes the Streamlit context setup.
        """
        # Retrieve the current Streamlit script execution context.
        # This context holds session information necessary for Streamlit operations.
        ctx = get_script_run_ctx()

        def wrapper(*args, **kwargs) -> fn_return_type:
            """
            Wrapper function that adds the Streamlit context and then calls the original function.
            If the Streamlit context is not set, it can lead to NoSessionContext() errors, which this
            wrapper resolves by ensuring that the correct context is used when the function runs.

            Args:
                *args: Positional arguments to pass to the original function.
                **kwargs: Keyword arguments to pass to the original function.
            Returns:
                fn_return_type: The result from the original function.
            """
            # Add the previously captured Streamlit context to the current execution.
            # This step fixes NoSessionContext() errors by ensuring that Streamlit knows which session
            # is executing the code, allowing it to properly manage session state and updates.
            add_script_run_ctx(ctx=ctx)
            return fn(*args, **kwargs)  # Call the original function with its arguments

        return wrapper

    # Create an instance of Streamlit's StreamlitCallbackHandler with the provided Streamlit container
    st_cb = StreamlitCallbackHandler(parent_container)

    # Iterate over all methods of the StreamlitCallbackHandler instance
    for method_name, method_func in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if method_name.startswith('on_'):  # Identify callback methods that respond to LLM events
            # Wrap each callback method with the Streamlit context setup to prevent session errors
            setattr(st_cb, method_name,
                    add_streamlit_context(method_func))  # Replace the method with the wrapped version

    # Return the fully configured StreamlitCallbackHandler instance, now context-aware and integrated with any ChatLLM
    return st_cb

# Load the tools from the Toolbox server
client = ToolboxClient("http://127.0.0.1:5000")
tools = client.load_toolset()

prompt = """
  You're a helpful investment research assistant. 
  You can use the provided tools to search for companies, 
  people at companies, industries, and news articles from 2023.
  Make sure to use prior tool outputs and memory from the conversation to 
  lookup entities by id or 
  filter, e.g. by location, sentiment, etc.
  or as inputs for subsequent operations. If needed use the tools that provide more detailed information 
  on articles or companies to get the information you need for filtering or sorting.
  Don't ask for confirmations from the user.
"""

queries = [
    "What industries deal with neurological implants?",
    "List 5 companies in from those industries with their description and filter the list by California.",
    "Who is working at these companies?",
    "What were the news in January 2023 with positive sentiment? List top 5 articles.",
    "Summarize these articles.",
    "Which 3 companies were mentioned by these articles?",
    "Who is working there as board members?",
]

llm = ChatVertexAI(model_name="gemini-2.0-flash-001", streaming=True)

memory = MemorySaver()
graph_runnable = create_react_agent(llm, tools, checkpointer=memory)

# Function to invoke the compiled graph externally
def invoke_our_graph(st_messages, callables):
    # Ensure the callables parameter is a list as you can have multiple callbacks
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")
    # Invoke the graph with the current messages and callback configuration
    return graph_runnable.invoke({"messages": st_messages}, stream_mode="values", config={"configurable": {"thread_id": "thread-1"}, "callbacks": callables})

load_dotenv()

st.title("Investment Research Agent")
st.markdown("### StreamLit 🤝 LangGraph 🤝 Gen AI Toolbox 🤝 Neo4j")
st.markdown("####  This is an investment research agent built with Google Gen AI Toolbox using a Neo4j Knowledge Graph")
st.markdown("""
            Learn more in the [blog post](https://medium.com/google-cloud/building-ai-agents-with-googles-gen-ai-toolbox-and-neo4j-knowledge-graphs-835c0cda3090)
            and [Neo4j GenAI Ecosystem Pages](https://neo4j.com/labs/genai-ecosystem)
            """)

# Check if the API key is available as an environment variable
if not os.getenv('GOOGLE_API_KEY'):
    # If not, display a sidebar input for the user to provide the API key
    st.sidebar.header("GOOGLE_API_KEY Project Setup")
    api_key = st.sidebar.text_input(label="API Key", type="password", label_visibility="collapsed")
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
    # If no key is provided, show an info message and stop further execution and wait till key is entered
    if not api_key:
        st.info("Please enter your GOOGLE_API_KEY in the sidebar.")
        st.stop()

if "messages" not in st.session_state:
    # default initial message to render in message state
    st.session_state["messages"] = [
        SystemMessage(content=prompt),
        AIMessage(content="How can I help you? You can research companies, articles, people.")
    ]

# Loop through all messages in the session state and render them as a chat on every st.refresh mech
for msg in st.session_state.messages:
    # https://docs.streamlit.io/develop/api-reference/chat/st.chat_message
    # we store them as AIMessage and HumanMessage as its easier to send to LangGraph
    if type(msg) == AIMessage:
        st.chat_message("assistant").write(msg.content)
    if type(msg) == HumanMessage:
        st.chat_message("user").write(msg.content)

question = st.selectbox("Questions", queries, index=None, placeholder="possible questions", label_visibility="hidden")
# takes new input in chat box from user and invokes the graph
prompt = st.chat_input()
prompt = question or prompt
if prompt:
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").write(prompt)

    # Process the AI's response and handles graph events using the callback mechanism
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()  # Placeholder for visually updating AI's response after events end
        # create a new placeholder for streaming messages and other events, and give it context
        st_callback = get_streamlit_cb(st.empty())
        response = invoke_our_graph(st.session_state.messages, [st_callback])
        last_msg = response["messages"][-1].content
        st.session_state.messages.append(AIMessage(content=last_msg))  # Add that last message to the st_message_state
        msg_placeholder.write(last_msg) # visually refresh the complete response after the callback container





