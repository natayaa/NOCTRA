from enum import Enum

class InquiryStatus(str, Enum):
    NEW = "new"
    REVIEW = "review"
    QUOTED = "quoted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    COMPLETED = "completed"   # baru

# constants.py
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "canceled"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    PREPARATION = "preparation"
    PAINTING = "painting"