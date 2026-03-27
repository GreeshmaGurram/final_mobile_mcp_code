from typing import Optional, Dict, Any
import subprocess
from appium.webdriver import Remote as AppiumRemote


class SharedState:
    def __init__(self):
        self.appium_driver: Optional[AppiumRemote] = None
        self.device_log_process: Optional[subprocess.Popen] = None
        self.current_platform: Optional[str] = None  # "ios" | "android"
        self.current_device: Optional[Dict[str, Any]] = None