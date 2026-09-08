/**
 * T0-07 · 锁定文案常量（coding-guidelines §1.5 / B-specs §0.5）。
 * e2e 断言引用同一常量；英文仅用于 API path / 代码标识。
 */
export const COPY = {
  appName: "司舵",

  // 角色
  roleManager: "管理者",
  roleStoreManager: "店长",

  // 侧栏 IA（ui-spec §1）
  navLedger: "账本",
  navEntries: "流水",
  navRecurring: "周期",
  navStats: "统计",
  navOverview: "概览",
  navEmployees: "员工",
  navSettings: "设置",

  // 账本操作
  recordEntry: "记一笔",
  needsReimbursement: "需要报销",
  claimApprove: "报销",
  claimReject: "驳回",
  claimedDone: "已报销 · 公账已扣",
  payrollSettle: "结算工资",
  dividendConfirm: "确认发放",
  reverse: "冲正",
  reversed: "已冲正",
  pendingReview: "待审",
  fromSettlement: "来自结算",
  reverseReason: "原因（可选）",
  confirmReverse: "确认冲正",
  filterAll: "全部",
  date: "日期",
  amount: "金额",
  memo: "摘要",

  // 周期（TC-05）
  newRecurring: "新建周期项",
  editRecurring: "编辑周期项",
  recurringName: "名称",
  recurringKind: "类型",
  recurringFixed: "固定金额",
  recurringFloating: "浮动",
  recordThisMonth: "记本月",
  thisMonthNotRecorded: "本月未录",
  wagesNoHandFill: "员工工资来自结算，禁手填",
  edit: "编辑",
  operations: "操作",
  active: "启用",
  inactive: "停用",

  // 统计 / 分红（TC-06）
  income: "收入",
  expense: "支出",
  profitRate: "利润率",
  publicAccount: "公账",
  recentTxns: "最近变动",
  dividendAmount: "分红金额",
  overBalance: "超过公账余额",
  insufficientBalance: "余额不足，未入账",

  // 认证 / 引导
  login: "登录",
  register: "注册",
  phone: "手机号",
  password: "密码",
  loginFailed: "手机号或密码错误",
  logout: "退出登录",
  createStore: "创建门店",
  storeName: "门店名称",
  pendingInvites: "待处理邀请",
  accept: "接受",
  reject: "拒绝",
  invitesSection: "邀请",
  transfersSection: "转让",

  // 成员设置
  inviteManager: "邀请店长",
  transferManager: "转让管理者",

  // 全局提示（AC-CON-02）
  conflictToast: "已被别人更新，已刷新",
} as const;
