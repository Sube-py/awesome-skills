# awesome-skills

一个用于沉淀和复用 Agent Skills 的仓库。

当前状态：**1 个可用 skill**。

## 当前 Skills

### 1) check-workday-cn

- 作用：判断某天在中国大陆是否为工作日。
- 数据源：`holiday-cn` 年度 JSON（通过 jsDelivr 拉取）。
- 判定逻辑：
  - 若日期命中官方节假日/调休表，按 `isOffDay` 判定；
  - 若未命中，回退为周规则（周一到周五上班，周六周日休息）。
- 位置：`skills/check-workday-cn/`

## 快速开始

### 运行今日是否工作日（Asia/Shanghai）

```bash
python3 skills/check-workday-cn/scripts/check_today_workday.py
```

### 查询指定日期

```bash
python3 skills/check-workday-cn/scripts/check_today_workday.py --date 2026-02-15
```

### 输出 JSON（适合自动化流程）

```bash
python3 skills/check-workday-cn/scripts/check_today_workday.py --json
```

## 输出字段说明

- `date`: 查询日期（`YYYY-MM-DD`）
- `is_workday`: 是否工作日（`true/false`）
- `reason`: 判定原因（`holiday override` 或 `weekday fallback`）
- `source_url`: 对应年份的数据源地址

## 目录结构

```text
awesome-skills/
└── skills/
    └── check-workday-cn/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        └── scripts/
            └── check_today_workday.py
```

## 后续扩展建议

- 每个新 skill 放在 `skills/<skill-name>/`
- 至少包含：
  - `SKILL.md`（用途、触发条件、工作流、输出契约）
  - `scripts/`（可复用脚本）
  - `agents/`（模型/代理侧配置）
