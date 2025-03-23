import ctypes
from ctypes import wintypes
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QMainWindow, QWidget, QHBoxLayout, QPushButton
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor, QIcon
from PyQt6.QtCore import Qt, QPoint, QTimer
import sys
import pyautogui
import win32gui
from pynput import mouse, keyboard
import io
import json

# Constants for Windows API
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

def enable_dark_mode(hwnd):
    # Enable dark mode for the application window using Windows API.
    try:
        # Load the DWM API
        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1)  # Enable dark mode
        dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception as e:
        print(f"Failed to enable dark mode: {e}")


class ScreenshotApp(QMainWindow):
    CONFIG_FILE = "config.json"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soteseg Maze Screenshotter")
        self.setGeometry(100, 100, 800, 600)

        # Load configuration
        self.screenshot_button = self.load_config()

        # Apply a dark mode theme to the application
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;  /* Dark grayish black background */
                color: white;  /* White text */
            }
            QLabel {
                color: white;  /* White text for labels */
            }
            QPushButton {
                background-color: #1e1e1e;  /* Dark button background */
                color: white;  /* White text */
                border: 1px solid #333333;
                padding: 5px;
            }
        """)

        # Main layout
        self.layout = QVBoxLayout()

        # Instruction label
        self.image_label = QLabel("Press 'Mouse4' to take a screenshot.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)

        # Button to customize the screenshot button
        self.customize_button = QPushButton("Customize Screenshot Button")
        self.customize_button.clicked.connect(self.customize_screenshot_button)
        self.layout.addWidget(self.customize_button)

        # Button to revert to the default screenshot button
        self.revert_button = QPushButton("Revert to Default Button")
        self.revert_button.clicked.connect(self.revert_to_default_button)
        self.layout.addWidget(self.revert_button)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Mouse and keyboard listeners for screenshots
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def load_config(self):
        # Load the configuration from a file.
        try:
            with open(self.CONFIG_FILE, "r") as file:
                config = json.load(file)
                return config.get("screenshot_button", "(256, 128, 1)")
        except (FileNotFoundError, json.JSONDecodeError):
            return "(256, 128, 1)"  # Default button

    def save_config(self):
        # Save the configuration to a file.
        with open(self.CONFIG_FILE, "w") as file:
            json.dump({"screenshot_button": self.screenshot_button}, file)

    def customize_screenshot_button(self):
        # Enable customization of the screenshot button.
        self.image_label.setText("Press the key or mouse button you want to use for screenshots.")
        self.mouse_listener.stop()  # Stop the current mouse listener
        self.keyboard_listener.stop()  # Stop the current keyboard listener

        # Temporary state to track if a button has been set
        self.is_setting_button = True

        def on_mouse_click(x, y, button, pressed):
            if pressed and self.is_setting_button:
                self.screenshot_button = str(getattr(button, "value", None))
                self.image_label.setText(f"Screenshot button set to: {button}")
                self.save_config()
                self.is_setting_button = False  # Stop setting the button
                temp_mouse_listener.stop()  # Stop the temporary listener
                self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
                self.mouse_listener.start()
                self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
                self.keyboard_listener.start()

        def on_key_press(key):
            if self.is_setting_button:
                try:
                    if hasattr(key, "char") and key.char is not None:
                        self.screenshot_button = key.char  # Save the character key
                    else:
                        self.screenshot_button = str(key)  # Save special keys like Key.space
                    self.image_label.setText(f"Screenshot button set to: {self.screenshot_button}")
                    self.save_config()
                    self.is_setting_button = False  # Stop setting the button
                    temp_keyboard_listener.stop()  # Stop the temporary listener
                    self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
                    self.mouse_listener.start()
                    self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
                    self.keyboard_listener.start()
                except Exception as e:
                    self.image_label.setText(f"Failed to set key: {e}")
                    self.is_setting_button = False  # Stop setting the button

        # Start temporary listeners for both mouse and keyboard
        temp_mouse_listener = mouse.Listener(on_click=on_mouse_click)
        temp_mouse_listener.start()

        temp_keyboard_listener = keyboard.Listener(on_press=on_key_press)
        temp_keyboard_listener.start()

    def revert_to_default_button(self):
        # Revert to the default screenshot button.
        self.screenshot_button = "(256, 128, 1)"  # Default button
        self.image_label.setText("Screenshot button reverted to default.")
        self.save_config()

    def showEvent(self, event):
        # Enable dark mode for the title bar when the window is shown.
        hwnd = int(self.winId())  # Get the native window handle
        enable_dark_mode(hwnd)  # Use Windows API to enable dark mode
        super().showEvent(event)

    def on_mouse_click(self, x, y, button, pressed):
        # Handle mouse clicks for taking screenshots.
        if pressed and (str(getattr(button, "value", None)) == self.screenshot_button or str(button) == self.screenshot_button):
            self.take_screenshot()

    def on_key_press(self, key):
        # Handle keyboard presses for taking screenshots.
        try:
            # Normalize the key for comparison
            if hasattr(key, "char") and key.char is not None:
                key_value = key.char  # Character keys (e.g., 'a', 'b', '1')
            else:
                key_value = str(key)  # Special keys (e.g., Key.space, Key.enter)

            if key_value == self.screenshot_button:
                # Use QTimer to safely call the screenshot method in the main thread
                QTimer.singleShot(0, self.take_screenshot)
        except Exception as e:
            print(f"Error handling key press: {e}")

    def take_screenshot(self):
        hwnd = win32gui.GetForegroundWindow()  # Get the active window
        client_rect = win32gui.GetClientRect(hwnd)  # Get the client area
        client_offset = win32gui.ClientToScreen(hwnd, (0, 0))  # Get the client area's top-left corner relative to the screen

        client_x, client_y = client_offset
        client_width, client_height = client_rect[2], client_rect[3]  # Extract client area width/height

        # Adjust the screenshot region to capture only the client area
        screenshot = pyautogui.screenshot(region=(client_x, client_y, client_width, client_height))

        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        buffer.seek(0)

        image = QImage()
        image.loadFromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(image)

        # Resize the window to fit the screenshot size (unless the window is already larger)
        self.resize(max(pixmap.width(), 800), max(pixmap.height(), 600))

        # Maintain aspect ratio and center the image
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def closeEvent(self, event):
        # Stop listeners when the application is closed.
        self.mouse_listener.stop()
        self.keyboard_listener.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScreenshotApp()
    window.show()
    sys.exit(app.exec())
