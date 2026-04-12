#!/usr/bin/env python3
"""
common - 共享模块
config.py   : 配置管理
utils.py    : 通用工具函数
email_generator.py : 临时邮箱生成
"""

from .config import Config, get_config
from .utils import (
    setup_logger,
    save_account_info,
    save_account_info_csv,
    save_account_info_txt,
    load_accounts,
    load_accounts_by_platform,
    check_duplicate_account,
    get_statistics,
    print_statistics,
    backup_accounts,
    clear_old_accounts,
    validate_email_format,
    validate_password_strength,
    mask_sensitive_info,
    extract_verification_link,
)
from .email_generator import EmailGenerator

__all__ = [
    "Config",
    "get_config",
    "setup_logger",
    "save_account_info",
    "save_account_info_csv",
    "save_account_info_txt",
    "load_accounts",
    "load_accounts_by_platform",
    "check_duplicate_account",
    "get_statistics",
    "print_statistics",
    "backup_accounts",
    "clear_old_accounts",
    "validate_email_format",
    "validate_password_strength",
    "mask_sensitive_info",
    "extract_verification_link",
    "EmailGenerator",
]
