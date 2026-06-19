from enum import Enum

class InquiryStatus(str, Enum):
    NEW = "new"
    REVIEW = "review"
    QUOTED = "quoted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    COMPLETED = "completed"   # baru

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"