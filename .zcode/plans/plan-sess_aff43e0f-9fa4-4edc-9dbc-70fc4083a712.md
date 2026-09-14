# O-07 费率规则落地（按小时/按日 + 单价入员工档案）

## 已拍板的规则
- **计薪方式**：员工档案自选「按小时 / 按日」+ 单价（元/小时 或 元/天）；算法模块按工种表驱动，留扩展位
- **按日口径**：自然日出勤——当天有任意班段记 1 天，同日多段不重复
- **加班费、奖金**：本期不实现，写入 README todo list；`rate_snapshot` 明细结构预留扩展位

## 分支
从最新 develop 新建 `feature/O07-RATE_AC-PAY-01-04`（develop 与 main 当前树一致，切分支不影响运行中的服务）。

## 后端

**1. Alembic 0006（新增，down_revision=0005）**：`employees` 加列
- `pay_type VARCHAR(10) NULL CHECK IN ('hourly','daily')`（命名 `ck_employees_pay_type`）
- `unit_price NUMERIC(14,2) NULL CHECK (unit_price IS NULL OR unit_price > 0)`（`ck_employees_unit_price`）
- 配对约束 `((pay_type IS NULL) = (unit_price IS NULL))`（`ck_employees_pay_pair`，仿 `ck_employees_resigned_pair` 模式）
- 同步 `employees/models.py`

**2. Employees API（schemas/models/service）**
- `EmployeeCreateIn` / `EmployeeUpdateIn`（保持 `extra="forbid"`）加可选 `pay_type` + `unit_price(gt=0)`；加 model_validator：两者同空或同设（防配对约束 500）
- `EmployeeOut` / `employee_out` / `update_employee`（沿用现有 versioned CAS 字段追加模式）同步加字段
- 不支持清除（设置后只能在 hourly/daily 间切换改价）；离职员工字段随表单禁用（现有逻辑）

**3. rate_rule.py 重写（唯一接缝，R9 单函数+表驱动）**
- 常量表：`OVERTIME`（阈值/倍率占位，本期不用）、未来按工种覆盖的 `JOB_ALGORITHMS` 扩展位
- `compute(employee, hours, month, worked_days=0) -> RateOutcome | None`
  - `RateOutcome(amount: Decimal, snapshot: dict)`；snapshot 含 `{pay_type, unit_price, base_hours/worked_days, amount, overtime: null}`（预留加班/奖金扩展）
  - hourly：`amount = quantize(hours × unit_price)`；daily：`amount = quantize(worked_days × unit_price)`
  - `pay_type`/`unit_price` 缺失 → `None`（保持「未设置计薪」优雅降级，settle → 422 rate_rule_missing）
  - keyword 默认参数使现有测试桩签名 `(e, hours, m)` 仍兼容

**4. payroll/service.py**
- `_aggregate_preview`：改为单条 SQL 按 `(employee_id, func.date(start_at))` 分组（服务端单一时区，与现 `_month_bounds` 口径一致），派生 `hours` 与 `worked_days`（distinct 天数）；`PayrollPreviewRow` 加 `worked_days`、`pay_type`
- `settle_payroll`：`rate_snapshot` 用真实 outcome.snapshot 替换占位 `{"rate_rule": "settled"}`；`rate_rule_missing` 逻辑不变（任一行 amount=None 即 422）

## 前端

- `types.ts`：`EmployeeItem` + `pay_type`/`unit_price`；`PayrollPreviewRow` + `worked_days`/`pay_type`
- `employees/stores/employees.ts` `saveProfile` 字段扩展
- `EmployeeDetailView.vue`：新增「计薪」区——计薪方式下拉（未设置占位/按小时/按日）+ 单价输入（label 随方式切 元/小时、元/天），沿用 500ms 防抖自动保存 + version，离职禁用
- `RosterTab.vue` 新增抽屉：可选 计薪方式 + 单价
- `PayrollTab.vue`：表格加「出勤」列；应发正常显示金额；`COPY.ratePending`「待费率拍板」→「未设置计薪」（null 语义已变为该员工未配置）；结算错误文案 →「无可结算行或存在未设置计薪的员工」（入 `copy.ts`）
- `npm run build` 验证类型

## 测试

- **后端** `test_payroll.py`：T-PAY-02/03 改用真实规则（员工 seed `pay_type=hourly, unit_price=50`，删 DI 桩）；`test_t_pay_rate_rule_missing` 改为「员工未配置计薪 → 422 rate_rule_missing」；T-PAY-04/05b 不动
- **新增** `test_rate_rule.py`：hourly 多段求和；daily 自然日出勤（同日多段计 1 天、跨天各计 1）；未配置 → amount null；PUT 配单价（version CAS）、非法 pay_type / price≤0 / 只配一半 → 422；settle 后 `rate_snapshot` 明细断言；preview `worked_days` 正确
- **e2e** `concurrency.spec.ts` 薪资用例：seed 员工带计薪字段，断言应发「200.00」且随班次变化（替换原「待费率拍板」断言，该用例注释本就预留了此改动）

## 文档
- `README.md`：新增 TODO 小节——加班费（单日超8h×1.5 方向）、奖金/额外人力支出
- `docs/plan/B-specs.md` §8 与 `docs/plan/C-tasks.md` §8 的 O-07 行标注「已拍板 2026-09-09」+ 规则摘要

## 提交与验收（沿用 goal 约定）
1. `feat(O07-1): employees 计薪字段 + Alembic 0006`（AC-EMP-02）→ 跑 pytest
2. `feat(O07-2): rate_rule 按小时/按日 + preview/settle 快照`（AC-PAY-01/02/04）→ 全量 pytest
3. `feat(O07-3): 员工计薪区 + 薪资 Tab 出勤/金额`（AC-EMP-02 · US-E7）→ `npm run build` + 薪资 e2e
4. `test(O07-T): 费率规则后端测试 + e2e 更新` → 全量 pytest + e2e
5. `docs(O07): O-07 拍板标注 + README todo`
6. 全绿后合并回 develop 并推送；运行中的 app 热更新后可在「员工详情 → 计薪」配置单价，薪资 Tab 即出金额、结算可用