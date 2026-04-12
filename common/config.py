#!/usr/bin/env python3
"""
Config - 配置文件模块
统一配置管理，支持多平台注册机共享
"""

import json
import os
import logging
from typing import Any, Dict, Optional


class Config:
    """配置类"""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "headless": False,
        "proxy": None,
        "register_interval": 30,
        "timeout": 300,
        "max_retries": 3,
        "save_format": "json",
        "accounts_file": "accounts.json",
        "log_level": "INFO",
        "user_agent_rotation": True,
        "proxy_rotation": False,
        "email_service": "random",
        "captcha_solving": False,
        "captcha_api_key": None,
        # 临时邮箱相关
        "temp_mail_timeout": 180,
        "temp_mail_check_interval": 5,
    }

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = self._load_config()
        self._logger: Optional[logging.Logger] = None

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = self.setup_logger("RegistrationMachine", self.get("log_level", "INFO"))
        return self._logger

    @logger.setter
    def logger(self, value: logging.Logger):
        self._logger = value

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config = self.DEFAULT_CONFIG.copy()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载配置文件失败: {e}")

        return config

    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"保存配置文件失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        self.config_data[key] = value
        self.save_config()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """批量更新配置"""
        self.config_data.update(new_config)
        self.save_config()

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config_data.copy()

    def reset_config(self) -> None:
        """重置配置为默认值"""
        self.config_data = self.DEFAULT_CONFIG.copy()
        self.save_config()

    @staticmethod
    def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        if logger.handlers:
            return logger

        # 文件处理器
        log_file = f"{name}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger


# 便捷函数，供其他模块直接调用
_instance: Optional[Config] = None


def get_config(config_file: str = "config.json") -> Config:
    """获取全局配置实例"""
    global _instance
    if _instance is None:
        _instance = Config(config_file)
    return _instance
