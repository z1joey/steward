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

export interface DividendConfirmResponse {
  run: { id: number; amount: string; confirmed_at: string };
  entry: LedgerRow;
  public: { balance: string; version: number };
}
