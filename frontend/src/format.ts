import type { Stream, StreamFilter } from "./api/types";

/** `country accept: MX, AU` */
export function formatFilter(filter: StreamFilter): string {
  const { payload } = filter;
  const value = Array.isArray(payload) ? payload.join(", ") : String(payload ?? "");
  return `${filter.name} ${filter.mode}: ${value}`;
}

export const byPosition = (a: Stream, b: Stream) => a.position - b.position;
