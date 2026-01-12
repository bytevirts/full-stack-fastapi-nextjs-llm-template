
"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from "@/components/ui";
import type { BillingSummary, CheckoutRequest, CheckoutResponse } from "@/types";

export default function BillingPage() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<BillingSummary>("/billing/summary");
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load billing data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const startCheckout = async (payload: CheckoutRequest, label: string) => {
    try {
      setCheckoutLoading(label);
      const data = await apiClient.post<CheckoutResponse>("/billing/checkout", payload);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setCheckoutLoading(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading billing...</p>;
  }

  if (!summary) {
    return <p className="text-sm text-muted-foreground">No billing data.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">Billing</h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Manage your credits and subscriptions.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 sm:pb-4">
            <CardTitle className="text-base sm:text-lg">Monthly Credits</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.wallet.monthly_remaining}</p>
            <p className="text-xs text-muted-foreground">Remaining this cycle</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 sm:pb-4">
            <CardTitle className="text-base sm:text-lg">Prepaid Balance</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.wallet.prepaid_balance}</p>
            <p className="text-xs text-muted-foreground">Credits available</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 sm:pb-4">
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              Subscription
              <Badge variant="secondary">
                {summary.subscription?.status ?? "inactive"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Monthly credits</span>
              <span className="font-medium">
                {summary.subscription?.monthly_credits ?? 0}
              </span>
            </div>
            {summary.subscription?.current_period_end && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Renews</span>
                <span>
                  {new Date(summary.subscription.current_period_end).toLocaleDateString()}
                </span>
              </div>
            )}
            <Button
              className="w-full"
              onClick={() => startCheckout({ kind: "subscription" }, "subscription")}
              disabled={checkoutLoading === "subscription"}
            >
              {checkoutLoading === "subscription" ? "Redirecting..." : "Subscribe"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2 sm:pb-4">
          <CardTitle className="text-base sm:text-lg">Credit Packs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {summary.credit_packs.map((pack) => {
              const label = `pack-${pack.credits}`;
              return (
                <div
                  key={pack.credits}
                  className="rounded-lg border p-4 flex flex-col gap-3"
                >
                  <div>
                    <p className="text-lg font-semibold">{pack.credits} credits</p>
                    <p className="text-sm text-muted-foreground">
                      ${pack.price_usd.toFixed(2)} USD
                    </p>
                  </div>
                  <Button
                    onClick={() =>
                      startCheckout(
                        { kind: "credit_pack", pack_credits: pack.credits },
                        label
                      )
                    }
                    disabled={checkoutLoading === label}
                  >
                    {checkoutLoading === label ? "Redirecting..." : "Buy Pack"}
                  </Button>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 sm:pb-4">
          <CardTitle className="text-base sm:text-lg">Recent Usage</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.recent_ledger.length === 0 ? (
            <p className="text-sm text-muted-foreground">No usage yet.</p>
          ) : (
            <div className="space-y-2">
              {summary.recent_ledger.map((entry) => (
                <div
                  key={entry.id}
                  className="flex flex-col gap-2 rounded-lg border p-3 text-sm sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium">
                      {entry.model_name ?? "model"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(entry.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>Total tokens: {entry.total_tokens}</span>
                    <span>Credits: {entry.cost_credits}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
