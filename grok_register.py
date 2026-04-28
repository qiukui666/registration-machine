#!/usr/bin/env python3
"""
Grok Register - xAI Grok 账号注册模块
使用 Selenium 自动化注册流程
"""

import random
import re
import string
import time
from typing import Dict, Optional

import requests
from fake_useragent import UserAgent
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager  # noqa: F401
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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


class GrokRegister:
    """Grok/xAI 账号注册器"""

    SIGNUP_URL = "https://grok.com/sign-up"
    GROK_URL = "https://grok.com/"

    # 可用于验证邮件的关键字
    VERIFY_KEYWORDS = ["x.ai", "grok", "verify", "confirm"]

    def __init__(self, config: Config):
        self.config = config
        self.logger = config.logger
        self.driver: Optional[webdriver.Chrome] = None
        self.max_retries = config.get("max_retries", 3)
        self._ua = UserAgent()

    # ─────────────────────────────────────────────────────────────────────────
    # Browser setup
    # ─────────────────────────────────────────────────────────────────────────

    def setup_driver(self, proxy: Optional[str] = None) -> bool:
        """设置浏览器驱动（WSL 标准 Selenium + webdriver-manager）"""
        for attempt in range(1, self.max_retries + 1):
            try:
                options = Options()

                if self.config.get("user_agent_rotation", True):
                    options.add_argument(f"user-agent={self._ua.random}")

                for arg in [
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]:
                    options.add_argument(arg)

                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)

                if proxy:
                    options.add_argument(f"--proxy-server={proxy}")

                # WSL 无显示器，强制 headless
                if True:
                    options.add_argument("--headless=new")

                # WSL Chrome 路径
                options.binary_location = "/usr/bin/google-chrome"

                # webdriver-manager 自动管理 ChromeDriver
                svc = Service("/home/qiukui/.wdm/drivers/chromedriver/linux64/147.0.7727.117/chromedriver-linux64/chromedriver")
                self.driver = webdriver.Chrome(service=svc, options=options)

                # 强化反检测
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); "
                    "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]}); "
                    "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']}); "
                    "window.chrome = {runtime: {}};"
                )

                self.logger.info("浏览器驱动设置完成 (Selenium + WSL Chrome)")
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
        """填写注册表单（支持 grok.com/sign-up 新 UI）"""
        try:
            wait = WebDriverWait(self.driver, 15)
            time.sleep(random.uniform(2, 3))

            # ── 处理 Cookie 弹窗 ──
            try:
                accept_cookie = self._find_clickable_button(wait, [
                    (By.XPATH, "//button[contains(text(),'接受所有 Cookie')]"),
                    (By.XPATH, "//button[contains(text(),'Accept All Cookies')]"),
                    (By.XPATH, "//button[contains(text(),'Accept all Cookie')]"),
                ])
                if accept_cookie:
                    accept_cookie.click()
                    self.logger.info("Cookie 弹窗已接受")
                    time.sleep(1)
            except Exception:
                pass  # 无 Cookie 弹窗也继续

            # ── 点击"使用邮箱注册"（新 UI） ──
            try:
                email_reg_btn = self._find_clickable_button(wait, [
                    (By.XPATH, "//button[contains(text(),'使用邮箱注册')]"),
                    (By.XPATH, "//button[contains(text(),'Sign up with Email')]"),
                    (By.XPATH, "//button[contains(text(),'Register with Email')]"),
                ])
                if email_reg_btn:
                    email_reg_btn.click()
                    self.logger.info("已点击邮箱注册")
                    time.sleep(2)
            except Exception:
                pass  # 没有邮箱注册按钮也继续（旧 UI 直接就是表单）

            # ── 定位并填写邮箱 ──
            email_input = self._find_element(wait, [
                (By.NAME, "email"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
                (By.CSS_SELECTOR, "input[autocomplete='email']"),
            ])

            if not email_input:
                self.logger.error("无法定位邮箱输入框")
                self._log_page_errors()
                return None

            self._human_type(email_input, email)

            # ── 点击注册/继续按钮 ──
            continue_btn = self._find_clickable_button(wait, [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Continue')]"),
                (By.XPATH, "//button[contains(text(), '注册')]"),
                (By.XPATH, "//button[contains(text(), 'Sign up')]"),
            ])

            if continue_btn:
                continue_btn.click()
                time.sleep(random.uniform(2, 3))

            # ── 填写密码 ──
            password = self.generate_password()
            password_input = self._find_element(wait, [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.CSS_SELECTOR, "input[placeholder*='password' i]"),
            ])

            if password_input:
                self._human_type(password_input, password)
                time.sleep(0.5)

                # 提交
                submit_btn = self._find_clickable_button(wait, [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Create')]"),
                    (By.XPATH, "//button[contains(text(), '注册')]"),
                    (By.XPATH, "//button[contains(text(), 'Sign up')]"),
                    (By.XPATH, "//button[contains(text(), 'Continue')]"),
                ])

                if submit_btn and submit_btn.is_enabled():
                    submit_btn.click()
                    time.sleep(random.uniform(3, 5))

            return self._check_registration_success(email, password)

        except Exception as e:
            self.logger.error(f"填写注册表单失败: {e}")
            return None

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

        if service == "temp-mail.org":
            return self._verify_via_api(email_info, timeout, check_interval)
        elif service == "guerrillamail.com":
            return self._verify_via_api(email_info, timeout, check_interval)

        self.logger.warning(f"不支持的邮箱服务: {service}")
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

def register_grok_account(
    args,
    config: Config,
    email_gen: EmailGenerator,
) -> Optional[Dict]:
    """生成邮箱并注册 Grok 账号"""
    email_info = email_gen.generate_temp_email("guerrillamail.com")
    email = email_info.get("email", "")

    if not email:
        config.logger.error("生成临时邮箱失败")
        return None

    if check_duplicate_account(email):
        config.logger.warning(f"账号已存在，跳过: {email}")
        return None

    config.logger.info(f"生成的临时邮箱: {email} (服务商: {email_info.get('service')})")

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
