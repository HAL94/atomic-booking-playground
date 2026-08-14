from typing import Optional

from fastapi import HTTPException, status

from app.core.schema import AppResponse


class AppException(HTTPException):
    """
    Base exception for application
    """

    def __init__(
        self,
        status_code: int,
        internal_code: Optional[int] = None,
        message: Optional[str] = "Internal Server Error",
    ):
        self.status_code = status_code
        self.message = message
        self.internal_code = internal_code
        super().__init__(status_code=status_code, detail=message)

    def dict(self) -> dict:
        return AppResponse(
            success=False,
            status_code=self.status_code,
            message=self.message,
        ).model_dump(by_alias=True)


class BadRequestException(AppException):
    """
    Bad request exception
    """

    def __init__(self, message: str = "Requested resource is not found"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)


class AlreadyExistException(AppException):
    """
    Already exist resource error exception
    """

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, message=message)


class UnauthorizedException(AppException):
    """
    Base exception for unauthorized access errors.
    """

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, message=message)


class ForbiddenException(AppException):
    """
    Base exception for forbidden errors.
    """

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, message=message)


class InternalFailureException(AppException):
    """
    Base exception for unknown errors.
    """

    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=message)


class NotFoundException(AppException):
    """
    Base exception for not found errors.
    """

    def __init__(self, message: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message)
