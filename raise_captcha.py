#!/usr/bin/env python3
"""
Simple Math Captcha UI
A PySide6 application that presents simple math questions for verification.
Falls back to console mode if GUI is not available.

Usage:
    python raise_captcha.py          # Try GUI, fallback to console
    python raise_captcha.py --console # Force console mode
"""

import argparse
import os
import random
import sys


class MathCaptcha:
    """Simple math captcha UI with random questions."""

    def __init__(self, use_gui=True):
        """Initialize the captcha with math questions."""
        # Dictionary of easy math questions and their answers
        self.questions = {
            "2 + 3": 5,
            "7 - 4": 3,
            "5 × 2": 10,
            "8 ÷ 2": 4,
            "6 + 1": 7,
            "9 - 3": 6,
            "3 × 4": 12,
            "15 ÷ 3": 5,
            "4 + 6": 10,
            "12 - 5": 7,
            "2 × 6": 12,
            "18 ÷ 6": 3,
            "5 + 5": 10,
            "10 - 4": 6,
            "7 × 1": 7,
        }

        self.current_question = None
        self.current_answer = None
        self.attempts = 0
        self.max_attempts = 3
        self.use_gui = use_gui
        self.app = None
        self.window = None

        if self.use_gui:
            self.setup_ui()
        self.new_question()

    def setup_ui(self):
        """Create and configure the UI elements using PySide6."""
        try:
            # Set Qt platform plugins as fallback options if xcb fails
            if "QT_QPA_PLATFORM" not in os.environ:
                # Try xcb first, then wayland, then offscreen as fallbacks
                os.environ["QT_QPA_PLATFORM"] = "xcb"

            from PySide6.QtCore import Qt
            from PySide6.QtGui import QFont
            from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

            # Create application instance
            self.app = QApplication.instance()
            if self.app is None:
                self.app = QApplication(sys.argv)

            # Create main window
            self.window = QMainWindow()
            self.window.setWindowTitle("Math Captcha")
            self.window.setFixedSize(400, 250)

            # Center the window
            self.center_window()

            # Create central widget and main layout
            central_widget = QWidget()
            self.window.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setSpacing(20)
            main_layout.setContentsMargins(20, 20, 20, 20)

            # Title
            title_label = QLabel("Math Captcha Verification")
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title_label)

            # Question label
            self.question_label = QLabel("")
            question_font = QFont()
            question_font.setPointSize(14)
            self.question_label.setFont(question_font)
            self.question_label.setAlignment(Qt.AlignCenter)
            self.question_label.setStyleSheet("color: blue;")
            main_layout.addWidget(self.question_label)

            # Answer input layout
            answer_layout = QHBoxLayout()
            answer_label = QLabel("Answer:")
            answer_font = QFont()
            answer_font.setPointSize(12)
            answer_label.setFont(answer_font)

            self.answer_entry = QLineEdit()
            self.answer_entry.setFont(answer_font)
            self.answer_entry.setMaximumWidth(100)
            self.answer_entry.setAlignment(Qt.AlignCenter)
            self.answer_entry.returnPressed.connect(self.check_answer)

            answer_layout.addStretch()
            answer_layout.addWidget(answer_label)
            answer_layout.addWidget(self.answer_entry)
            answer_layout.addStretch()
            main_layout.addLayout(answer_layout)

            # Buttons layout
            button_layout = QHBoxLayout()

            self.submit_btn = QPushButton("Submit")
            self.submit_btn.setFont(answer_font)
            self.submit_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 20px;")
            self.submit_btn.clicked.connect(self.check_answer)

            self.new_question_btn = QPushButton("New Question")
            self.new_question_btn.setFont(answer_font)
            self.new_question_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 20px;")
            self.new_question_btn.clicked.connect(self.new_question)

            button_layout.addStretch()
            button_layout.addWidget(self.submit_btn)
            button_layout.addWidget(self.new_question_btn)
            button_layout.addStretch()
            main_layout.addLayout(button_layout)

            # Status label
            self.status_label = QLabel("")
            status_font = QFont()
            status_font.setPointSize(10)
            self.status_label.setFont(status_font)
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("color: gray;")
            main_layout.addWidget(self.status_label)

            # Focus on entry
            self.answer_entry.setFocus()

        except (ImportError, OSError, RuntimeError) as e:
            print(f"Warning: Could not initialize PySide6 GUI: {e}")
            self._try_fallback_platforms()
        except Exception as e:
            # Catch any other GUI-related errors including display issues
            if any(keyword in str(e).lower() for keyword in ["xcb", "display", "qt", "platform"]):
                print(f"Display/Qt platform error: {e}")
                self._try_fallback_platforms()
            else:
                print(f"Warning: Could not initialize GUI: {e}")
                print("Falling back to console mode...")
                self.use_gui = False
                self.app = None
                self.window = None

    def center_window(self):
        """Center the window on the screen."""
        if self.window:
            screen = self.app.primaryScreen().geometry()
            window_geometry = self.window.frameGeometry()
            center = screen.center()
            window_geometry.moveCenter(center)
            self.window.move(window_geometry.topLeft())

    def new_question(self):
        """Generate a new random question."""
        self.current_question, self.current_answer = random.choice(list(self.questions.items()))

        if self.use_gui and self.window:
            self.question_label.setText(f"What is {self.current_question} ?")
            self.answer_entry.clear()
            self.status_label.setText(f"Attempts remaining: {self.max_attempts - self.attempts}")
            self.answer_entry.setFocus()
        else:
            print(f"\nMath Captcha: What is {self.current_question} ?")
            print(f"Attempts remaining: {self.max_attempts - self.attempts}")

    def check_answer(self):
        """Check if the provided answer is correct."""
        if self.use_gui and self.window:
            return self._check_answer_gui()
        else:
            return self._check_answer_console()

    def _check_answer_gui(self):
        """PySide6 version of answer checking."""
        try:
            from PySide6.QtWidgets import QMessageBox

            user_answer = int(self.answer_entry.text().strip())

            if user_answer == self.current_answer:
                QMessageBox.information(self.window, "Correct!", "Great! You solved the math problem correctly.\nCaptcha verification successful!")
                self.app.quit()
                return True
            else:
                self.attempts += 1
                remaining = self.max_attempts - self.attempts

                if remaining > 0:
                    QMessageBox.warning(self.window, "Incorrect", f"Wrong answer. You have {remaining} attempts remaining.")
                    self.status_label.setText(f"Attempts remaining: {remaining}")
                    self.status_label.setStyleSheet("color: orange;")
                    self.answer_entry.clear()
                    self.answer_entry.setFocus()
                else:
                    QMessageBox.critical(self.window, "Failed", "Maximum attempts exceeded. Captcha verification failed.")
                    self.app.quit()
                    return False

        except ValueError:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self.window, "Invalid Input", "Please enter a valid number.")
            self.answer_entry.clear()
            self.answer_entry.setFocus()

    def _check_answer_console(self):
        """Console version of answer checking."""
        try:
            user_input = input("Enter your answer: ").strip()
            user_answer = int(user_input)

            if user_answer == self.current_answer:
                print("✓ Correct! Captcha verification successful!")
                return True
            else:
                self.attempts += 1
                remaining = self.max_attempts - self.attempts

                if remaining > 0:
                    print(f"✗ Wrong answer. You have {remaining} attempts remaining.")
                    return self._retry_console()
                else:
                    print("✗ Maximum attempts exceeded. Captcha verification failed.")
                    return False

        except ValueError:
            print("✗ Invalid input. Please enter a valid number.")
            return self._retry_console()
        except (EOFError, KeyboardInterrupt):
            print("\nCaptcha verification cancelled.")
            return False

    def _retry_console(self):
        """Handle retry in console mode."""
        if self.attempts < self.max_attempts:
            retry = input("Try again? (y/n): ").strip().lower()
            if retry in ["y", "yes", ""]:
                return self.check_answer()
        return False

    def run(self):
        """Start the captcha UI or console interface."""
        if self.use_gui and self.window:
            try:
                self.window.show()
                result = self.app.exec()
                return self.attempts < self.max_attempts
            except Exception as e:
                print(f"GUI error: {e}")
                print("Falling back to console mode...")
                self.use_gui = False
                return self.run()
        else:
            # Console mode
            print("=== Math Captcha Verification (Console Mode) ===")
            while self.attempts < self.max_attempts:
                if self.check_answer():
                    return True
                if self.attempts < self.max_attempts:
                    self.new_question()
            return False

    def _try_fallback_platforms(self):
        """Try alternative Qt platforms as fallback."""
        fallback_platforms = ["wayland", "offscreen", "minimal"]

        for platform in fallback_platforms:
            try:
                print(f"Trying Qt platform: {platform}")
                os.environ["QT_QPA_PLATFORM"] = platform

                # Clear any existing app instance
                if self.app:
                    self.app.quit()
                    self.app = None

                # Reimport and retry
                from PySide6.QtWidgets import QApplication

                self.app = QApplication(sys.argv)

                # If we reach here, the platform worked
                print(f"Successfully initialized Qt with {platform} platform")

                # Continue with offscreen mode or minimal GUI
                if platform == "offscreen":
                    print("Using offscreen mode - falling back to console interface")
                    self.use_gui = False
                    self.app = None
                    self.window = None
                    return
                else:
                    # Try to continue with GUI setup
                    from PySide6.QtWidgets import QMainWindow

                    self.window = QMainWindow()
                    return

            except Exception as e:
                print(f"Platform {platform} failed: {e}")
                continue

        # If all platforms failed, fall back to console
        print("All Qt platforms failed - falling back to console mode")
        self.use_gui = False
        self.app = None
        self.window = None


def detect_display_available():
    """Check if display is available for GUI applications."""
    if os.name == "nt":  # Windows
        return True

    # Check for DISPLAY environment variable (Linux/Unix)
    display = os.environ.get("DISPLAY", "")
    if not display:
        return False

    # Check if we're in a headless environment
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return False

    # Check for SSH connection without X11 forwarding
    if os.environ.get("SSH_CONNECTION") and not os.environ.get("SSH_X11_FORWARDING"):
        return False

    # Check for specific environment variables that indicate no GUI
    if os.environ.get("TERM") == "dumb" or os.environ.get("DEBIAN_FRONTEND") == "noninteractive":
        return False

    # Force console mode if requested
    if os.environ.get("FORCE_CONSOLE_MODE") or "--console" in sys.argv:
        return False

    # Check if we're in a container or virtual environment
    if os.path.exists("/.dockerenv") or os.environ.get("container"):
        return False

    # Check for WSL (Windows Subsystem for Linux) without X server
    if os.environ.get("WSL_DISTRO_NAME") and not os.environ.get("DISPLAY"):
        return False

    # Try to detect if required Qt/xcb libraries are available
    try:
        # Quick test to see if we can import PySide6 without errors
        import subprocess

        result = subprocess.run(["python3", "-c", 'import PySide6.QtWidgets; print("OK")'], capture_output=True, timeout=5, text=True)
        if result.returncode != 0 or "OK" not in result.stdout:
            print("PySide6 import test failed, using console mode")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        print("Could not test PySide6 availability, using console mode")
        return False

    # Basic display variable format check
    if display and ":" in display:
        return True

    return False


def main():
    """Main function to run the math captcha."""
    parser = argparse.ArgumentParser(description="Math Captcha Verification")
    parser.add_argument("--console", action="store_true", help="Force console mode (no GUI)")
    args = parser.parse_args()

    print("Starting Math Captcha...")

    # Set environment to prevent XCB threading issues
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    # Detect if GUI is available (unless forced to console)
    gui_available = not args.console and detect_display_available()

    if not gui_available:
        print("Using console mode")
    else:
        print("Attempting to use PySide6 GUI mode")

    try:
        captcha = MathCaptcha(use_gui=gui_available)
        success = captcha.run()

        if success:
            print("Captcha verification successful!")
            sys.exit(0)
        else:
            print("Captcha verification failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Error running captcha: {e}")
        # If GUI failed, try console mode as fallback
        if gui_available:
            print("Falling back to console mode due to error...")
            try:
                captcha = MathCaptcha(use_gui=False)
                success = captcha.run()
                if success:
                    print("Captcha verification successful!")
                    sys.exit(0)
                else:
                    print("Captcha verification failed!")
                    sys.exit(1)
            except Exception as fallback_error:
                print(f"Console fallback also failed: {fallback_error}")
                sys.exit(1)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
