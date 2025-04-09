from dataclasses import dataclass


@dataclass
class Task:
    id: int
    name: str
    comment: str
    description: str
    priority: int
    tag: str
    done: bool = False
