import autogen
from autogen import config_list_from_json
from autogen.retrieve_utils import TEXT_FORMATS
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
import chromadb
import os
import autogen
import time
import speech_recognition as sr
from elevenlabs import generate, set_api_key, stream

set_api_key("9ea1ee7db09a5fe4db9eabadedcbae24")

os.environ["TOKENIZERS_PARALLELISM"] = "false"

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

Recog = sr.Recognizer()


WELCOME_MSG = "Welcome to the Maritime Innovation Center! How may I assist you today?"
GOODBYE_MSG = "Thank you for visiting the Maritime Innovation Center! We hope to see you again!"
ERROR_MSG = "Sorry, I am unable to answer your question given the current context. Would you mind providing more context on your query?"
FINAL_ERROR_MSG = "Sorry, I am unable to find an appropriate answer to your query. Please rephrase your query or ask another question. Thank you!"
TIMEOUT_SECS = 30

test_questions = ["May I get a time extension please?",
                  "Can you give me more information about Section H of the Maritime Census?",
                  "Can I update my contact details?",
                  "Why does MPA conduct the Maritime Census?",
                  "Is my company's information kept confidential?"]

def start_chat():
    with open("chat_log.txt", "a") as file:
        file.write("\n\nNew Chat\n")
    start_time = time.perf_counter()

    assistant = RetrieveAssistantAgent(
        name="assistant",
        system_message="You are a helpful and cheerful human assistant. Your job is to answer queries about the Maritime Census.",
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

    #Reset all agents
    assistant.reset()
    ragproxyagent.reset()
    critic.reset()
    
    # Runs chat with user
    user_question = askfor_userVoiceInput(WELCOME_MSG)
    user_start_time = time.perf_counter()
    if (user_question == "user_timeout"):
        return user_question

    message = f"""expand the following question to add more relevant questions. think of the most relevant supplementary question and combine it with the original question. Only return the combined question as a singular question.
    \n
    Question: '{user_question}'
    """

    ragproxyagent.initiate_chat(critic, problem=message, silent=True)

    expanded_message = ragproxyagent.last_message(critic)['content']
    with open("chat_log.txt", "a") as file:
        file.write("User question: " + user_question + "\n")
        file.write("Expanded message: " + expanded_message + "\n")

    problem = f"""
    Always say if you are not sure of some parts of the question. Answer the question in a full sentence. Keep your answer brief but informative.
    If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

    Question: "{expanded_message}"
    """

    ragproxyagent.initiate_chat(assistant, problem=problem, silent=True)
    answer = assistant.last_message(ragproxyagent)['content']
    if (answer == ERROR_MSG):
        with open("chat_log.txt", "a") as file:
            file.write("ERROR_MSG")
        new_question = askfor_userVoiceInput(ERROR_MSG)
        if (new_question == "user_timeout"):
            return new_question
        new_message = f"""expand the following question to add more relevant questions. think of the 5 most relevant supplementary questions, select the top 1 question and add it to the original question. The original question must be part of the final question. Only return the final question.
        \n
        Question: '{new_question}'
        """

        ragproxyagent.initiate_chat(critic, problem=new_message, silent=True)

        expanded_message = ragproxyagent.last_message(critic)['content']

        problem = f"""Always say if you are not sure of some parts of the question. Answer the question in a full sentence. Keep your answer brief but informative.
        If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

        Question: "{expanded_message}"
        """

        ragproxyagent.initiate_chat(assistant, problem=problem, silent=True)
        final_answer = assistant.last_message(ragproxyagent)['content']
        if (final_answer == ERROR_MSG):
            SpeakText(FINAL_ERROR_MSG)
            with open("chat_log.txt", "a") as file:
                file.write("FINAL_ERROR_MSG")
            return FINAL_ERROR_MSG
        else:
            SpeakText(final_answer)
            return final_answer
    else:
        response_time = str(time.perf_counter()-user_start_time)
        print("Response time: " + response_time)
        SpeakText(answer)
        with open("chat_log.txt", "a") as file:
            file.write("Final Answer: " + answer + "\n")
            file.write("Response Time: " + response_time + "s\n")
        return answer

def SpeakText(inputText):
    audio_stream = generate(
        text=inputText,
        voice="Serena",
        model="eleven_turbo_v2",
        stream=True
    )

    stream(audio_stream)

def askfor_userVoiceInput(question):
    SpeakText(question)
    print("Start speaking!")
    start_userVoiceTime = time.perf_counter()
    while (True):
        if (time.perf_counter() - start_userVoiceTime > TIMEOUT_SECS):
            break
        try:
            # Use Microphone as source for input
            with sr.Microphone() as source:

                # Wait for a second to let the recognier adjust the energy threhold based on the surrounding noise level
                Recog.adjust_for_ambient_noise(source, duration=0.2)
                
                # Listen for user voice input
                audio = Recog.listen(source, timeout=30)
                    
                # Use google to recognize audio
                userVoiceInput = Recog.recognize_google(audio)
                userVoiceInput = userVoiceInput.lower()
                return userVoiceInput
            
        except sr.RequestError as e:
            print("Could not request results; {0}".format(e))

        except sr.UnknownValueError:
            print("User is not speaking: " + str(time.perf_counter() - start_userVoiceTime))
            continue

    return "user_timeout"

def main():
    timeout = False
    while (timeout == False):
            output = start_chat()
            if (output == "user_timeout"):
                SpeakText(GOODBYE_MSG)
                print("user timed out")
                timeout = True
    
        
main()
