import abc
import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)



class IJob(abc.ABC):
    @abc.abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass


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
