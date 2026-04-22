#!/usr/bin/env python3
"""
Clash Mi 节点轮换工具
通过 API 切换 Clash Mi 的代理节点
"""

import requests
import json
import sys

# Clash Mi API 配置（请修改为你的实际配置）
API_BASE = "http://127.0.0.1:9090"
AUTH_SECRET = "your-clash-api-secret"
PROXY_GROUP = "Proxies"  # 要切换的代理组名称

HEADERS = {"Authorization": f"Bearer {AUTH_SECRET}"}


def get_proxies():
    """获取所有代理节点"""
    try:
        resp = requests.get(f"{API_BASE}/proxies/{PROXY_GROUP}", headers=HEADERS, timeout=5)
        if resp.ok:
            data = resp.json()
            return data.get("all", []), data.get("now", "")
    except Exception as e:
        print(f"获取代理失败: {e}")
    return [], ""


def switch_proxy(node_name: str) -> bool:
    """切换到指定节点"""
    try:
        resp = requests.put(
            f"{API_BASE}/proxies/{PROXY_GROUP}",
            json={"name": node_name},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=5
        )
        if resp.ok:
            print(f"✅ 已切换到: {node_name}")
            return True
        else:
            print(f"❌ 切换失败: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"切换失败: {e}")
        return False


def get_next_proxy(current: str, all_proxies: list) -> str:
    """获取下一个代理节点（轮换）"""
    if not all_proxies:
        return ""
    try:
        idx = all_proxies.index(current)
        return all_proxies[(idx + 1) % len(all_proxies)]
    except ValueError:
        return all_proxies[0]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 指定节点
        node = sys.argv[1]
        switch_proxy(node)
    else:
        # 轮换到下一个节点
        all_proxies, current = get_proxies()
        if all_proxies:
            next_node = get_next_proxy(current, all_proxies)
            print(f"当前: {current} → 切换到: {next_node}")
            switch_proxy(next_node)
        else:
            print("无法获取代理列表")