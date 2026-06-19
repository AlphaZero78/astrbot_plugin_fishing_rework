from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


class _DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


if "astrbot.api" not in sys.modules:
    astrbot_module = types.ModuleType("astrbot")
    astrbot_module.__path__ = []
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = _DummyLogger()
    astrbot_module.api = api_module
    sys.modules["astrbot"] = astrbot_module
    sys.modules["astrbot.api"] = api_module

    core_module = types.ModuleType("astrbot.core")
    core_module.__path__ = []
    message_module = types.ModuleType("astrbot.core.message")
    message_module.__path__ = []
    components_module = types.ModuleType("astrbot.core.message.components")

    class At:
        def __init__(self, qq=None):
            self.qq = qq

    components_module.At = At
    sys.modules["astrbot.core"] = core_module
    sys.modules["astrbot.core.message"] = message_module
    sys.modules["astrbot.core.message.components"] = components_module


repo_root = Path(__file__).resolve().parents[1]
repo_parent = repo_root.parent
if str(repo_parent) not in sys.path:
    sys.path.insert(0, str(repo_parent))

package = importlib.import_module(repo_root.name)
sys.modules.setdefault("astrbot_plugin_fishing", package)
