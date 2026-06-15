export interface CreditCtx {
  balance: number;
  usedFree: boolean;
}

export type CreditAction = "free_generate" | "paid_generate" | "buy";

export interface UiStateResult {
  action: CreditAction;
  canDownload: boolean;
}

export function uiState(ctx: CreditCtx): UiStateResult {
  if (ctx.balance > 0) {
    return { action: "paid_generate", canDownload: true };
  }
  if (!ctx.usedFree) {
    return { action: "free_generate", canDownload: false };
  }
  return { action: "buy", canDownload: false };
}
