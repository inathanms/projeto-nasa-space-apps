"""Single-flight por processo (REQ-531).

Requisições concorrentes com a mesma chave compartilham uma única execução
de `factory`. O trabalho roda em uma task própria, protegida por
`asyncio.shield`: cancelar um chamador não cancela o trabalho nem os demais.
A entrada é removida quando a task termina, com sucesso ou erro.
"""

import asyncio
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, TypeVar

T = TypeVar("T")


class SingleFlight:
    def __init__(self) -> None:
        self._inflight: dict[Hashable, asyncio.Task[Any]] = {}

    async def do(self, key: Hashable, factory: Callable[[], Awaitable[T]]) -> T:
        task = self._inflight.get(key)
        if task is None or task.done():
            task = asyncio.ensure_future(factory())
            self._inflight[key] = task
            task.add_done_callback(lambda t, k=key: self._release(k, t))
        return await asyncio.shield(task)

    def _release(self, key: Hashable, task: asyncio.Task[Any]) -> None:
        if self._inflight.get(key) is task:
            del self._inflight[key]
        # Marca a exceção como recuperada mesmo quando todos os chamadores
        # já cancelaram, evitando o aviso "exception was never retrieved".
        if not task.cancelled():
            task.exception()
