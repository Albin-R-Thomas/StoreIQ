export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function api(path: string, method = "GET", data?: unknown) {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
  });
  const result = await response
    .json()
    .catch(() => ({ detail: "The server returned an unreadable response." }));
  if (!response.ok)
    throw new ApiError(
      typeof result.detail === "string"
        ? result.detail
        : JSON.stringify(result.detail),
      response.status,
    );
  if (response.status === 202 && result.status_url) {
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 750));
      const next = await fetch(result.status_url, { credentials: "same-origin" });
      const value = await next.json();
      if (!next.ok) throw new ApiError(value.detail || "Retry the saved message.", next.status);
      if (next.status !== 202) return value;
    }
    throw new ApiError("Your message is saved. Retry to check its result.", 503);
  }
  return result;
}
export const money = (n: number | null | undefined) =>
  n === null || n === undefined
    ? "Not confirmed"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(n);
export const date = (s: string) =>
  new Date(s).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
