#!/usr/bin/env python3
"""
Utils - 工具函数模块
统一工具函数，供多平台注册机共享
"""

import csv
import json
import logging
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import Config


# ─────────────────────────────────────────────────────────────────────────────
# Logger setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    log_file = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Account persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_account_info(
    account_info: Dict[str, Any],
    filename: str = "accounts.json",
    platform: str = "gpt",
) -> bool:
    """保存账号信息到 JSON 文件"""
    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

        existing_data: List[Dict[str, Any]] = []
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                existing_data = raw if isinstance(raw, list) else []
            except (json.JSONDecodeError, IOError):
                existing_data = []

        account_info = account_info.copy()
        account_info["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        account_info["platform"] = platform
        existing_data.append(account_info)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        return True

    except IOError as e:
        print(f"保存账号信息失败: {e}")
        return False


def save_account_info_csv(
    account_info: Dict[str, Any],
    filename: str = "accounts.csv",
    platform: str = "gpt",
) -> bool:
    """保存账号信息到 CSV 文件"""
    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

        fieldnames = [
            "email", "password", "status", "platform",
            "created_at", "saved_at", "session_token", "email_verified",
        ]

        existing_data: List[Dict[str, str]] = []
        file_exists = os.path.exists(filename)

        if file_exists:
            try:
                with open(filename, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    existing_data = list(reader)
            except (csv.Error, IOError):
                existing_data = []

        account_info = account_info.copy()
        account_info["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        account_info["platform"] = platform
        existing_data.append({k: account_info.get(k, "") for k in fieldnames})

        with open(filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_data)

        return True

    except IOError as e:
        print(f"保存账号信息到CSV失败: {e}")
        return False


def save_account_info_txt(
    account_info: Dict[str, Any],
    filename: str = "accounts.txt",
    platform: str = "gpt",
) -> bool:
    """保存账号信息到文本文件"""
    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

        account_info = account_info.copy()
        account_info["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        account_info["platform"] = platform

        info_text = f"""
{'='*60}
账号信息 - {account_info['email']}
{'='*60}
平台:    {account_info.get('platform', 'N/A')}
邮箱:    {account_info.get('email', 'N/A')}
密码:    {account_info.get('password', 'N/A')}
状态:    {account_info.get('status', 'N/A')}
邮箱验证: {account_info.get('email_verified', 'N/A')}
创建时间: {account_info.get('created_at', 'N/A')}
保存时间: {account_info.get('saved_at', 'N/A')}
{'='*60}

"""
        with open(filename, "a", encoding="utf-8") as f:
            f.write(info_text)

        return True

    except IOError as e:
        print(f"保存账号信息到文本失败: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Account loading & queries
# ─────────────────────────────────────────────────────────────────────────────

def load_accounts(filename: str = "accounts.json") -> List[Dict[str, Any]]:
    """加载保存的账号信息"""
    try:
        if not os.path.exists(filename):
            return []

        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, IOError) as e:
        print(f"加载账号信息失败: {e}")
        return []


def load_accounts_by_platform(
    filename: str = "accounts.json",
    platform: str = "gpt",
) -> List[Dict[str, Any]]:
    """只加载指定平台的账号"""
    accounts = load_accounts(filename)
    return [acc for acc in accounts if acc.get("platform") == platform]


def check_duplicate_account(email: str, filename: str = "accounts.json") -> bool:
    """检查账号是否已存在"""
    accounts = load_accounts(filename)
    return any(acc.get("email") == email for acc in accounts)


def get_statistics(filename: str = "accounts.json") -> Dict[str, Any]:
    """获取账号统计信息"""
    accounts = load_accounts(filename)
    total = len(accounts)
    active = sum(1 for acc in accounts if acc.get("status") == "active")
    inactive = total - active

    # 按平台统计
    platforms: Dict[str, int] = {}
    for acc in accounts:
        p = acc.get("platform", "unknown")
        platforms[p] = platforms.get(p, 0) + 1

    # 按日期统计
    creation_dates: Dict[str, int] = {}
    for acc in accounts:
        date = acc.get("created_at", "").split()[0] if acc.get("created_at") else "N/A"
        creation_dates[date] = creation_dates.get(date, 0) + 1

    return {
        "total_accounts": total,
        "active_accounts": active,
        "inactive_accounts": inactive,
        "platforms": platforms,
        "creation_dates": creation_dates,
        "success_rate": round(active / total * 100, 1) if total > 0 else 0,
    }


def print_statistics(stats: Dict[str, Any]) -> None:
    """打印统计信息"""
    print(f"""
📊 账号统计信息
{'='*40}
📝 总账号数:   {stats['total_accounts']}
🟢 活跃账号:   {stats['active_accounts']}
🔴 非活跃账号: {stats['inactive_accounts']}
📈 成功率:    {stats['success_rate']}%
{'='*40}
""")

    platforms = stats.get("platforms", {})
    if platforms:
        print("🔗 平台分布:")
        for platform, count in sorted(platforms.items()):
            emoji = "🤖" if platform == "gpt" else "⚡" if platform == "grok" else "📦"
            print(f"   {emoji} {platform.upper()}: {count} 个账号")

    creation_dates = stats.get("creation_dates", {})
    if creation_dates:
        print("\n📅 创建时间分布:")
        for date, count in sorted(creation_dates.items()):
            print(f"   {date}: {count} 个账号")


# ─────────────────────────────────────────────────────────────────────────────
# Backup & cleanup
# ─────────────────────────────────────────────────────────────────────────────

def generate_backup_filename(base_filename: str) -> str:
    """生成备份文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(base_filename)
    return f"{name}_backup_{timestamp}{ext}"


def backup_accounts(filename: str = "accounts.json") -> Optional[str]:
    """备份账号文件"""
    try:
        if not os.path.exists(filename):
            print(f"文件 {filename} 不存在，无需备份")
            return None

        backup_filename = generate_backup_filename(filename)
        shutil.copy2(filename, backup_filename)
        print(f"✅ 备份完成: {backup_filename}")
        return backup_filename

    except IOError as e:
        print(f"备份失败: {e}")
        return None


def clear_old_accounts(
    filename: str = "accounts.json",
    days_to_keep: int = 30,
) -> int:
    """清理旧的账号记录"""
    try:
        accounts = load_accounts(filename)
        cutoff = datetime.now().timestamp() - days_to_keep * 86400

        filtered: List[Dict[str, Any]] = []
        removed = 0

        for account in accounts:
            created = account.get("created_at", "")
            try:
                if created:
                    ts = datetime.strptime(created, "%Y-%m-%d %H:%M:%S").timestamp()
                    if ts >= cutoff:
                        filtered.append(account)
                    else:
                        removed += 1
                else:
                    filtered.append(account)
            except ValueError:
                filtered.append(account)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)

        print(f"✅ 清理完成，移除了 {removed} 个旧账号记录")
        return removed

    except (IOError, OSError) as e:
        print(f"清理旧账号失败: {e}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_email_format(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> Dict[str, bool]:
    """验证密码强度"""
    return {
        "has_uppercase": any(c.isupper() for c in password),
        "has_lowercase": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(not c.isalnum() for c in password),
        "is_long_enough": len(password) >= 8,
        "is_strong": bool(re.search(r"[A-Z]", password))
        and bool(re.search(r"[a-z]", password))
        and bool(re.search(r"\d", password))
        and len(password) >= 8,
    }


def mask_sensitive_info(info: str, visible_chars: int = 4) -> str:
    """隐藏敏感信息，中间部分用 * 替代"""
    if not info or len(info) <= visible_chars * 2:
        return info
    masked_len = len(info) - visible_chars * 2
    return info[:visible_chars] + "*" * masked_len + info[-visible_chars:]


def extract_verification_link(text: str) -> Optional[str]:
    """从文本中提取验证链接（通用版）"""
    # 按优先级排列：verify/confirm > x.ai/grok > signup/register
    patterns = [
        # verify/confirm 链接（最优先）
        r"https?://[^\s<>\"']+verify[^\s<>\"']*",
        r"https?://[^\s<>\"']+confirm[^\s<>\"']*",
        # x.ai / grok 专用链接
        r"https?://x\.ai[^\s<>\"']*",
        r"https?://[^\s<>\"']+grok[^\s<>\"']*",
        # 通用的 signup/register 链接
        r"https?://[^\s<>\"']+signup[^\s<>\"']*",
        r"https?://[^\s<>\"']+register[^\s<>\"']*",
        # openai 链接
        r"https?://[^\s<>\"']+openai[^\s<>\"']*",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for link in matches:
            if "cancel" not in link.lower() and len(link) > 10:
                return link[:300]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Module self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running utils self-test...")

    # test logging
    logger = setup_logger("Utils-Test", "DEBUG")
    logger.info("Logger works")

    # test email validation
    assert validate_email_format("test@example.com")
    assert not validate_email_format("invalid-email")

    # test password validation
    result = validate_password_strength("Test1234!")
    assert result["is_strong"], f"Weak password passed: {result}"

    # test masking
    masked = mask_sensitive_info("my_secret_password", 3)
    assert masked.startswith("my_") and masked.endswith("ord")
    assert "secret" not in masked

    print("✅ All utils tests passed")
