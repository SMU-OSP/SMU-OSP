from collections.abc import Callable
from functools import wraps
from typing import Any

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from common.responses import fail


def project_login_required(
    view_method: Callable[..., Response],
) -> Callable[..., Response]:
    """프로젝트 API의 기존 로그인 실패 응답을 유지한다.

    Args:
        view_method: 인증 이후 실행할 APIView 메서드.

    Returns:
        로그인 확인이 추가된 APIView 메서드.
    """

    @wraps(view_method)
    def wrapped_view(
        view: Any,
        request: Request,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        return view_method(view, request, *args, **kwargs)

    return wrapped_view
