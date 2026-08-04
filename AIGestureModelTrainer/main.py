import sys
from PySide6.QtWidgets import QApplication
from ui import GestureTrainerWindow

def main():
    # Initialize the Qt Application
    app = QApplication(sys.argv)
    
    # Create the Main Application Window
    window = GestureTrainerWindow()
    window.show()
    
    # Run the Application Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
