
import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "sample_billing_app_v2-frontend",
  });
}
