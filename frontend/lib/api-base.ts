// Endereço da API SPHEREye usado pelas telas (resolvido no build).
// develop e o dev server passam pelo proxy /api/spherex-dev (rewrites em vercel.json).
const proxy = "/api/spherex-dev";
const configuredApi = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "");

export const apiBase = process.env.VERCEL_GIT_COMMIT_REF === "develop"
  ? proxy
  : configuredApi || (process.env.NODE_ENV === "development" ? proxy : undefined);
