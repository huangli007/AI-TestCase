"""桌面 GUI 独立入口(Windows / macOS 通用)。"""

import sys

from testcase_agent.gui.app import run_app

if __name__ == "__main__":
    sys.exit(run_app())
