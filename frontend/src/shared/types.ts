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
