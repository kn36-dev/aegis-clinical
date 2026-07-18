/**
 * Wire-level mirrors of aegis.models.base — constrained strings on the
 * Python side serialize as plain strings over HTTP.
 */
export type ICDCode = string;
export type UUID = string;

/** Mirrors aegis.api.schemas.errors.ErrorResponse. */
export interface ErrorResponse {
  detail: string;
}
