# modules/project/__init__.py
"""
Project Module

Module untuk mengelola:
- Project management (CRUD)
- Tasks management
- Labor management
- Expenses management
- Timeline/Milestone management
- Documents management
- Price list items integration
- Stages management
- Financial summary
"""

from .models import (
    Project,
    ProjectTask,
    ProjectExpense,
    ProjectLabor,
    ProjectActivity,
    ProjectStage,
    ProjectPriceListItem,
    ProjectTimeline,
    ProjectDocument,
    ProjectTeam,
)

from .schemas import (
    # Project
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectMinimalResponse,
    ProjectUpdateStatus,
    ProjectUpdateProgress,
    ProjectCancel,
    # Task
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskResponse,
    # Labor
    ProjectLaborCreate,
    ProjectLaborResponse,
    # Expense
    ProjectExpenseCreate,
    ProjectExpenseResponse,
    # Price List
    ProjectPriceListItemResponse,
    # Timeline
    ProjectTimelineCreate,
    ProjectTimelineUpdate,
    ProjectTimelineResponse,
    # Document
    ProjectDocumentCreate,
    ProjectDocumentUpdate,
    ProjectDocumentResponse,
    ProjectDocumentUpload,
    # Team
    ProjectTeamCreate,
    ProjectTeamResponse,
    # Stage
    ProjectStageCreate,
    ProjectStageUpdate,
    ProjectStageResponse,
    # Financial
    ProjectFinancialSummary,
    ProjectDetailResponse,
    # Kanban
    ProjectKanbanItem,
    ProjectKanbanResponse,
    # Statistics
    ProjectStatisticsResponse,
    ProjectFinancialSummaryResponse,
    # Material
    ProjectMaterialSummary,
    ProjectLaborSummary,
)

from .repository import ProjectRepository
from .services import ProjectService
from .router import project_router

__all__ = [
    # Models
    "Project",
    "ProjectTask",
    "ProjectExpense",
    "ProjectLabor",
    "ProjectActivity",
    "ProjectStage",
    "ProjectPriceListItem",
    "ProjectTimeline",
    "ProjectDocument",
    "ProjectTeam",
    # Schemas - Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectMinimalResponse",
    "ProjectUpdateStatus",
    "ProjectUpdateProgress",
    "ProjectCancel",
    # Schemas - Task
    "ProjectTaskCreate",
    "ProjectTaskUpdate",
    "ProjectTaskResponse",
    # Schemas - Labor
    "ProjectLaborCreate",
    "ProjectLaborResponse",
    # Schemas - Expense
    "ProjectExpenseCreate",
    "ProjectExpenseResponse",
    # Schemas - Price List
    "ProjectPriceListItemResponse",
    # Schemas - Timeline
    "ProjectTimelineCreate",
    "ProjectTimelineUpdate",
    "ProjectTimelineResponse",
    # Schemas - Document
    "ProjectDocumentCreate",
    "ProjectDocumentUpdate",
    "ProjectDocumentResponse",
    "ProjectDocumentUpload",
    # Schemas - Team
    "ProjectTeamCreate",
    "ProjectTeamResponse",
    # Schemas - Stage
    "ProjectStageCreate",
    "ProjectStageUpdate",
    "ProjectStageResponse",
    # Schemas - Financial
    "ProjectFinancialSummary",
    "ProjectDetailResponse",
    # Schemas - Kanban
    "ProjectKanbanItem",
    "ProjectKanbanResponse",
    # Schemas - Statistics
    "ProjectStatisticsResponse",
    "ProjectFinancialSummaryResponse",
    # Schemas - Material
    "ProjectMaterialSummary",
    "ProjectLaborSummary",
    # Repository
    "ProjectRepository",
    # Service
    "ProjectService",
    # Router
    "project_router",
]
