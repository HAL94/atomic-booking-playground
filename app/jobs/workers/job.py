import abc
import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IJob(abc.ABC):
    @abc.abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    async def on_start(self, handler: Callable[..., Awaitable[Any]], *args, **kwargs) -> None:
        pass


class BasicJob(IJob):
    def __init__(
        self,
        job_task: Callable[..., Awaitable[Any]],
        *args,
        **kwargs,
    ) -> None:
        self.job_task = job_task
        self._on_start: Optional[Callable[..., Awaitable[Any]]] = None
        self.args = args
        self.kwargs = kwargs

    async def on_start(self, handler: Callable[..., Awaitable[Any]], *args, **kwargs) -> None:
        if not handler:
            return None

        async def handler_wrapper():
            return await handler(*args, **kwargs)

        self._on_start = handler_wrapper

    async def execute(self, shutdown_event: asyncio.Event, worker_id: str):
        if not self.job_task:
            raise ValueError("[Job]: job task was not passed")

        logger.info(f"[Worker {worker_id}] Sweeper task started.")

        if self._on_start:
            await self._on_start()

        while not shutdown_event.is_set():
            try:
                await self.job_task(worker_id, *self.args, **self.kwargs)
            except asyncio.CancelledError:
                logger.info(f"[Worker {worker_id}] Received cancellation. Exiting loop.")
                break
            except Exception as e:
                logger.exception(f"[Worker {worker_id}] Unhandled error in job task: {e}")
                # CRITICAL: Prevent CPU thrashing / log flooding when infra services fail
                await asyncio.sleep(1)

        logger.info(f"[Worker {worker_id}] Worker loop terminated cleanly.")


class IntervalJob(IJob):
    def __init__(
        self,
        job_task: Callable[..., Awaitable[Any]],
        seconds: int = 10,
        *args,
        **kwargs,
    ) -> None:
        self.job_task = job_task
        # Used for intervals
        self.seconds = seconds
        self.args = args
        self.kwargs = kwargs

    def set_interval(self, seconds: int = 10) -> Any:
        self.seconds = seconds

    async def execute(self, shutdown_event: asyncio.Event, worker_id: int):
        if not self.job_task:
            raise ValueError("[Job]: job task was not passed")

        while not shutdown_event.is_set():
            try:
                await self.job_task(worker_id, *self.args, **self.kwargs)
                # Sleep interval (shorter than TTL to allow smooth leader transition if leader crashes)
                jitter = random.uniform(-3, 3)
                sleep_duration = max(1.0, self.seconds + jitter)
                await asyncio.sleep(sleep_duration)  # with jitter
            except asyncio.CancelledError:
                logger.info(f"[Worker {worker_id}] Received forced cancellation. Exitting cleanly..")
                break
            except Exception as e:
                logger.exception(f"Error in background sweeper loop: {e}")
        if shutdown_event.is_set():
            logger.info(f"[Worker {worker_id}] shutdown event is set..clearing.. ")
