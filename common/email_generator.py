#!/usr/bin/env python3
"""
Email Generator - 临时邮箱生成模块
支持多种临时邮箱服务提供商，统一供多平台注册机使用
"""

import random
import string
import time
from typing import Dict, List, Optional

import requests


class EmailGenerator:
    """临时邮箱生成器"""

    REGULAR_DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com",
        "hotmail.com", "aol.com", "protonmail.com",
    ]

    TEMP_SERVICES = ["temp-mail.org", "10minutemail.com", "guerrillamail.com"]

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_random_email(self, domain: Optional[str] = None) -> str:
        """生成随机普通邮箱（非临时）"""
        if not domain:
            domain = random.choice(self.REGULAR_DOMAINS)
        username_len = random.randint(8, 15)
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=username_len))
        return f"{username}@{domain}"

    def generate_temp_email(self, service: Optional[str] = None) -> Dict[str, str]:
        """生成临时邮箱，返回完整邮箱信息"""
        if not service:
            service = random.choice(self.TEMP_SERVICES)

        if service == "temp-mail.org":
            return self._generate_temp_mail_org()
        elif service == "10minutemail.com":
            return self._generate_10minutemail()
        elif service == "guerrillamail.com":
            return self._generate_guerrillamail()
        else:
            # 降级到随机邮箱
            return {
                "email": self.generate_random_email(),
                "service": service,
                "type": "fallback",
            }

    def get_email_messages(self, email_info: Dict[str, str]) -> List[Dict[str, str]]:
        """获取邮箱中的邮件列表"""
        service = email_info.get("service", "")
        api_url = email_info.get("api_url", "")

        if not api_url:
            return []

        try:
            if service == "temp-mail.org":
                return self._fetch_temp_mail_org_messages(api_url)
            elif service == "guerrillamail.com":
                return self._fetch_guerrillamail_messages(api_url)
            return []
        except requests.RequestException as e:
            print(f"获取邮件失败 [{service}]: {e}")
            return []

    def poll_verification_email(
        self,
        email_info: Dict[str, str],
        keywords: Optional[List[str]] = None,
        timeout: int = 180,
        check_interval: int = 5,
    ) -> Optional[str]:
        """轮询等待验证邮件，返回验证链接"""
        if keywords is None:
            keywords = ["verify", "confirm", "registration"]

        print(f"⏳ 等待验证邮件，邮箱: {email_info.get('email', 'N/A')}")

        start = time.time()
        last_error_time = 0

        while time.time() - start < timeout:
            try:
                messages = self.get_email_messages(email_info)

                for msg in messages:
                    subject = msg.get("subject", "").lower()
                    body = msg.get("body", "") or msg.get("mail_text_only", "") or msg.get("mail_text", "")

                    # 检查关键字匹配
                    if any(kw in subject for kw in keywords):
                        print(f"✅ 找到验证邮件: {msg.get('subject', 'N/A')}")

                        # 提取验证链接
                        from .utils import extract_verification_link
                        link = extract_verification_link(body)
                        if link:
                            return link

                        # 如果 body 中有纯文本验证信息，也返回
                        if body:
                            return body

                elapsed = int(time.time() - start)
                # 每30秒打印一次进度，避免刷屏
                if elapsed - last_error_time >= 30:
                    print(f"   等待中... ({elapsed}秒)")
                    last_error_time = elapsed

            except requests.RequestException as e:
                print(f"   检查邮件时出错: {e}")

            time.sleep(check_interval)

        print("⏰ 等待验证邮件超时")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # temp-mail.org
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_temp_mail_org(self) -> Dict[str, str]:
        """生成 temp-mail.org 邮箱"""
        try:
            # 1. 获取可用域名列表
            resp = self._session.get(
                "https://api.temp-mail.org/request/domains",
                timeout=10,
            )
            resp.raise_for_status()
            domains: List[str] = resp.json()

            if not domains:
                raise ValueError("No domains returned")

            # 随机选一个域名，确保带 @
            domain = domains[0] if domains[0].startswith("@") else "@" + domains[0]

            # 2. 生成随机用户名
            username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{username}{domain}"

            # 3. 构建邮件轮询 URL（格式: /request/mail/id/{full_email}）
            api_url = f"https://api.temp-mail.org/request/mail/id/{email}"

            return {
                "email": email,
                "service": "temp-mail.org",
                "type": "temporary",
                "api_url": api_url,
                "username": username,
                "domain": domain,
            }

        except requests.RequestException as e:
            print(f"生成 temp-mail.org 邮箱失败: {e}")
            return self._fallback_email("temp-mail.org")

    def _fetch_temp_mail_org_messages(self, api_url: str) -> List[Dict[str, str]]:
        """获取 temp-mail.org 邮件"""
        resp = self._session.get(api_url, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 有时候 API 返回单个对象而不是列表
            return [data] if data else []
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # guerrillamail.com
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_guerrillamail(self) -> Dict[str, str]:
        """生成 guerrillamail.com 邮箱"""
        try:
            username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{username}@guerrillamail.com"
            api_url = (
                f"https://www.guerrillamail.com/ajax.php"
                f"?f=get_email_list&offset=0&email_addr={username}"
            )

            return {
                "email": email,
                "service": "guerrillamail.com",
                "type": "temporary",
                "api_url": api_url,
                "username": username,
            }

        except requests.RequestException as e:
            print(f"生成 guerrillamail 邮箱失败: {e}")
            return self._fallback_email("guerrillamail.com")

    def _fetch_guerrillamail_messages(self, api_url: str) -> List[Dict[str, str]]:
        """获取 guerrillamail 邮件"""
        resp = self._session.get(api_url, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("list", []) if isinstance(data, dict) else []

    # ─────────────────────────────────────────────────────────────────────────
    # 10minutemail.com
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_10minutemail(self) -> Dict[str, str]:
        """生成 10minutemail.com 邮箱（需要浏览器操作，降级）"""
        print("⚠️  10minutemail 需要浏览器操作，已降级到 guerrillamail")
        return self._generate_guerrillamail()

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback
    # ─────────────────────────────────────────────────────────────────────────

    def _fallback_email(self, service: str) -> Dict[str, str]:
        """生成降级邮箱"""
        return {
            "email": self.generate_random_email(),
            "service": service,
            "type": "fallback",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Module self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    gen = EmailGenerator()

    print("=== EmailGenerator self-test ===\n")

    # Test random email
    email = gen.generate_random_email()
    print(f"✅ Random email: {email}")

    # Test temp email services
    for svc in EmailGenerator.TEMP_SERVICES:
        try:
            info = gen.generate_temp_email(svc)
            print(f"✅ {svc}: {info['email']} | api_url: {'set' if info.get('api_url') else 'missing'}")
        except Exception as e:
            print(f"❌ {svc}: {e}")

    print("\n=== All tests complete ===")
