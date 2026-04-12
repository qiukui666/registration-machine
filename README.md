# Registration Machine

GPT (OpenAI) 和 Grok (xAI) 账号批量自动注册工具。基于 Selenium 浏览器自动化，支持临时邮箱自动验证。

## 功能特性

- **多平台支持**：统一入口，支持 `--platform gpt` / `grok` / `both` 切换
- **批量注册**：可指定每个平台的注册数量
- **临时邮箱**：集成 temp-mail.org、guerrillamail.com 等临时邮箱服务
- **邮箱验证**：自动轮询等待并点击验证链接
- **反检测**：使用 undetected-chromedriver + User-Agent 轮换 + 模拟人类输入
- **多格式存储**：账号信息自动保存为 JSON / CSV / TXT
- **账号管理**：查重、备份、清理、统计
- **代理支持**：支持 HTTP 代理
- **无头模式**：可选不显示浏览器窗口
- **日志记录**：完整的运行日志

## 项目结构

```
registration-machine/
├── main.py                 # 统一入口
├── gpt_register.py         # GPT/OpenAI 注册模块
├── grok_register.py       # Grok/xAI 注册模块
├── requirements.txt        # 依赖列表
├── config.json             # 配置文件（可选）
├── common/
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── utils.py            # 通用工具（账号存取、统计、备份等）
│   └── email_generator.py  # 临时邮箱生成
├── accounts.json           # 账号存储（JSON）
├── accounts.csv            # 账号存储（CSV）
├── accounts.txt            # 账号存储（TXT）
└── *.log                   # 运行日志
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行注册

```bash
# 注册 1 个 GPT 账号
python main.py --platform gpt

# 注册 1 个 Grok 账号
python main.py --platform grok

# 两个平台各注册 1 个
python main.py --platform both

# 每个平台注册 5 个
python main.py --platform both --max-accounts 5

# 开启邮箱验证
python main.py --platform gpt --verify

# 无头模式（不显示浏览器）
python main.py --platform gpt --headless

# 使用代理
python main.py --platform gpt --proxy http://127.0.0.1:7890
```

## 命令行参数

### 注册相关

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--platform` | 注册平台：`gpt` / `grok` / `both` | `both` |
| `--max-accounts` | 每个平台注册的账号数量 | `1` |
| `--verify` | 注册完成后等待并验证邮箱 | 关闭 |
| `--headless` | 无头模式（不显示浏览器） | 关闭 |
| `--proxy` | HTTP 代理地址，如 `http://127.0.0.1:7890` | 不使用 |
| `--config` | 配置文件路径 | `config.json` |

### 输出格式（可叠加）

| 参数 | 说明 |
|------|------|
| `--json` | 保存为 JSON 格式（默认已开启） |
| `--csv` | 保存为 CSV 格式（默认已开启） |
| `--txt` | 保存为 TXT 格式（默认已开启） |

### 工具命令

| 参数 | 说明 |
|------|------|
| `--stats` | 显示账号统计信息 |
| `--backup` | 备份现有账号数据 |
| `--cleanup DAYS` | 清理 N 天前的旧账号记录 |
| `--dedup` | 去除重复账号记录 |

## 配置说明

程序默认使用 `config.json`（不存在时使用内置默认值）。示例：

```json
{
  "headless": false,
  "proxy": null,
  "max_retries": 3,
  "user_agent_rotation": true,
  "temp_mail_timeout": 180,
  "temp_mail_check_interval": 5,
  "log_level": "INFO"
}
```

CLI 参数会覆盖配置文件中的同名项。

## 账号存储

注册成功后，账号信息默认同时保存为三种格式：

- **accounts.json**：完整 JSON，含 session_token 等全部字段
- **accounts.csv**：表格格式，便于导入 Excel
- **accounts.txt**：可读文本，每条记录以 `====` 分隔

字段说明：

| 字段 | 说明 |
|------|------|
| `email` | 账号邮箱 |
| `password` | 账号密码 |
| `status` | 账号状态（`active` 等） |
| `platform` | 平台（`gpt` 或 `grok`） |
| `created_at` | 创建时间 |
| `saved_at` | 保存时间 |
| `session_token` | 会话令牌 |
| `email_verified` | 邮箱是否已验证 |

## 常见问题

### 1. 浏览器驱动启动失败

确保已安装 Chrome 并配置好 PATH。若使用代理或企业网络，尝试加上 `--proxy` 参数或检查网络连通性。

### 2. 临时邮箱收不到验证邮件

- 检查网络延迟，可适当增大 `config.json` 中的 `temp_mail_timeout`（默认 180 秒）
- 确认临时邮箱服务商（temp-mail.org / guerrillamail.com）在当前网络环境下可用
- 使用 `--verify` 参数会自动轮询等待，若最终仍未收到会标记 `email_verified: false`

### 3. 被网站检测为机器人

程序默认开启以下反检测措施：
- `undetected-chromedriver`（自动化特征屏蔽）
- User-Agent 随机轮换
- 模拟人类逐字符输入
- 随机等待时间

如仍被检测，尝试切换 IP 或使用代理。

### 4. 注册失败率高

- 降低 `--max-accounts` 数量，减少单 IP 请求频率
- 使用代理轮换
- 检查网络稳定性

### 5. 如何查看统计信息？

```bash
python main.py --stats
```

输出示例：
```
📊 账号统计信息
========================================
📝 总账号数:   10
🟢 活跃账号:   8
🔴 非活跃账号: 2
📈 成功率:    80.0%
========================================
🔗 平台分布:
   gpt: 5 个账号
   grok: 5 个账号

📅 创建时间分布:
   2026-04-13: 10 个账号
```

### 6. 如何备份账号？

```bash
python main.py --backup
```

备份文件命名格式：`accounts_backup_YYYYMMDD_HHMMSS.json`

### 7. 如何清理旧记录？

```bash
# 清理 30 天前的记录
python main.py --cleanup 30
```

### 8. 如何去重？

```bash
python main.py --dedup
```

## 依赖说明

| 依赖 | 用途 |
|------|------|
| `selenium >= 4.10.0` | 浏览器自动化基础 |
| `undetected-chromedriver >= 3.5.0` | 反检测 Chrome 驱动 |
| `fake-useragent >= 1.1.3` | User-Agent 随机生成 |
| `requests >= 2.31.0` | HTTP 请求 |
| `tqdm >= 4.65.0` | 进度条 |
| `colorama >= 0.4.6` | 彩色输出 |
| `python-dotenv >= 1.0.0` | 环境变量支持 |

## 免责声明

本工具仅供学习与研究使用。请遵守各平台的服务条款，合理使用账号注册功能，切勿用于任何商业或滥用目的。
