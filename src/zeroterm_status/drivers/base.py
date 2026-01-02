from __future__ import annotations

from abc import ABC, abstractmethod


class DisplayError(RuntimeError):
    pass


class BaseDisplay(ABC):
    width: int
    height: int

    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def show(self, image) -> None:
        raise NotImplementedError

    @abstractmethod
    def sleep(self) -> None:
        raise NotImplementedError