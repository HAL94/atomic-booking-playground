import abc
import asyncio
import logging
import os

from app.jobs.workers.job import IJob
from app.jobs.workers.worker_loop import run_worker_loop

logger = logging.getLogger(__name__)


class IWorkerManager(abc.ABC):
    @abc.abstractmethod
    def start_workers(self, workers_num: int) -> list[asyncio.Task[None]]:
        pass

    @abc.abstractmethod
    def teardown(self) -> None:
        pass


class InProcessWorkerManager(IWorkerManager):
    _shutdown_event: asyncio.Event

    def __init__(self, shutdown_event: asyncio.Event, tasks: list[IJob]):
        self._shutdown_event = shutdown_event
        self.jobs = tasks
        self._tasks: list[asyncio.Task[None]] = []

    def start_workers(self, workers_num: int = 2) -> None:
        """Create and start N worker tasks. Returns list of tasks for await on shutdown"""
        tasks: list[asyncio.Task[None]] = []

        for i in range(workers_num):
            for job in self.jobs:
                task = asyncio.create_task(job.execute(shutdown_event=self._shutdown_event, worker_id=i))
                tasks.append(task)

        logger.info(f"Workers created (startup/reload). Pid {os.getpid()} worker_count: {workers_num}")
        self._tasks = tasks

    async def teardown(self):
        self._shutdown_event.set()
        if self._tasks:
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        logger.info("All background worker tasks stopped cleanly.")


def start_worker(shutdown_event: asyncio.Event, workers_num: int = 2) -> list[asyncio.Task[None]]:
    """Create and start N worker tasks. Returns list of tasks for await on shutdown"""
    tasks: list[asyncio.Task[None]] = []

    for i in range(workers_num):
        task = asyncio.create_task(run_worker_loop(_worker_id=i, shutdown_event=shutdown_event))
        tasks.append(task)

    logger.info(f"Workers created (startup/reload). Pid {os.getpid()} worker_count: {workers_num}")

    return tasks
