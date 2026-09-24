from typing import Protocol


class AntivirusScanner(Protocol):
    async def scan(self, content: bytes) -> bool: ...


class NoOpAntivirus:
    async def scan(self, content: bytes) -> bool:
        return True
