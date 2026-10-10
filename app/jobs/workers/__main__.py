import asyncio
import logging
import signal

from app.core.logging import configure_logging
from app.jobs.workers.bid_loop import bid_processor_loop
from app.jobs.workers.job import IntervalJob
from app.jobs.workers.manager import InProcessWorkerManager

configure_logging()
logger = logging.getLogger(__name__)

shutdown_event: asyncio.Event = asyncio.Event()


async def start_workers():
    bid_job = IntervalJob(job_task=bid_processor_loop, seconds=10)
    workers = InProcessWorkerManager(shutdown_event, [bid_job])
    loop = asyncio.get_running_loop()

    def handle_shutdown():
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown)

    try:
        workers.start_workers()
        logger.info("[app.jobs.workers]: workers started successfully")
    except Exception as e:
        logger.exception(f"[app.jobs.workers]: Something went wrong with workers {str(e)}")
        await workers.teardown()

    await shutdown_event.wait()
    await workers.teardown()


asyncio.run(start_workers())
