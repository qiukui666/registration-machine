#!/usr/bin/env python3
"""
Grok Register - xAI Grok 账号注册模块
使用 Selenium 自动化注册流程
"""

import imaplib
import email as email_lib
import random
import re
import string
import time
from email.header import decode_header
from typing import Dict, Optional

import requests
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common import (
    Config,
    EmailGenerator,
    check_duplicate_account,
    extract_verification_link,
    setup_logger,
)
from human_mouse import (
    human_click,
    human_delay,
    human_click_element,
    simulate_pre_registration_behavior,
)


class GrokRegister:
    """Grok/xAI 账号注册器"""

    SIGNUP_URL = "https://accounts.x.ai/sign-up?redirect=grok-com"
    GROK_URL = "https://x.ai/grok"

    # 可用于验证邮件的关键字
    VERIFY_KEYWORDS = ["x.ai", "grok", "verify", "激活", "验证"]
    # 必须包含的域名关键字
    VERIFY_DOMAINS = ["x.ai", "grok.com"]

    def __init__(self, config: Config):
        self.config = config
        self.logger = config.logger
        self.driver: Optional[uc.Chrome] = None
        self.max_retries = config.get("max_retries", 3)
        self._ua = UserAgent()

    # ─────────────────────────────────────────────────────────────────────────
    # Browser setup
    # ─────────────────────────────────────────────────────────────────────────

    def setup_driver(self, proxy: Optional[str] = None) -> bool:
        """设置浏览器驱动"""
        for attempt in range(1, self.max_retries + 1):
            try:
                options = uc.ChromeOptions()

                if self.config.get("user_agent_rotation", True):
                    options.add_argument(f"user-agent={self._ua.random}")

                for arg in [
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]:
                    options.add_argument(arg)

                if proxy:
                    options.add_argument(f"--proxy-server={proxy}")

                if self.config.get("headless", False):
                    options.add_argument("--headless")

                self.driver = uc.Chrome(options=options, version_main=None)

                # 强化反检测
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
                    "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});"
                    "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});"
                    "window.chrome = {runtime: {}};".replace("\n", "")
                )

                self.logger.info("浏览器驱动设置完成")
                return True

            except Exception as e:
                self.logger.warning(f"设置驱动失败 (尝试 {attempt}/{self.max_retries}): {e}")
                if attempt == self.max_retries:
                    self.logger.error("设置浏览器驱动最终失败")
                    return False
                time.sleep(2)

        return False

    def teardown_driver(self) -> None:
        """关闭浏览器驱动"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ─────────────────────────────────────────────────────────────────────────
    # Password generation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_password(length: int = 16) -> str:
        """生成随机密码"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(random.choice(chars) for _ in range(length))

    # ─────────────────────────────────────────────────────────────────────────
    # Main registration flow
    # ─────────────────────────────────────────────────────────────────────────

    def register(self, email_info: Dict) -> Optional[Dict]:
        """注册 Grok 账号，带重试机制"""
        email = email_info.get("email", "")
        if not email:
            self.logger.error("无效的邮箱信息")
            return None

        for attempt in range(1, self.max_retries + 1):
            self.logger.info(f"开始注册 Grok 账号: {email} (尝试 {attempt}/{self.max_retries})")

            if not self.setup_driver():
                time.sleep(3)
                continue

            try:
                self.driver.get(self.SIGNUP_URL)
                time.sleep(random.uniform(2, 4))

                # 模拟人类预热行为（滚动、鼠标移动等）
                if self.config.get("human_behavior", True):
                    simulate_pre_registration_behavior(self.driver)

                account_info = self._fill_registration_form(email)

                if account_info:
                    account_info.update(email_info)
                    self.logger.info(f"✅ Grok 账号注册成功: {email}")
                    return account_info

            except WebDriverException as e:
                self.logger.warning(f"WebDriver 错误 ({attempt}/{self.max_retries}): {e}")
                self.teardown_driver()
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"注册失败 ({attempt}/{self.max_retries}): {e}")
                self.teardown_driver()
                time.sleep(2)

        self.logger.error(f"注册最终失败: {email}")
        return None

    def _fill_registration_form(self, email: str) -> Optional[Dict]:
        """填写注册表单（Grok无密码流程）"""
        try:
            wait = WebDriverWait(self.driver, 15)
            time.sleep(random.uniform(1, 2))

            # ── 先点击邮箱注册按钮（如果存在）──
            email_reg_btn = self._find_clickable_button(wait, [
                (By.XPATH, "//button[contains(text(), '使用邮箱注册')]"),
                (By.XPATH, "//button[contains(text(), 'Sign up with Email')]"),
                (By.XPATH, "//button[contains(text(), 'Email')]"),
            ])
            if email_reg_btn:
                human_click(self.driver, email_reg_btn)
                time.sleep(random.uniform(1, 2))

            # ── 定位并填写邮箱 ──
            email_input = self._find_element(wait, [
                (By.CSS_SELECTOR, "[data-testid='email']"),
                (By.NAME, "email"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[autocomplete='email']"),
            ])

            if not email_input:
                self.logger.error("无法定位邮箱输入框")
                return None

            self._human_type_with_move(email_input, email)

            # ── 点击继续按钮 ──
            continue_btn = self._find_clickable_button(wait, [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Continue')]"),
                (By.XPATH, "//button[contains(text(), 'Sign up')]"),
            ])

            if continue_btn:
                human_click(self.driver, continue_btn)
                time.sleep(random.uniform(2, 3))

            # ── 等待验证码输入框出现 ──
            verification_input = self._find_element(wait, [
                (By.CSS_SELECTOR, "[data-testid='otp']"),
                (By.CSS_SELECTOR, "input[maxlength='1']"),
                (By.XPATH, "//input[@placeholder or contains(@class,'code')]"),
                (By.NAME, "code"),
                (By.ID, "code"),
            ])

            if verification_input:
                self.logger.info("检测到验证码输入框，等待验证码...")
                # 等几秒让邮件先发过来（xAI发邮件有延迟）
                time.sleep(random.uniform(5, 8))
                # Grok用域名邮箱，验证码通过IMAP获取
                code = self._wait_for_verification_code(email)
                if code:
                    # 重新查找验证码输入框（页面可能已变化）
                    time.sleep(1)
                    verification_input = self._find_element(wait, [
                        (By.CSS_SELECTOR, "[data-testid='otp']"),
                        (By.CSS_SELECTOR, "input[maxlength='1']"),
                        (By.NAME, "code"),
                        (By.ID, "code"),
                    ])
                    if verification_input:
                        try:
                            verification_input.clear()
                            verification_input.send_keys(code)
                            time.sleep(1)
                            # 点击继续/提交验证码
                            verify_btn = self._find_clickable_button(wait, [
                                (By.CSS_SELECTOR, "button[type='submit']"),
                                (By.XPATH, "//button[contains(text(), 'Continue')]"),
                                (By.XPATH, "//button[contains(text(), 'Verify')]"),
                            ])
                            if verify_btn:
                                human_click(self.driver, verify_btn)
                                time.sleep(random.uniform(2, 3))
                        except Exception as e:
                            self.logger.warning(f"输入验证码失败: {e}")
                else:
                    self.logger.warning("未收到验证码")

            # ── 等待名字+密码输入框出现 ──
            # 验证码提交后需要等待页面上新输入框出现
            time.sleep(5)

            # 用XPATH精确定位可见的输入框
            try:
                # givenName - 名（第二个才是可见的）
                givenName_inputs = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='givenName']")
                givenName_input = None
                for inp in givenName_inputs:
                    if inp.is_displayed():
                        givenName_input = inp
                        break

                if givenName_input:
                    first_name = self._generate_first_name()
                    # 先用JS激活再输入
                    self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].focus();", givenName_input)
                    givenName_input.clear()
                    givenName_input.send_keys(first_name)
                    time.sleep(random.uniform(0.3, 0.6))

                # familyName - 姓
                familyName_input = self._find_element(wait, [
                    (By.CSS_SELECTOR, "[data-testid='familyName']"),
                ])
                if familyName_input and familyName_input.is_displayed():
                    last_name = self._generate_last_name()
                    self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].focus();", familyName_input)
                    familyName_input.clear()
                    familyName_input.send_keys(last_name)
                    time.sleep(random.uniform(0.3, 0.6))

                # 密码
                password = self.generate_password()
                password_input = self._find_element(wait, [
                    (By.CSS_SELECTOR, "[data-testid='password']"),
                ])
                if password_input and password_input.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].focus();", password_input)
                    password_input.clear()
                    password_input.send_keys(password)
                    time.sleep(random.uniform(0.5, 1))
            except Exception as e:
                self.logger.error(f"输入名字密码失败: {e}")

            # 点击完成/创建按钮
            submit_btn = self._find_clickable_button(wait, [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Complete')]"),
                (By.XPATH, "//button[contains(text(), 'Create')]"),
                (By.XPATH, "//button[contains(text(), 'Continue')]"),
            ])
            if submit_btn and submit_btn.is_enabled():
                human_click(self.driver, submit_btn)
                time.sleep(random.uniform(3, 5))

            return self._check_registration_success(email, password)

        except Exception as e:
            self.logger.error(f"填写注册表单失败: {e}")
            return None

    def _wait_for_verification_code(self, email: str, timeout: int = 180) -> Optional[str]:
        """通过IMAP等待并获取验证码"""
        from common import EmailGenerator
        gen = EmailGenerator()

        # 从config获取QQ邮箱信息
        target_email = self.config.get("domain_email", {}).get("target_email", "")
        imap_password = self.config.get("domain_email", {}).get("qq_imap_password", "")

        if not target_email or not imap_password:
            self.logger.error("缺少QQ邮箱IMAP配置")
            return None

        start = time.time()
        check_interval = 3

        while time.time() - start < timeout:
            try:
                self.logger.info(f"连接QQ邮箱 {target_email}...")
                mail = imaplib.IMAP4_SSL("imap.qq.com", 993)
                mail.login(target_email, imap_password)
                mail.select("INBOX")

                status, messages = mail.search(None, "ALL")
                if status == "OK":
                    mail_ids = messages[0].split()
                    self.logger.info(f"收件箱共有 {len(mail_ids)} 封邮件")
                    recent_ids = mail_ids[-10:] if len(mail_ids) > 10 else mail_ids

                    for mail_id in reversed(recent_ids):
                        status, msg_data = mail.fetch(mail_id, "(RFC822)")
                        if status == "OK":
                            raw = msg_data[0][1]
                            msg = email_lib.message_from_bytes(raw)
                            sender = msg.get("From", "")
                            subject = self._decode_email_subject(msg.get("Subject", ""))

                            # 获取邮件正文
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        try:
                                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                        except:
                                            pass
                                        break
                            else:
                                try:
                                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                                except:
                                    pass

                            self.logger.info(f"检查邮件: {subject} | 发件人: {sender}")

                            # 直接从邮件主题提取验证码（如 "65O-N03 xAI confirmation code"）
                            # 主题格式: "XXX-XXX xAI confirmation code"
                            subject_codes = re.findall(r'\b([A-Z0-9]{2,3}-[A-Z0-9]{3})\b', subject)
                            if subject_codes:
                                clean_code = subject_codes[0].replace('-', '')
                                self.logger.info(f"✅ 找到验证码: {clean_code} (邮件: {subject})")
                                mail.logout()
                                return clean_code

                mail.logout()
            except Exception as e:
                self.logger.error(f"IMAP错误: {e}")

            time.sleep(check_interval)

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

    def _generate_first_name(self) -> str:
        """生成随机英文名"""
        first_names = ["James", "John", "Michael", "David", "Robert", "William", "Richard", "Joseph", "Thomas", "Charles", "Emma", "Olivia", "Ava", "Isabella", "Sophia"]
        return random.choice(first_names)

    def _generate_last_name(self) -> str:
        """生成随机英文姓"""
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Wilson", "Moore", "Jackson"]
        return random.choice(last_names)

    def _check_registration_success(self, email: str, password: str) -> Optional[Dict]:
        """检查注册是否成功"""
        try:
            url = self.driver.current_url.lower()

            success_indicators = ["dashboard", "grok", "auth", "chat", "/"]
            failure_indicators = ["signup", "login"]

            if any(ind in url for ind in success_indicators):
                if not any(ind in url for ind in failure_indicators):
                    return {
                        "email": email,
                        "password": password,
                        "status": "active",
                        "platform": "grok",
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "session_token": self._get_session_token(),
                    }

            self._log_page_errors()
            return None

        except Exception as e:
            self.logger.error(f"检查注册状态失败: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Email verification
    # ─────────────────────────────────────────────────────────────────────────

    def verify_email(self, email_info: Dict) -> bool:
        """验证邮箱"""
        service = email_info.get("service", "")
        self.logger.info(f"开始验证邮箱: {email_info.get('email', '')}")

        timeout = self.config.get("temp_mail_timeout", 180)
        check_interval = self.config.get("temp_mail_check_interval", 5)

        if service == "domain-email":
            return self._verify_via_qq_imap(email_info, timeout, check_interval)
        elif service == "temp-mail.org":
            return self._verify_via_api(email_info, timeout, check_interval)
        elif service == "guerrillamail.com":
            return self._verify_via_api(email_info, timeout, check_interval)

        self.logger.warning(f"不支持的邮箱服务: {service}")
        return False

    def _verify_via_qq_imap(self, email_info: Dict, timeout: int, check_interval: int) -> bool:
        """通过 QQ 邮箱 IMAP 轮询验证邮件"""
        target_email = email_info.get("target_email", "")
        imap_password = email_info.get("imap_password", "")

        if not target_email or not imap_password:
            self.logger.error("域名邮箱验证缺少目标邮箱或IMAP密码")
            return False

        from common import EmailGenerator
        gen = EmailGenerator()
        link = gen.poll_qq_email_verification(
            target_email,
            imap_password,
            keywords=self.VERIFY_KEYWORDS,
            allowed_domains=self.VERIFY_DOMAINS,
            timeout=timeout,
            check_interval=check_interval,
        )

        if link:
            self.driver.get(link)
            time.sleep(3)
            return True
        return False

    def _verify_via_api(self, email_info: Dict, timeout: int, check_interval: int) -> bool:
        """通过 API 轮询验证邮箱"""
        api_url = email_info.get("api_url", "")
        start = time.time()

        while time.time() - start < timeout:
            try:
                resp = requests.get(api_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        messages = data.get("list", [])
                    elif isinstance(data, list):
                        messages = data
                    else:
                        messages = []

                    for msg in messages:
                        subject = msg.get("mail_subject", "").lower()
                        if any(kw in subject for kw in self.VERIFY_KEYWORDS):
                            self.logger.info(f"找到验证邮件: {msg.get('mail_subject')}")
                            body = msg.get("mail_text_only", "") or msg.get("mail_text", "")
                            if body:
                                link = extract_verification_link(body)
                                if link:
                                    self.driver.get(link)
                                    time.sleep(3)
                                    return True
            except requests.RequestException as e:
                self.logger.debug(f"检查邮件: {e}")

            time.sleep(check_interval)

        self.logger.warning("等待验证邮件超时")
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Element helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _find_element(self, wait: WebDriverWait, selectors) -> Optional[object]:
        """尝试多个选择器，找到第一个存在的元素"""
        for selector in selectors:
            try:
                return wait.until(EC.presence_of_element_located(selector))
            except TimeoutException:
                continue
        return None

    def _find_clickable_button(self, wait: WebDriverWait, selectors) -> Optional[object]:
        """找到第一个可点击的按钮"""
        for selector in selectors:
            try:
                el = wait.until(EC.element_to_be_clickable(selector))
                if el.is_enabled():
                    return el
            except TimeoutException:
                continue
        return None

    def _human_type(self, element, text: str) -> None:
        """模拟人类输入，避免被检测为机器人"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))
        time.sleep(random.uniform(0.2, 0.5))

    def _human_type_with_move(self, element, text: str) -> None:
        """
        人类方式输入：先移动鼠标到元素，再输入
        集成贝塞尔曲线鼠标轨迹模拟
        """
        # 先移动到元素（带人类轨迹）
        human_click(self.driver, element)
        time.sleep(random.uniform(0.1, 0.2))

        element.clear()
        # 逐字符输入，模拟人类打字
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))
        time.sleep(random.uniform(0.2, 0.5))

    def _log_page_errors(self) -> None:
        """输出页面上的错误信息"""
        error_selectors = [
            ".error-message", ".alert-error", ".alert-danger",
            "[data-error]", "[class*='error']",
        ]
        for selector in error_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        text = el.text.strip()
                        if text:
                            self.logger.error(f"页面错误: {text}")
            except NoSuchElementException:
                pass

    def _get_session_token(self) -> Optional[str]:
        """提取 session token"""
        try:
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                name = cookie["name"].lower()
                if any(x in name for x in ["token", "session", "auth", "csrf"]):
                    value = cookie["value"]
                    if value and len(value) > 5:
                        return value
            return None
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Convenience function
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Convenience function
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_SERVICES = ["guerrillamail.com", "temp-mail.org", "protonmail.com"]
_email_index = 0

def _get_next_email_service():
    global _email_index
    service = EMAIL_SERVICES[_email_index % len(EMAIL_SERVICES)]
    _email_index += 1
    return service


def register_grok_account(
    args,
    config: Config,
    email_gen: EmailGenerator,
) -> Optional[Dict]:
    """生成邮箱并注册 Grok 账号"""
    # 检查是否启用域名邮箱
    domain_config = config.get("domain_email", {})
    if domain_config.get("enabled") and domain_config.get("domain"):
        domain = domain_config.get("domain")
        target_email = domain_config.get("target_email")
        imap_password = domain_config.get("qq_imap_password")
        if domain and target_email:
            email_info = email_gen.generate_domain_email(domain, target_email)
            email_info["imap_password"] = imap_password
        else:
            config.logger.warning("域名邮箱未完整配置，降级到临时邮箱")
            service = _get_next_email_service()
            email_info = email_gen.generate_temp_email(service)
    else:
        service = _get_next_email_service()
        email_info = email_gen.generate_temp_email(service)

    email = email_info.get("email", "")

    if not email:
        config.logger.error("生成邮箱失败")
        return None

    if check_duplicate_account(email):
        config.logger.warning(f"账号已存在，跳过: {email}")
        return None

    config.logger.info(f"生成的邮箱: {email} (服务商: {email_info.get('service')})")

    register = GrokRegister(config)
    account = register.register(email_info)

    if not account:
        config.logger.error(f"注册失败: {email}")
        register.teardown_driver()
        return None

    if getattr(args, "verify", False):
        config.logger.info("等待并验证邮箱...")
        if register.verify_email(email_info):
            account["email_verified"] = True
            config.logger.info("✅ 邮箱验证成功")
        else:
            account["email_verified"] = False
            config.logger.warning("邮箱验证失败或超时")

    register.teardown_driver()
    return account
