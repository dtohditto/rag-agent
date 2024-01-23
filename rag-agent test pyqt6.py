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
import pyttsx3
import threading
import tkinter as tk
import sys
from pydub import AudioSegment
from pydub.playback import play
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject

os.environ["TOKENIZERS_PARALLELISM"] = "false"
root = tk.Tk()
root.title("rag-agent")
flashing_label = tk.Label(root, text="Icon", width=10, height=5, relief="solid")
flashing_label.pack(pady=20)

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

class BackgroundWorker(QObject):
    update_signal = pyqtSignal(str)

    def start_chat(self):
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
        user_question = self.askfor_userVoiceInput(WELCOME_MSG)
        if (user_question == "user_timeout"):
            return user_question

        message = f"""expand the following question to add more relevant questions. think of the 5 most relevant supplementary questions, select the top 1 question and add it to the original question. Only return the final question.
        \n
        Question: '{user_question}'
        """

        ragproxyagent.initiate_chat(critic, problem=message)

        expanded_message = ragproxyagent.last_message(critic)['content']
        print(expanded_message)

        problem = f"""Always say if you are not sure of some parts of the question. Answer the question in a full sentence.
        If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

        Question: "{expanded_message}"
        """

        ragproxyagent.initiate_chat(assistant, problem=problem)
        answer = assistant.last_message(ragproxyagent)['content']
        if (answer == ERROR_MSG):
            new_question = self.askfor_userVoiceInput(ERROR_MSG)
            if (new_question == "user_timeout"):
                return new_question
            new_message = f"""expand the following question to add more relevant questions. think of the 5 most relevant supplementary questions, select the top 1 question and add it to the original question. Only return the final question.
            \n
            Question: '{new_question}'
            """

            ragproxyagent.initiate_chat(critic, problem=new_message)

            expanded_message = ragproxyagent.last_message(critic)['content']
            print(expanded_message)

            problem = f"""Always say if you are not sure of some parts of the question. Answer the question in a full sentence.
            If you can't answer the question with or without the current context, you should reply exactly '{ERROR_MSG}'.

            Question: "{expanded_message}"
            """

            ragproxyagent.initiate_chat(assistant, problem=problem)
            final_answer = assistant.last_message(ragproxyagent)['content']
            if (final_answer == ERROR_MSG):
                self.SpeakText(FINAL_ERROR_MSG)
                return FINAL_ERROR_MSG
        else:
            self.SpeakText(answer)
            return answer

    def SpeakText(self, text):
        engine = pyttsx3.init()#nsss on Mac, sapi5 on windows, espeak on every other platform
        engine.save_to_file(text, 'test.wav')
        engine.say(text)
        engine.runAndWait()
        audio_segment = AudioSegment.from_file('test.wav')
        self.analyse_audio_and_flash(flashing_label, audio_segment)

    def askfor_userVoiceInput(self, question):
        self.SpeakText(question)
        print("Start speaking!")
        start_userVoiceTime = time.perf_counter()
        while (True):
            if (time.perf_counter() - start_userVoiceTime > TIMEOUT_SECS):
                break
            try:
                # Use Microphone as source for input
                with sr.Microphone() as source:

                    # Wait for a second to let the recognier adjust the energy threhold based on the surrounding noise level
                    Recog.adjust_for_ambient_noise(source, duration=0.5)
                    
                    # Listen for user voice input
                    audio = Recog.listen(source, timeout=30)
                        
                        
                    # Use google to recognize audio
                    userVoiceInput = Recog.recognize_google(audio)
                    userVoiceInput = userVoiceInput.lower()
                    return userVoiceInput
                
            except sr.RequestError as e:
                print("Could not request results; {0}".format(e))

            except sr.UnknownValueError:
                print("User is not speaking")
                continue

        return "user_timeout"

    def analyse_audio_and_flash(self, label, audio):
        # Analyse audio to get volume level
        rms = audio.rms

        # Adjust brightness based on volume level
        brightness = int(rms/1000)

        # Execute flashing effect based on brightness
        self.flash_icon(label, brightness)

    def flash_icon(self, label, brightness):
        # Implement your flashing effect here using brightness
        # For simplicity, changing background color based on brightness

        # Adjust the factor for brightness mapping as needed
        color_intensity = int(brightness * 2.55)  # Map brightness [0, 100] to [0, 255]

        # Convert color intensity to hexadecimal format
        color_hex = "#{:02X}{:02X}{:02X}".format(color_intensity, color_intensity, color_intensity)

        self.update_signal.emit("bot speaking") 
        # Reset the background color


    def background_process(self):
        timeout = False
        while (timeout == False):
                chat_output = self.start_chat()
                if (chat_output == "user_timeout"):
                    self.SpeakText(GOODBYE_MSG)
                    print("user timed out")
                    timeout = True

# def start_background_thread():
#     background_thread = threading.Thread(target=background_process)
#     background_thread.start()

# def main():
#     start_background_thread()
#     root.mainloop()    
        
# main()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()

        self.setWindowTitle("Voice Assistant")

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.status_label)

        self.start_background_thread()

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def start_background_thread(self):
        self.background_worker = BackgroundWorker()
        self.background_thread = QThread()

        self.background_worker.moveToThread(self.background_thread)

        #Connect signals and slots
        self.background_worker.update_signal.connect(self.update_gui)
        self.background_thread.started.connect(self.background_worker.background_process)

        # Start the background thread
        self.background_thread.start()
    
    def update_gui(self, message):
        # Update gui on main thread
        self.status_label.setText(message)

        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    main_window.show()
    sys.exit(app.exec())