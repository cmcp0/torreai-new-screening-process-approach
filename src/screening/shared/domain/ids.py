from typing import Union
from uuid import UUID


def _uuid(v: Union[str, UUID]) -> UUID:
    return v if isinstance(v, UUID) else UUID(str(v))


class ApplicationId:
    def __init__(self, value: Union[str, UUID]) -> None:
        self._value = _uuid(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApplicationId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class CandidateId:
    def __init__(self, value: Union[str, UUID]) -> None:
        self._value = _uuid(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CandidateId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class JobOfferId:
    def __init__(self, value: Union[str, UUID]) -> None:
        self._value = _uuid(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JobOfferId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class CallId:
    def __init__(self, value: Union[str, UUID]) -> None:
        self._value = _uuid(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CallId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class AnalysisId:
    def __init__(self, value: Union[str, UUID]) -> None:
        self._value = _uuid(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AnalysisId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
