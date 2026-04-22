#!/usr/bin/env python3
"""
Email Generator - 临时邮箱生成模块
支持多种临时邮箱服务提供商，统一供多平台注册机使用
"""

import imaplib
import random
import string
import time
import email
from typing import Dict, List, Optional
from email.header import decode_header

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

    # ─────────────────────────────────────────────────────────────────────────
    # Domain Email (Cloudflare Email Routing)
    # ─────────────────────────────────────────────────────────────────────────

    def generate_domain_email(self, domain: str, target_email: str) -> Dict[str, str]:
        """生成域名邮箱（Cloudflare Email Routing）
        所有发到该域名的邮件都会转发到 target_email
        """
        # 随机生成邮箱前缀，避免规律命名被关联
        chars = string.ascii_lowercase + string.digits
        username = "".join(random.choice(chars) for _ in range(random.randint(8, 12)))

        return {
            "email": f"{username}@{domain}",
            "service": "domain-email",
            "type": "domain",
            "domain": domain,
            "target_email": target_email,
            "username": username,
            "api_url": "",  # 域名邮箱不需要轮询API，邮件直接转发到目标邮箱
        }

    def poll_qq_email_verification(
        self,
        qq_email: str,
        authorization_code: str,
        keywords: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        timeout: int = 180,
        check_interval: int = 5,
    ) -> Optional[str]:
        """通过 IMAP 轮询 QQ 邮箱，等待验证邮件
        qq_email: QQ 邮箱地址，如 123456@qq.com
        authorization_code: QQ 邮箱 IMAP 授权码（不是密码）
        allowed_domains: 允许的发件人域名列表，如 ["openai.com"]
        """
        if keywords is None:
            keywords = ["verify", "confirm", "account", "激活", "验证"]
        if allowed_domains is None:
            allowed_domains = []

        print(f"⏳ 等待验证邮件，目标邮箱: {qq_email}")

        start = time.time()
        last_check = 0

        while time.time() - start < timeout:
            try:
                # 连接 QQ 邮箱 IMAP
                mail = imaplib.IMAP4_SSL("imap.qq.com", 993)
                mail.login(qq_email, authorization_code)
                mail.select("INBOX")

                # 搜索最新邮件
                status, messages = mail.search(None, "ALL")
                if status != "OK":
                    mail.logout()
                    time.sleep(check_interval)
                    continue

                mail_ids = messages[0].split()
                # 只检查最近的几封
                recent_ids = mail_ids[-10:] if len(mail_ids) > 10 else mail_ids

                for mail_id in reversed(recent_ids):
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = self._decode_email_subject(msg.get("Subject", ""))
                    sender = msg.get("From", "")

                    # 检查发件人域名
                    sender_lower = sender.lower()
                    domain_ok = True
                    if allowed_domains:
                        domain_ok = any(
                            domain in sender_lower
                            for domain in allowed_domains
                        )

                    # 检查关键字 + 发件人域名
                    if domain_ok and any(kw.lower() in subject.lower() for kw in keywords):
                        print(f"✅ 找到验证邮件: {subject}")
                        print(f"   发件人: {sender}")

                        # 获取邮件正文
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                        break
                                    except:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                            except:
                                pass

                        # 提取验证链接
                        from .utils import extract_verification_link
                        link = extract_verification_link(body)
                        if link:
                            mail.logout()
                            return link

                mail.logout()

            except Exception as e:
                print(f"   检查 QQ 邮箱时出错: {e}")

            time.sleep(check_interval)

        print("⏰ 等待验证邮件超时")
        return None

    def _decode_email_subject(self, subject: str) -> str:
        """解码邮件主题"""
        if not subject:
            return ""
        parts = decode_header(subject)
        result = []
        for part, charset in parts:
            if isinstance(part, bytes):
                charset = charset or "utf-8"
                try:
                    result.append(part.decode(charset, errors="ignore"))
                except:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        return "".join(result)


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
