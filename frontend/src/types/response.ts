export interface ApiSuccess<T> {
  status: "SUCCESS";
  data: T;
  detail: null;
}

export interface ApiFailure {
  status: ErrorCode;
  data: null;
  detail: { message: string; httpStatus: number };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export const ERROR_CODES = {
  PROJECT_NOT_FOUND: "PROJECT_NOT_FOUND",
  INVALID_PROJECT_INPUT: "INVALID_PROJECT_INPUT",
  INVALID_GITHUB_URL: "INVALID_GITHUB_URL",
  GITHUB_REPOSITORY_NOT_FOUND: "GITHUB_REPOSITORY_NOT_FOUND",
  GITHUB_RATE_LIMIT_EXCEEDED: "GITHUB_RATE_LIMIT_EXCEEDED",
  PRIVATE_REPOSITORY: "PRIVATE_REPOSITORY",
  PERMISSION_DENIED: "PERMISSION_DENIED",
  REQUIRED_FIELD_MISSING: "REQUIRED_FIELD_MISSING",
  INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];
