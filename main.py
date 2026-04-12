#!/usr/bin/env python3
"""
Registration Machine - 统一注册程序
支持 GPT (OpenAI) 和 Grok (xAI) 账号的自动注册

用法:
    python main.py --platform gpt                 # 注册 GPT 账号
    python main.py --platform grok                # 注册 Grok 账号
    python main.py --platform both                # 两个都注册
    python main.py --platform gpt --max-accounts 5   # 批量注册
"""

import argparse
import random
import sys
import time
from typing import List, Optional

from common import (
    Config,
    EmailGenerator,
    backup_accounts,
    clear_old_accounts,
    get_statistics,
    load_accounts,
    print_statistics,
    save_account_info,
    save_account_info_csv,
    save_account_info_txt,
    setup_logger,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Registration Machine - GPT/Grok 账号批量注册工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --platform gpt
  python main.py --platform grok
  python main.py --platform both --max-accounts 3
  python main.py --platform gpt --verify
  python main.py --stats
        """,
    )

    parser.add_argument(
        "--platform",
        type=str,
        choices=["gpt", "grok", "both"],
        default="both",
        help="注册平台: gpt / grok / both (默认: both)",
    )
    parser.add_argument(
        "--max-accounts",
        type=int,
        default=1,
        help="每个平台注册的账号数量 (默认: 1)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="注册完成后等待并验证邮箱",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（不显示浏览器窗口）",
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        help="HTTP 代理地址, 如: http://127.0.0.1:7890",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径 (默认: config.json)",
    )

    # 输出格式选项（默认全部开启）
    group_out = parser.add_argument_group("输出格式")
    group_out.add_argument("--json", action="store_true", help="保存为 JSON 格式")
    group_out.add_argument("--csv", action="store_true", help="保存为 CSV 格式")
    group_out.add_argument("--txt", action="store_true", help="保存为 TXT 格式")

    # 工具命令
    group_util = parser.add_argument_group("工具命令")
    group_util.add_argument(
        "--stats", action="store_true", help="显示账号统计信息"
    )
    group_util.add_argument(
        "--backup", action="store_true", help="备份现有账号数据"
    )
    group_util.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="清理 N 天前的旧账号记录",
    )
    group_util.add_argument(
        "--dedup",
        action="store_true",
        help="去除重复账号记录",
    )

    return parser.parse_args()


def run_platform(
    platform: str,
    args,
    config: Config,
    email_gen: EmailGenerator,
) -> tuple[int, int]:
    """运行指定平台的注册，返回 (成功数, 失败数)"""
    # 延迟导入，避免 --help 时需要安装 selenium
    if platform == "gpt":
        from gpt_register import register_gpt_account
        register_fn = register_gpt_account
    else:
        from grok_register import register_grok_account
        register_fn = register_grok_account

    success, fail = 0, 0

    for i in range(1, args.max_accounts + 1):
        config.logger.info("")
        config.logger.info(f"[{platform.upper()}] [{i}/{args.max_accounts}] 开始注册...")

        account: Optional[dict] = register_fn(args, config, email_gen)

        if account:
            success += 1
            _save_accounts(account, args, platform)
            config.logger.info(f"✅ 账号已保存: {account['email']}")
        else:
            fail += 1
            config.logger.error(f"❌ 注册失败")

        # 批次间随机等待
        if i < args.max_accounts:
            wait = random.uniform(5, 15)
            config.logger.info(f"等待 {wait:.1f}s 后继续...")
            time.sleep(wait)

    return success, fail


def _save_accounts(account: dict, args, platform: str) -> None:
    """根据参数保存账号到指定格式"""
    if args.json or (not args.json and not args.csv and not args.txt):
        save_account_info(account, platform=platform)
    if args.csv:
        save_account_info_csv(account, platform=platform)
    if args.txt:
        save_account_info_txt(account, platform=platform)


def dedup_accounts(filename: str = "accounts.json") -> int:
    """去除重复账号，返回移除的数量"""
    accounts = load_accounts(filename)
    seen = set()
    unique = []
    removed = 0

    for acc in accounts:
        email = acc.get("email", "")
        if email and email not in seen:
            seen.add(email)
            unique.append(acc)
        else:
            removed += 1

    if removed > 0:
        import json
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)
        print(f"✅ 去除重复完成，移除了 {removed} 条记录")

    return removed


def main():
    args = parse_args()

    # 工具命令直接处理
    if args.stats:
        accounts = load_accounts()
        if accounts:
            stats = get_statistics()
            print_statistics(stats)
        else:
            print("暂无账号记录")
        return

    if args.backup:
        backup_accounts()
        return

    if args.cleanup is not None:
        removed = clear_old_accounts(days_to_keep=args.cleanup)
        return

    if args.dedup:
        dedup_accounts()
        return

    # ── 主流程 ──────────────────────────────────────────────────────────────
    config = Config(args.config)
    config.logger = setup_logger("Registration-Machine", config.get("log_level", "INFO"))

    # CLI 参数覆盖配置
    if args.headless:
        config.config_data["headless"] = True
    if args.proxy:
        config.config_data["proxy"] = args.proxy
    if args.verify:
        config.config_data["verify"] = True

    email_gen = EmailGenerator()

    # 默认保存所有格式
    if not (args.json or args.csv or args.txt):
        args.json = args.csv = args.txt = True

    platforms = ["gpt", "grok"] if args.platform == "both" else [args.platform]

    config.logger.info("=" * 60)
    config.logger.info(" Registration Machine 启动")
    config.logger.info(f" 平台: {', '.join(p.upper() for p in platforms)}")
    config.logger.info(f" 数量: {args.max_accounts} × {len(platforms)} = {args.max_accounts * len(platforms)} 个")
    config.logger.info(f" 邮箱验证: {'开启' if args.verify else '关闭'}")
    config.logger.info(f" 无头模式: {'开启' if args.headless else '关闭'}")
    config.logger.info(f" 代理: {args.proxy or '未使用'}")
    config.logger.info("=" * 60)

    total_success, total_fail = 0, 0

    for platform in platforms:
        config.logger.info("")
        config.logger.info(f"{'#' * 50}")
        config.logger.info(f"# {platform.upper()} 注册批次")
        config.logger.info(f"{'#' * 50}")

        s, f = run_platform(platform, args, config, email_gen)
        total_success += s
        total_fail += f

        # 平台间额外等待
        if platform != platforms[-1]:
            wait = random.uniform(10, 20)
            config.logger.info(f"切换平台，等待 {wait:.1f}s...")
            time.sleep(wait)

    # 最终统计
    config.logger.info("")
    config.logger.info("=" * 60)
    config.logger.info(" 注册完成!")
    config.logger.info(f" 成功: {total_success}")
    config.logger.info(f" 失败: {total_fail}")
    config.logger.info("=" * 60)

    if total_success > 0:
        print_statistics(get_statistics())


if __name__ == "__main__":
    sys.exit(main())
