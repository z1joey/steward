/**
 * T0-11 · 非入账表单防抖自动保存（300–800ms，[C 500ms]；coding-guidelines §2）。
 * 入账 / 结算 / 发放类操作不走此路径，必须显式点击。
 */
import { onBeforeUnmount } from "vue";

export function useDebouncedSave(
  save: () => Promise<unknown>,
  delayMs = 500,
): () => void {
  let timer: number | null = null;

  function schedule(): void {
    if (timer != null) window.clearTimeout(timer);
    timer = window.setTimeout(async () => {
      timer = null;
      await save();
    }, delayMs);
  }

  onBeforeUnmount(() => {
    if (timer != null) window.clearTimeout(timer);
  });

  return schedule;
}
