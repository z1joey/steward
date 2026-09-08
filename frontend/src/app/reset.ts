/**
 * 店级资源 Pinia store 统一注册表（B-specs §0.5）：
 * 切店 / 409 时 resetStoreScopedStores() → 所有 feature store $reset() + 关闭全部弹窗。
 */
type ResetFn = () => void;

const resets: ResetFn[] = [];
const modalClosers: ResetFn[] = [];

export function registerStoreReset(fn: ResetFn): () => void {
  resets.push(fn);
  return () => {
    const i = resets.indexOf(fn);
    if (i >= 0) resets.splice(i, 1);
  };
}

export function registerModalCloser(fn: ResetFn): () => void {
  modalClosers.push(fn);
  return () => {
    const i = modalClosers.indexOf(fn);
    if (i >= 0) modalClosers.splice(i, 1);
  };
}

export function resetStoreScopedStores(): void {
  modalClosers.forEach((fn) => fn());
  resets.forEach((fn) => fn());
}
