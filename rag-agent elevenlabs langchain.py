import getpass
import chromadb
import os
import speech_recognition as sr
from elevenlabs import generate, set_api_key, stream
import bs4
from langchain import hub
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

os.environ["OPENAI_API_KEY"] = getpass.getpass('OpenAI API Key: 9ea1ee7db09a5fe4db9eabadedcbae24')

#LangSmith for logging and evaluation
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "rag-agent"
os.environ["LANGCHAIN_API_KEY"] = getpass.getpass()

#Load documents in data folder
loader = DirectoryLoader(os.path.join(os.path.abspath(''), "data"), glob="**/*.md", loader_cls=PyPDFLoader, silent_errors=True, show_progress=True)
context_docs = loader.load()

#Can test semantic chunking vs recursively split by character vs split by tokens

#Split by token
text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=100, chunk_overlap=0
)
all_splits = text_splitter.split_documents(context_docs)

#Semantic Chunking
text_splitter = SemanticChunker(OpenAIEmbeddings())
all_splits = text_splitter.create_documents(context_docs)

vectorstore = Chroma.from_document(documents=all_splits, embedding=OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
prompt = '''You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
Question: {question} 
Context: {context} 
Answer: '''

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

rag_chain.invoke("Is my company's information kept secret")

vectorstore.delete_collection()

# Recog = sr.Recognizer()


# WELCOME_MSG = "Welcome to the Maritime Innovation Center! How may I assist you today?"
# GOODBYE_MSG = "Thank you for visiting the Maritime Innovation Center! We hope to see you again!"
# ERROR_MSG = "Sorry, I am unable to answer your question given the current context. Would you mind providing more context on your query?"
# FINAL_ERROR_MSG = "Sorry, I am unable to find an appropriate answer to your query. Please rephrase your query or ask another question. Thank you!"
# TIMEOUT_SECS = 30

# test_questions = ["May I get a time extension please?",
#                   "Can you give me more information about Section H of the Maritime Census?",
#                   "Can I update my contact details?",
#                   "Why does MPA conduct the Maritime Census?",
#                   "Is my company's information kept confidential?"]

# def start_chat():
#     with open("chat_log.txt", "a") as file:
#         file.write("\n\nNew Chat\n")
#     start_time = time.perf_counter()

#     assistant = RetrieveAssistantAgent(
#         name="assistant",
#         system_message="You are a helpful and cheerful human assistant. Your job is to answer queries about the Maritime Census.",
#         llm_config=LLM_CONFIG,
#     )

#     ragproxyagent = RetrieveUserProxyAgent(
#         name="ragproxyagent",
#         human_input_mode="NEVER",
#         max_consecutive_auto_reply=0,
#         retrieve_config=RETRIEVE_CONFIG,
#         code_execution_config=False, # set to False if you don't want to execute the code
#     )

#     critic = autogen.AssistantAgent(
#         name="critic",
#         system_message=''' You are a helpful assistant.
#         ''',
#         llm_config=LLM_CONFIG,
#     )

#     #Reset all agents
#     assistant.reset()
#     ragproxyagent.reset()
#     critic.reset()
    
#     # Runs chat with user
#     user_question = askfor_userVoiceInput(WELCOME_MSG)
#     user_start_time = time.perf_counter()
#     if (user_question == "user_timeout"):
#         return user_question

#     message = f"""expand the following question to add more relevant questions. think of the most relevant supplementary question and combine it with the original question. Only return the combined question as a singular question.
#     \n
#     Question: '{user_question}'
#     """

#     ragproxyagent.initiate_chat(critic, problem=message, silent=True)

#     expanded_message = ragproxyagent.last_message(critic)['content']
#     with open("chat_log.txt", "a") as file:
#         file.write("User question: " + user_question + "\n")
#         file.write("Expanded message: " + expanded_message + "\n")

#     problem = f"""
#     Always say if you are not sure of some parts of the question. Answer the question in a full sentence. Keep your answer brief but informative.
#     If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

#     Question: "{expanded_message}"
#     """

#     ragproxyagent.initiate_chat(assistant, problem=problem, silent=True)
#     answer = assistant.last_message(ragproxyagent)['content']
#     if (answer == ERROR_MSG):
#         with open("chat_log.txt", "a") as file:
#             file.write("ERROR_MSG")
#         new_question = askfor_userVoiceInput(ERROR_MSG)
#         if (new_question == "user_timeout"):
#             return new_question
#         new_message = f"""expand the following question to add more relevant questions. think of the 5 most relevant supplementary questions, select the top 1 question and add it to the original question. The original question must be part of the final question. Only return the final question.
#         \n
#         Question: '{new_question}'
#         """

#         ragproxyagent.initiate_chat(critic, problem=new_message, silent=True)

#         expanded_message = ragproxyagent.last_message(critic)['content']

#         problem = f"""Always say if you are not sure of some parts of the question. Answer the question in a full sentence. Keep your answer brief but informative.
#         If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

#         Question: "{expanded_message}"
#         """

#         ragproxyagent.initiate_chat(assistant, problem=problem, silent=True)
#         final_answer = assistant.last_message(ragproxyagent)['content']
#         if (final_answer == ERROR_MSG):
#             SpeakText(FINAL_ERROR_MSG)
#             with open("chat_log.txt", "a") as file:
#                 file.write("FINAL_ERROR_MSG")
#             return FINAL_ERROR_MSG
#         else:
#             SpeakText(final_answer)
#             return final_answer
#     else:
#         response_time = str(time.perf_counter()-user_start_time)
#         print("Response time: " + response_time)
#         SpeakText(answer)
#         with open("chat_log.txt", "a") as file:
#             file.write("Final Answer: " + answer + "\n")
#             file.write("Response Time: " + response_time + "s\n")
#         return answer

# def SpeakText(inputText):
#     audio_stream = generate(
#         text=inputText,
#         voice="Serena",
#         model="eleven_turbo_v2",
#         stream=True
#     )

#     stream(audio_stream)

# def askfor_userVoiceInput(question):
#     SpeakText(question)
#     print("Start speaking!")
#     start_userVoiceTime = time.perf_counter()
#     while (True):
#         if (time.perf_counter() - start_userVoiceTime > TIMEOUT_SECS):
#             break
#         try:
#             # Use Microphone as source for input
#             with sr.Microphone() as source:

#                 # Wait for a second to let the recognier adjust the energy threhold based on the surrounding noise level
#                 Recog.adjust_for_ambient_noise(source, duration=0.2)
                
#                 # Listen for user voice input
#                 audio = Recog.listen(source, timeout=30)
                    
#                 # Use google to recognize audio
#                 userVoiceInput = Recog.recognize_google(audio)
#                 userVoiceInput = userVoiceInput.lower()
#                 return userVoiceInput
            
#         except sr.RequestError as e:
#             print("Could not request results; {0}".format(e))

#         except sr.UnknownValueError:
#             print("User is not speaking: " + str(time.perf_counter() - start_userVoiceTime))
#             continue

#     return "user_timeout"

# def main():
#     timeout = False
#     while (timeout == False):
#             output = start_chat()
#             if (output == "user_timeout"):
#                 SpeakText(GOODBYE_MSG)
#                 print("user timed out")
#                 timeout = True
    
        
# main()
