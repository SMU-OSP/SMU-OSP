import { ApiFailure, ApiSuccess, ErrorCode } from "../types/response";

export function success<T>(data: T): ApiSuccess<T> {
  return {
    status: "SUCCESS",
    data,
    detail: null,
  };
}

export function fail(
  code: ErrorCode,
  message: string,
  httpStatus = 400
): ApiFailure {
  return {
    status: code,
    data: null,
    detail: { message, httpStatus },
  };
}

export function serverError(
  code: ErrorCode = "INTERNAL_SERVER_ERROR",
  message = "서버 내부 오류가 발생했습니다."
): ApiFailure {
  return {
    status: code,
    data: null,
    detail: { message, httpStatus: 500 },
  };
}
