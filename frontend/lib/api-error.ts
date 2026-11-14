import { isRecord } from "./sequence";

export function apiErrorDetail(payload: unknown) {
  return isRecord(payload) ? payload.detail : undefined;
}
