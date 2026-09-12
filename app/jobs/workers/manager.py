import abc
import asyncio
import logging
import os
import socket

from app.jobs.workers.job import IJob

logger = logging.getLogger(__name__)


class IWorkerManager(abc.ABC):
    @abc.abstractmethod
    def start_workers(self, workers_num: int) -> list[asyncio.Task[None]]:
        pass

    @abc.abstractmethod
    def teardown(self) -> None:
        pass

    def get_unique_consumer_name(self, worker_id: int) -> str:
        container_id = os.getenv("HOSTNAME", socket.gethostname())
        return f"worker:{container_id}:{os.getpid()}:task_{worker_id}"


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
                worker_id = self.get_unique_consumer_name(i)
                task = asyncio.create_task(job.execute(shutdown_event=self._shutdown_event, worker_id=worker_id))
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
