export interface PaginationMeta {
  start: number;
  limit: number;
  count: number;
  currentPage: number;
  totalPages: number;
  hasPrevious: boolean;
  hasNext: boolean;
}

export interface PaginationDetail {
  pagination: PaginationMeta;
}

export interface ApiSuccess<T, D = null> {
  status: "SUCCESS";
  data: T;
  detail: D;
}

export interface ApiFailure {
  status: ErrorCode;
  data: null;
  detail: { message: string; httpStatus: number };
}

export type ApiResponse<T, D = null> = ApiSuccess<T, D> | ApiFailure;

export const ERROR_CODES = {
  PROJECT_NOT_FOUND: "PROJECT_NOT_FOUND",
  MEMBERSHIP_NOT_FOUND: "MEMBERSHIP_NOT_FOUND",
  MEMBERSHIP_ALREADY_EXISTS: "MEMBERSHIP_ALREADY_EXISTS",
  MEMBERSHIP_REAPPLICATION_LIMIT: "MEMBERSHIP_REAPPLICATION_LIMIT",
  INVALID_MEMBER_STATUS: "INVALID_MEMBER_STATUS",
  INVALID_PROJECT_STATUS: "INVALID_PROJECT_STATUS",
  INVALID_PROJECT_INPUT: "INVALID_PROJECT_INPUT",
  INVALID_GITHUB_URL: "INVALID_GITHUB_URL",
  GITHUB_REPOSITORY_NOT_FOUND: "GITHUB_REPOSITORY_NOT_FOUND",
  GITHUB_RATE_LIMIT_EXCEEDED: "GITHUB_RATE_LIMIT_EXCEEDED",
  PRIVATE_REPOSITORY: "PRIVATE_REPOSITORY",
  PERMISSION_DENIED: "PERMISSION_DENIED",
  REQUIRED_FIELD_MISSING: "REQUIRED_FIELD_MISSING",
  INVALID_PAGINATION_PARAMETER: "INVALID_PAGINATION_PARAMETER",
  INVALID_PROJECT_FILTER: "INVALID_PROJECT_FILTER",
  INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];
