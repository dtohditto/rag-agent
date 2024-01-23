import sys
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject

class BackgroundWorker(QObject):
    update_signal = pyqtSignal(str)

    def background_process(self):
        while True:
            time.sleep(2)
            # Simulate some background processing
            self.update_signal.emit("Background process is running...")

class MyMainWindow(QMainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()

        self.setWindowTitle("Voice Assistant")

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.status_label)

        self.start_background_thread()

        speak_button = QPushButton("Speak", self)
        speak_button.clicked.connect(self.start_speaking)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(speak_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def start_background_thread(self):
        self.background_worker = BackgroundWorker()
        self.background_thread = QThread()

        self.background_worker.moveToThread(self.background_thread)

        # Connect signals and slots
        self.background_worker.update_signal.connect(self.update_gui)
        self.background_thread.started.connect(self.background_worker.background_process)

        # Start the background thread
        self.background_thread.start()

    def update_gui(self, message):
        # Update the GUI on the main thread
        self.status_label.setText(message)

    def start_speaking(self):
        self.update_gui("Speaking...")
        # Your speech synthesis code here
        # ...
        self.update_gui("Speech complete.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    main_window.show()
    sys.exit(app.exec())
