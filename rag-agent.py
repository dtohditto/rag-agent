import autogen
from autogen import config_list_from_json
from autogen.retrieve_utils import TEXT_FORMATS
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
import chromadb
import os
import autogen

CONFIG_FILE_NAME = "OAI_CONFIG_LIST.json"
config_list = config_list_from_json(env_or_file=CONFIG_FILE_NAME)
cheap_config_list = autogen.config_list_from_json(
    env_or_file=CONFIG_FILE_NAME,  
    filter_dict={
        "model": {
            "gpt-3.5-turbo",
        }
    }
)

costly_config_list = autogen.config_list_from_json(
    env_or_file=CONFIG_FILE_NAME, 
    filter_dict={
        "model": {
            "gpt-4-1106-preview",
        }
    }
)

LLM_CONFIG = {
    "cache_seed": 42,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": costly_config_list, # Can be amended to either cheap_config_list or costly_config_list
    "timeout": 120, # Default was 120
    # "tools": tools_list, # TESTING: function calling and automated admin 
}

RETRIEVE_CONFIG={
        "task": "qa", # Possible values are "code", "qa" and "default". System prompt will be different for different tasks. The default value is `default`, which supports both code and qa.
        "docs_path": [
            os.path.join(os.path.abspath(''), "data"),
        ],
        # "custom_text_types": ["mdx"], # Default: autogen.retrieve_utils.TEXT_FORMATS = ['txt', 'json', 'csv', 'tsv', 'md', 'html', 'htm', 'rtf', 'rst', 'jsonl', 'log', 'xml', 'yaml', 'yml', 'pdf']
        "chunk_token_size": 2000,
        "model": LLM_CONFIG["config_list"][0]["model"],
        "client": chromadb.PersistentClient(path="/tmp/chromadb"),
        "embedding_model": "all-mpnet-base-v2",
        "get_or_create": True,  # set to False if you don't want to reuse an existing collection, but you'll need to remove the collection manually
        "must_break_at_empty_line": False
    }

CODE_EXECUTION_CONFIG={
        # "code": None,
        "work_dir": "generated_code", # Codes will be saved in this folder, if "save the code to disk." is used in the prompt
        # "filename": "test1.py",
        "use_docker": False
    }

assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful and cheerful assistant. Your job is to answer queries about the Maritime Census.",
    llm_config=LLM_CONFIG,
)

ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=0,
    retrieve_config=RETRIEVE_CONFIG,
    code_execution_config=False, # set to False if you don't want to execute the code
)

critic = autogen.AssistantAgent(
    name="critic",
    system_message=''' You are a helpful assistant.
    ''',
    llm_config=LLM_CONFIG,
)

content = 'Can I check if my request for an extention has been granted?'
message = f"""expand the following question to add more relevant questions. think of the 5 most relevant supplementary questions, select the top 1 question and add it to the original question. Only return the final question.
\n
Question: '{content}'
"""

ragproxyagent.initiate_chat(critic, problem=message)

expanded_message = ragproxyagent.last_message(critic)['content']
print(expanded_message)

problem = f"""Always answer all questions. Always say if you are not sure of some parts of the question. Answer the question in a full sentence.

Question: '{expanded_message}'
"""

assistant.reset() # it says always to reset, but havent read thru to find out more

ragproxyagent.initiate_chat(assistant, problem=problem)
answer = assistant.last_message(ragproxyagent)['content']

print(answer)