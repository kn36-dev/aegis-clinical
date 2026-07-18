import { env } from "../config/env";

/** Thrown for any non-2xx response; `detail` is always normalized to a displayable string. */
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

/** A single FastAPI/Pydantic `RequestValidationError` item, as seen in a 422 body. */
interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
}

/**
 * The backend always responds with a `{"detail": ...}` envelope, but `detail`
 * itself has two shapes depending on where the error originates: routers
 * raising `HTTPException` send a plain string (`ErrorResponse.detail`, see
 * aegis.api.schemas.errors), while FastAPI's own request-body validation
 * (422s — e.g. a malformed patient_id) bypasses that schema and sends its
 * default `list[ValidationErrorItem]` instead. This normalizes both into one
 * string so the rest of the frontend never has to know about that transport
 * inconsistency.
 */
function normalizeDetail(body: unknown, fallback: string): string {
  if (body === null || typeof body !== "object" || !("detail" in body)) {
    return fallback;
  }
  const detail = (body as { detail: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const { loc, msg } = item as ValidationErrorItem;
            const field = loc?.filter((segment) => segment !== "body").join(".");
            return field ? `${field}: ${msg}` : String(msg);
          }
          return JSON.stringify(item);
        })
        .join("; ") || fallback
    );
  }

  return fallback;
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
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(response.status, normalizeDetail(body, response.statusText));
  }

  return (await response.json()) as TResponse;
}

export const httpClient = {
  get: <TResponse>(path: string): Promise<TResponse> => request<TResponse>(path, { method: "GET" }),
  post: <TResponse>(path: string, body: unknown): Promise<TResponse> =>
    request<TResponse>(path, { method: "POST", body: JSON.stringify(body) }),
};
