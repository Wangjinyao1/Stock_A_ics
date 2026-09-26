# Stock_A_ics — 中国股市开盘日历（iCalendar / .ics）

**中国 A 股交易日日历**，自动生成可订阅的 `.ics` 文件。周末与法定节假日自动休市，数据来源于上海证券交易所公布的年度休市安排。

> 📅 订阅后可在 iPhone / Android / Outlook / Google 日历中直接看到每个交易日（开盘日），并附带节假日休市日历。

---

## 📌 订阅地址（请订阅以下地址）

将下面地址粘贴到日历应用的「订阅日历 / 通过 URL 订阅」中即可：

### 1️⃣ 开盘日历（主日历，推荐订阅）

```
https://cdn.jsdelivr.net/gh/your-name/Stock_A_ics@main/calendar/stock_a_open.ics
```

备用地址（GitHub 原始文件）：

```
https://raw.githubusercontent.com/your-name/Stock_A_ics/main/calendar/stock_a_open.ics
```

### 2️⃣ 休市日历（节假日休市提醒，可选订阅）

```
https://cdn.jsdelivr.net/gh/your-name/Stock_A_ics@main/calendar/stock_a_closed.ics
```

备用地址：

```
https://raw.githubusercontent.com/your-name/Stock_A_ics/main/calendar/stock_a_closed.ics
```

> ⚠️ 发布到 GitHub 后，请把上面地址中的 `your-name` 替换为你自己的 GitHub 用户名（与 `.env` 中 `GITHUB_REPO` 保持一致）。

### 订阅方法

| 平台 | 操作步骤 |
|------|----------|
| iPhone / iPad | 设置 → 日历 → 账户 → 添加账户 → 其他 → 订阅日历 → 粘贴地址 |
| Android | Google 日历网页版 → 其他日历 → 通过 URL 订阅 → 粘贴地址 |
| Google 日历 | 左侧「其他日历」旁的 ＋ → 通过 URL 订阅 → 粘贴地址 |
| Outlook | 日历 → 添加日历 → 从 Internet 订阅 → 粘贴地址 |

---

## 📐 交易日规则

1. **周末（周六、周日）不开市** —— 即使因节假日调休补班，周末也休市；
2. 上交所公布的**年度休市安排**中的日期休市（元旦、春节、清明、劳动、端午、中秋、国庆）；
3. 其余周一至周五为**交易日（开盘日）**。

数据来源：[上海证券交易所 · 休市安排](https://www.sse.com.cn/disclosure/dealinstruc/closed/)

> 上交所通常在每年 12 月公布下一年度休市安排，公布后本项目自动/手动重新运行即可补全年份。

---

## 🚀 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制并按需修改环境变量
copy .env.example .env

# 3. 生成日历
python main.py                # 在线抓取上交所页面 + 写入数据库 + 生成 ics
python main.py --offline      # 离线模式：仅使用内置 data/sse_closed_fallback.json
python main.py --no-db        # 跳过数据库持久化
python main.py --year-from 2026 --year-to 2028
```

生成结果：

| 文件 | 说明 |
|------|------|
| `calendar/stock_a_open.ics` | 开盘日历（交易日） |
| `calendar/stock_a_closed.ics` | 休市日历（工作日节假日） |
| `run_log.log` | 运行日志（单文件，最大 3M） |

---

## ⚙️ 自动更新（GitHub Actions）

仓库内置 `.github/workflows/update_calendar.yml`：

- 每周自动运行一次（上交所公布新年度安排后会自动补齐新年份）；
- 也支持在 Actions 页面手动触发（`workflow_dispatch`）；
- 生成的 `.ics` 有变化时自动提交回仓库，订阅地址保持有效。

---

## 🗂️ 项目结构

```
Stock_A_ics/
├── main.py                    # 主入口（抓取 → 计算 → 持久化 → 生成 ics）
├── config.py                  # 全部配置项（含数据库、订阅地址、年份范围）
├── sse_fetcher.py             # 上交所休市安排抓取与自然语言解析
├── trading_calendar.py        # 交易日计算规则（周末不开市 + 节假日休市）
├── ics_generator.py           # RFC 5545 标准 ics 生成（CRLF / 75 字节折行）
├── db.py                      # MySQL 持久化（表 stock_a_calendar）
├── logger_setup.py            # 日志（run_log.log 单文件 3M 截断）
├── data/
│   └── sse_closed_fallback.json  # 内置兜底休市数据
├── calendar/                  # 生成的 ics（发布到 GitHub 供订阅）
├── .temp/                     # 临时文件（temp_ 前缀，已 gitignore）
├── .github/workflows/         # 自动更新工作流
├── .env / .env.example        # 环境变量（.env 不入库）
├── requirements.txt
├── LICENSE                    # MIT
└── README.md
```

---

## 🗄️ 数据库

业务数据（每个日期的开盘/休市状态）持久化到 MySQL：

- 表名：`stock_a_calendar`（项目名前缀）
- 主键：自增 `id`，含 `created_at` / `updated_at` 字段，`trade_date` 唯一键
- 连接配置见 `.env`（数据库不可用时自动跳过，不影响 ics 生成）

---

## 📄 License

[MIT](LICENSE)
