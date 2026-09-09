/** API 载荷类型（与 backend schemas 对齐；JSON 字段英文锁定）。 */

export interface StoreItem {
  id: number;
  name: string;
  role: "manager" | "store_manager";
  version: number;
}

export interface PendingInviteItem {
  id: number;
  store: { id: number; name: string };
  inviter_phone: string;
  created_at: string;
}

export interface PendingTransferItem {
  id: number;
  store: { id: number; name: string };
  from_phone: string;
  created_at: string;
}

export interface PendingList {
  invites: PendingInviteItem[];
  transfers: PendingTransferItem[];
}

export interface MembersSettings {
  members: { user: { id: number; phone: string }; role: string; since: string }[];
  pending_invites: { id: number; user: { id: number; phone: string }; created_at: string }[];
  pending_transfers: { id: number; user: { id: number; phone: string }; created_at: string }[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: { id: number; phone: string };
}

// —— Phase B · Ledger / Claims（与 backend schemas 对齐）——

export interface RequestedBy {
  id: number;
  phone: string;
}

export interface ClaimView {
  id: number;
  date: string;
  amount: string;
  memo: string;
  status: "pending" | "posted" | "rejected";
  requested_by: RequestedBy;
  decided_at: string | null;
  ledger_entry_id: number | null;
  version: number;
}

export interface LedgerRow {
  row_type: "entry" | "claim_pending";
  id: number;
  date: string;
  amount: string;
  direction: "income" | "expense" | null;
  memo: string;
  source_type: "manual" | "claim" | "payroll" | "dividend" | "recurring" | null;
  source_id: number | null;
  is_reversal: boolean;
  reversed_by_id: number | null;
  claim_status: string | null;
  version: number;
  created_at: string | null;
  requested_by: RequestedBy | null;
}

export interface LedgerList {
  items: LedgerRow[];
  total: number;
}

export interface EntryCreateResponse {
  kind: "entry" | "claim";
  entry: LedgerRow | null;
  claim: ClaimView | null;
}

export interface ReversalResponse {
  entry: LedgerRow;
  original: LedgerRow;
  public_txn: { id: number; balance_after: string } | null;
}

// —— Phase C · Recurring / Stats / Dividend ——

export type RecurringKind = "rent" | "utilities" | "wages";

export interface RecurringOccurrence {
  id: number;
  period_month: string;
  amount: string;
  recurring_expense_id: number;
}

export interface RecurringItem {
  id: number;
  name: string;
  kind: RecurringKind;
  period: "month";
  is_fixed: boolean;
  fixed_amount: string | null;
  active: boolean;
  version: number;
  created_at: string;
  current_month_occurrence: RecurringOccurrence | null;
}

export interface RecentTxn {
  id: number;
  amount: string;
  direction: "in" | "out";
  source_type: string;
  balance_after: string;
  created_at: string;
  memo: string;
}

export interface LedgerStats {
  month: string;
  income: string;
  expense: string;
  profit_rate: number | null;
  public: {
    balance: string;
    version: number;
    recent_txns: RecentTxn[];
  };
}

export interface BalanceAdjustResponse {
  balance: string;
  public_txn: { id: number; balance_after: string | null };
}

export interface AdjustmentItem {
  id: number;
  date: string;
  direction: "income" | "expense";
  amount: string;
  reason: string;
  balance_after: string;
  created_at: string;
}

export interface AdjustmentList {
  items: AdjustmentItem[];
  total: number;
}

export interface DividendConfirmResponse {
  run: { id: number; amount: string; confirmed_at: string };
  entry: LedgerRow;
  public: { balance: string; version: number };
}

// —— Phase D · Employees / Shifts / Payroll ——

export type JobType = "long_term" | "summer" | "winter" | "weekend" | "temporary";
export type PayType = "hourly" | "daily";   // [O-07] 计薪方式
export type EmployeeStatusType = "active" | "resigned";

export interface EmployeeItem {
  id: number;
  name: string;
  status: EmployeeStatusType;
  display_status: "active" | "resigned" | "on_leave";
  contact: string;
  job_type: JobType;
  notes: string;
  pay_type: PayType | null;      // [O-07] 单价存员工档案
  unit_price: string | null;
  resigned_on: string | null;
  version: number;
}

export interface LeaveItem {
  id: number;
  employee_id: number;
  start_date: string;
  end_date: string;
  note: string;
  version: number;
}

export interface EmployeeDetail extends EmployeeItem {
  leaves: LeaveItem[];
}

export interface ShiftSegmentItem {
  id: number;
  employee_id: number;
  start_at: string;
  end_at: string;
  minutes: number;
  version: number;
}

export interface ShiftEmployee {
  id: number;
  name: string;
  status: string;
  display_status: string;
  job_type: JobType;
  version: number;
}

export interface ShiftList {
  items: ShiftSegmentItem[];
  employees: ShiftEmployee[];
}

export interface PayrollPreviewRow {
  employee_id: number;
  name: string;
  hours: string;
  worked_days: number;   // [O-07] 自然日出勤天数
  amount: string | null;
  segments_count: number;
  pay_type: PayType | null;
}

export interface PayrollRunView {
  id: number;
  period_month: string;
  total_amount: string;
  lines: {
    employee_id: number;
    hours: string;
    amount: string;
    ledger_entry_id: number | null;
  }[];
}

export interface PayrollData {
  month: string;
  settled: PayrollRunView | null;
  preview: PayrollPreviewRow[];
  total_hours: string;
  total_amount: string | null;
}
