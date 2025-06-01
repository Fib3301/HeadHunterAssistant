from typing import Dict, Any
from .tools import Executor
from ..types import ExecutorType

map_type = ExecutorType.RESTAPIHANDLER

map = {
    "get-current-user-info": Executor.hh_get_current_user_info,
    "get-active-vacancy-list": Executor.hh_get_active_vacancy_list,
    "get-vacancy": Executor.hh_get_vacancy,
    "get-negotiations-list": Executor.hh_get_negotiations_list,
    "get-resume": Executor.hh_get_resume,
    "analyze-resume": Executor.hh_analyze_resume,
    "generate-rejection-message": Executor.hh_generate_rejection_message,
    "generate-invitation-message": Executor.hh_generate_invitation_message,
    "change-negotiation-action": Executor.hh_change_negotiation_state
} 