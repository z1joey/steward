/**
 * T0-07 · 枚举字面量 → 中文文案映射（与 backend/app/enums.py 对齐 [C · O-03]）。
 * 拍板后随迁移一次性替换字面量。
 */

export const ROLE_LABELS = {
  manager: "管理者",
  store_manager: "店长",
} as const;

export const INVITE_STATUS_LABELS = {
  pending: "待接受",
  accepted: "已接受",
  rejected: "已拒绝",
} as const;

export const TRANSFER_STATUS_LABELS = {
  pending: "待接受",
  accepted: "已接受",
} as const;

// —— 以下映射供 Phase B+ 使用（此处先行对齐，避免 T0-07 返工）——

export const CLAIM_STATUS_LABELS = {
  pending: "待审",
  posted: "已报销",
  rejected: "已驳回",
} as const;

export const SOURCE_TYPE_LABELS = {
  manual: "手工",
  claim: "报销",
  payroll: "工资",
  dividend: "分红",
  recurring: "周期",
} as const;

export const DIRECTION_LABELS = {
  income: "收入",
  expense: "支出",
} as const;

export const TXN_DIRECTION_LABELS = {
  in: "入",
  out: "出",
} as const;

export const RECURRING_KIND_LABELS = {
  rent: "房租",
  utilities: "水电",
  wages: "员工工资",
} as const;

export const RECURRING_PERIOD_LABELS = {
  month: "每月",
} as const;

export const JOB_TYPE_LABELS = {
  long_term: "长期",
  summer: "暑假",
  winter: "寒假",
  weekend: "周末",
  temporary: "临时",
} as const;

export const EMPLOYEE_STATUS_LABELS = {
  active: "在职",
  resigned: "离职",
} as const;
