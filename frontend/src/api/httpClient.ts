import { env } from "../config/env";
import type { ErrorResponse } from "../domain/common";

/** Thrown for any non-2xx response; `detail` mirrors the backend's {"detail": ...} envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorResponse | null;
    throw new ApiError(response.status, body?.detail ?? response.statusText);
  }

  return (await response.json()) as TResponse;
}

export const httpClient = {
  get: <TResponse>(path: string): Promise<TResponse> => request<TResponse>(path, { method: "GET" }),
  post: <TResponse>(path: string, body: unknown): Promise<TResponse> =>
    request<TResponse>(path, { method: "POST", body: JSON.stringify(body) }),
};
