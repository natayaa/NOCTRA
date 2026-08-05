import enum


class RestoredBikeStatus(str, enum.Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    FEATURED = "featured"


class InitialCondition(str, enum.Enum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"
