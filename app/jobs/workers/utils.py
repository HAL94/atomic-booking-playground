from enum import StrEnum


class JobStatus(StrEnum):
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
