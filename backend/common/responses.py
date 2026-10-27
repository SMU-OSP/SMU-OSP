def success(data, detail=None):
    return {
        "status": "SUCCESS",
        "data": data,
        "detail": detail,
    }


def fail(code, message, http_status):
    return {
        "status": code,
        "data": None,
        "detail": {
            "message": message,
            "httpStatus": http_status,
        },
    }
