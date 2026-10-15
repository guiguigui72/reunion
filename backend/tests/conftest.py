"""测试全局配置。

pytest 会在收集任何测试文件之前自动导入这个文件，所以在这里
设置环境变量是安全的 —— config.py 在模块级就把路径算好了，
必须赶在它被 import 之前。
"""

import os
import tempfile
from pathlib import Path

# 每个测试会话一个全新的临时目录，测试结束不会污染 ~/.reunion/
_TEST_HOME = Path(tempfile.mkdtemp(prefix="reunion-test-"))
os.environ["REUNION_HOME"] = str(_TEST_HOME)