"""Config validation summary with no side effects."""

import json

from .config import resolve_team_config
from .roles import resolve_roles
from .state import get_pipeline_stages


def cmd_validate(args, config: dict) -> None:
    """Validate config and return a small summary without creating run state."""
    pipeline_mode, isolation_mode = resolve_team_config(config)
    roles = resolve_roles(config)
    stages = get_pipeline_stages(config)

    result = {
        "valid": True,
        "pipeline_mode": pipeline_mode or "standalone",
        "isolation_mode": isolation_mode,
        "role_count": len(roles),
        "stage_count": len(stages),
    }
    print(json.dumps(result))
