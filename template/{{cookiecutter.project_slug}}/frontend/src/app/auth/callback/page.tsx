{%- if cookiecutter.enable_oauth %}
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { Card, CardContent } from "@/components/ui";
import { ROUTES } from "@/lib/constants";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    const handleCallback = async () => {
      const accessToken = searchParams.get("access_token");
      const refreshToken = searchParams.get("refresh_token");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError(errorParam);
        setTimeout(() => {
          router.push(ROUTES.LOGIN);
        }, 3000);
        return;
      }

      if (accessToken && refreshToken) {
        // Store tokens - the API route will handle this
        try {
          const response = await fetch("/api/auth/oauth-callback", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ accessToken, refreshToken }),
          });

          if (response.ok) {
            // Refresh auth state
            await checkAuth();
            router.push(ROUTES.DASHBOARD);
          } else {
            setError("Failed to complete authentication");
            setTimeout(() => {
              router.push(ROUTES.LOGIN);
            }, 3000);
          }
        } catch {
          setError("Authentication error");
          setTimeout(() => {
            router.push(ROUTES.LOGIN);
          }, 3000);
        }
      } else {
        setError("Missing authentication tokens");
        setTimeout(() => {
          router.push(ROUTES.LOGIN);
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, router, checkAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          {error ? (
            <div className="text-center">
              <p className="text-destructive mb-2">{error}</p>
              <p className="text-sm text-muted-foreground">
                Redirecting to login...
              </p>
            </div>
          ) : (
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
              <p className="text-muted-foreground">
                Completing authentication...
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
{%- else %}
export default function AuthCallbackPage() {
  return <div>OAuth not enabled</div>;
}
{%- endif %}
