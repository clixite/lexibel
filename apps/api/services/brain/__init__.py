"""Brain Intelligence Engine — Central AI services for LexiBel case management.

Provides case analysis, deadline intelligence, communication scoring,
and proactive insights to Belgian lawyers managing their practice.
"""

from apps.api.services.brain.case_analyzer import (
    CaseAnalyzer,
    CaseHealth,
    CompletenessElement,
    CompletenessReport,
    HealthComponent,
    RiskAssessment,
    RiskFactor,
    StrategySuggestion,
)
from apps.api.services.brain.communication_scorer import (
    CommunicationGap,
    CommunicationHealth,
    CommunicationScorer,
    PartyContact,
    SentimentMoment,
    SentimentTrend,
    UrgencyIndicator,
    UrgencyScore,
)
from apps.api.services.brain.deadline_intelligence import (
    DeadlineAnalysis,
    DeadlineConflict,
    DeadlineIntelligence,
    DeadlineItem,
    FilingSuggestion,
    LegalDeadline,
    WeekWorkload,
    WorkloadPrediction,
)
from apps.api.services.brain.orchestrator import (
    ActionSuggestion,
    BrainOrchestrator,
    BrainSummary,
    CaseAnalysis,
    DeadlineSummary,
    InsightResult,
)

__all__ = [
    # Orchestrator
    "BrainOrchestrator",
    "CaseAnalysis",
    "InsightResult",
    "ActionSuggestion",
    "BrainSummary",
    "DeadlineSummary",
    # Case Analyzer
    "CaseAnalyzer",
    "RiskAssessment",
    "RiskFactor",
    "CompletenessReport",
    "CompletenessElement",
    "StrategySuggestion",
    "CaseHealth",
    "HealthComponent",
    # Deadline Intelligence
    "DeadlineIntelligence",
    "DeadlineAnalysis",
    "DeadlineItem",
    "DeadlineConflict",
    "LegalDeadline",
    "FilingSuggestion",
    "WeekWorkload",
    "WorkloadPrediction",
    # Communication Scorer
    "CommunicationScorer",
    "CommunicationHealth",
    "CommunicationGap",
    "PartyContact",
    "UrgencyScore",
    "UrgencyIndicator",
    "SentimentTrend",
    "SentimentMoment",
]
