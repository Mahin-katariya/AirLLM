"""Abstract inference backend."""

from __future__ import annotations

from abc import ABC, abstractmethod

from buscraft.models.inference import InferenceRequest, InferenceResponse


class InferenceBackend(ABC):
    backend_id: str = "abstract"

    @abstractmethod
    def complete(self, req: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True
