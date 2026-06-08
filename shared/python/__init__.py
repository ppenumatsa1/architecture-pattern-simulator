from __future__ import annotations

from .models import RiskResult, Submission, TimelineEvent
from .risk_rules import evaluate_risk
from .timeline import create_timeline_event, create_timeline_payload

__all__ = [
    "RiskResult",
    "Submission",
    "TimelineEvent",
    "create_timeline_event",
    "create_timeline_payload",
    "evaluate_risk",
]

try:
    from .db import get_database_settings as get_database_settings
    from .db import get_db_session as get_db_session
    from .db import get_engine as get_engine
    from .db import session_scope as session_scope

    __all__.extend(
        ["get_database_settings", "get_db_session", "get_engine", "session_scope"]
    )
except ModuleNotFoundError:
    pass

try:
    from .redis_client import RISK_RESULTS_STREAM as RISK_RESULTS_STREAM
    from .redis_client import SUBMISSION_REQUESTS_STREAM as SUBMISSION_REQUESTS_STREAM
    from .redis_client import RedisStreams as RedisStreams
    from .redis_client import get_redis_client as get_redis_client
    from .redis_client import get_redis_settings as get_redis_settings

    __all__.extend(
        [
            "RISK_RESULTS_STREAM",
            "SUBMISSION_REQUESTS_STREAM",
            "RedisStreams",
            "get_redis_client",
            "get_redis_settings",
        ]
    )
except ModuleNotFoundError:
    pass
