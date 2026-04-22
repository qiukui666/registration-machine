#!/usr/bin/env python3
"""
Human Mouse - 人类鼠标行为模拟模块
通过贝塞尔曲线模拟人类鼠标移动轨迹，带随机偏移和延迟
"""

import random
import time
from typing import Optional, Tuple

from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def random_delay(min_ms: float = 10, max_ms: float = 50) -> None:
    """随机延迟（毫秒）"""
    delay = random.uniform(min_ms, max_ms) / 1000.0
    time.sleep(delay)


def human_delay(min_ms: int = 100, max_ms: int = 300) -> None:
    """人类操作前的随机延迟（毫秒）"""
    delay = random.randint(min_ms, max_ms) / 1000.0
    time.sleep(delay)


def cubic_bezier_curve_points(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    steps: int = 15,
) -> list[Tuple[float, float]]:
    """
    生成三次贝塞尔曲线上的点序列
    B(t) = (1-t)³·P0 + 3(1-t)²·t·P1 + 3(1-t)·t²·P2 + t³·P3
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        one_t = 1.0 - t
        one_t2 = one_t ** 2
        one_t3 = one_t2 * one_t
        t2 = t * t
        t3 = t2 * t
        x = one_t3 * p0[0] + 3 * one_t2 * t * p1[0] + 3 * one_t * t2 * p2[0] + t3 * p3[0]
        y = one_t3 * p0[1] + 3 * one_t2 * t * p1[1] + 3 * one_t * t2 * p2[1] + t3 * p3[1]
        points.append((x, y))
    return points


def simulate_human_mouse_move(
    driver: WebDriver,
    element: WebElement,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """
    鼠标移动到目标元素中心（简化版，直接用 ActionChains）
    """
    # 获取元素中心（视口相对坐标）
    elem_x = element.location["x"]
    elem_y = element.location["y"]
    elem_w = element.size["width"]
    elem_h = element.size["height"]

    # 目标中心 + 随机人类点击偏移 ±5px
    click_offset_x = random.uniform(-5, 5)
    click_offset_y = random.uniform(-5, 5)
    target_x = elem_x + elem_w / 2 + offset_x + click_offset_x
    target_y = elem_y + elem_h / 2 + offset_y + click_offset_y

    # 先移到元素，再微调偏移
    ActionChains(driver).move_to_element(element).perform()
    time.sleep(random.uniform(0.1, 0.2))

    # 微调偏移（带人类延迟）
    if abs(click_offset_x) > 1 or abs(click_offset_y) > 1:
        ActionChains(driver).move_by_offset(int(click_offset_x), int(click_offset_y)).perform()
        time.sleep(random.uniform(0.05, 0.15))


def simulate_human_mouse_move_simple(
    driver: WebDriver,
    target_x: int,
    target_y: int,
) -> None:
    """
    简单版：从当前位置移动到指定绝对坐标（相对位移）
    用于模拟人类在页面上的随机移动。

    Args:
        driver: Selenium WebDriver 实例
        target_x: 目标 X 坐标
        target_y: 目标 Y 坐标
    """
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver).move_to_element_with_offset(body, 0, 0).perform()
    except NoSuchElementException:
        body = None

    # 获取视口尺寸
    viewport = driver.get_window_size()
    vp_width = viewport["width"]
    vp_height = viewport["height"]

    # 视口中心作为起点
    start_x = vp_width / 2
    start_y = vp_height / 2

    # 控制点（随机偏移）
    ctrl1_x = start_x + (target_x - start_x) * 0.3 + random.uniform(-50, 50)
    ctrl1_y = start_y + (target_y - start_y) * 0.3 + random.uniform(-50, 50)
    ctrl2_x = start_x + (target_x - start_x) * 0.7 + random.uniform(-50, 50)
    ctrl2_y = start_y + (target_y - start_y) * 0.7 + random.uniform(-50, 50)

    points = cubic_bezier_curve_points(
        p0=(start_x, start_y),
        p1=(ctrl1_x, ctrl1_y),
        p2=(ctrl2_x, ctrl2_y),
        p3=(target_x, target_y),
        steps=random.randint(8, 20),
    )

    prev_x, prev_y = points[0]
    for px, py in points[1:]:
        ActionChains(driver).move_by_offset(int(px - prev_x), int(py - prev_y)).perform()
        time.sleep(random.uniform(0.01, 0.03))
        prev_x, prev_y = px, py


def human_click(
    driver: WebDriver,
    element: WebElement,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> None:
    """
    人类点击：鼠标移动 + 随机延迟 + 随机偏移点击

    Args:
        driver: Selenium WebDriver 实例
        element: 目标元素
        offset_x: 额外 X 偏移
        offset_y: 额外 Y 偏移
    """
    simulate_human_mouse_move(driver, element, int(offset_x), int(offset_y))
    time.sleep(random.uniform(0.1, 0.3))

    # 点击偏移（抵消 simulate_human_mouse_move 已有的 ±5px，这里只加 ±3px）
    cx = random.uniform(-3, 3)
    cy = random.uniform(-3, 3)
    ActionChains(driver).move_to_element_with_offset(element, int(cx), int(cy)).click().perform()


def human_click_element(
    driver: WebDriver,
    wait: WebDriverWait,
    selectors: list,
    description: str = "元素",
    timeout: int = 15,
) -> Optional[WebElement]:
    """
    等待元素可点击后人类方式点击

    Args:
        driver: Selenium WebDriver 实例
        wait: WebDriverWait 实例
        selectors: 选择器列表 [(By.XXX, "selector"), ...]
        description: 元素描述（用于日志）
        timeout: 超时时间（秒）

    Returns:
        被点击的元素，失败返回 None
    """
    for selector in selectors:
        try:
            elem = wait.until(EC.element_to_be_clickable(selector))
            human_click(driver, elem)
            return elem
        except Exception:
            continue
    return None


def wait_and_human_click(
    driver: WebDriver,
    selector: Tuple[By, str],
    description: str = "元素",
    timeout: int = 15,
) -> Optional[WebElement]:
    """
    等待元素出现并人类方式点击（单选择器版本）

    Args:
        driver: Selenium WebDriver 实例
        selector: (By.XXX, "selector") 元组
        description: 元素描述
        timeout: 超时时间

    Returns:
        被点击的元素
    """
    wait = WebDriverWait(driver, timeout)
    return human_click_element(driver, wait, [selector], description, timeout)


def simulate_page_scroll(driver: WebDriver, direction: int = 1) -> None:
    """模拟页面滚动"""
    scroll_amount = random.randint(100, 200) * direction
    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    time.sleep(random.uniform(0.2, 0.5))


def simulate_pre_registration_behavior(driver: WebDriver) -> None:
    """
    注册前模拟人类预热行为：滚动页面 + 随机鼠标移动
    """
    time.sleep(random.uniform(0.5, 1.5))
    for _ in range(3):
        simulate_page_scroll(driver, random.choice([1, -1]))
        time.sleep(random.uniform(0.3, 0.8))

    viewport = driver.get_window_size()
    for _ in range(2):
        x = random.randint(0, viewport["width"])
        y = random.randint(0, viewport["height"])
        simulate_human_mouse_move_simple(driver, x, y)
        time.sleep(random.uniform(0.2, 0.5))
