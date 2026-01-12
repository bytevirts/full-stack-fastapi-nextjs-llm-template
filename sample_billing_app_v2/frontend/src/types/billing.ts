export interface BillingWallet {
  monthly_remaining: number;
  prepaid_balance: number;
}

export interface BillingSubscription {
  status: string;
  plan_name?: string | null;
  monthly_credits: number;
  current_period_start?: string | null;
  current_period_end?: string | null;
  provider?: string | null;
}

export interface BillingCreditPack {
  credits: number;
  price_usd: number;
}

export interface TokenLedgerEntry {
  id: string;
  model_name?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens: number;
  cost_credits: number;
  overage_credits: number;
  created_at: string;
}

export interface BillingSummary {
  wallet: BillingWallet;
  subscription: BillingSubscription | null;
  credit_packs: BillingCreditPack[];
  recent_ledger: TokenLedgerEntry[];
}

export type CheckoutKind = "subscription" | "credit_pack";

export interface CheckoutRequest {
  kind: CheckoutKind;
  pack_credits?: number;
}

export interface CheckoutResponse {
  provider: string;
  checkout_url: string;
}
