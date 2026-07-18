const rawBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!rawBaseUrl) {
  throw new Error(
    "VITE_API_BASE_URL is not set. Copy .env.example to .env.local and point it at the backend's base URL.",
  );
}

export const env = {
  apiBaseUrl: rawBaseUrl.replace(/\/$/, ""),
};
