from typing import List, Dict, Any
from datetime import datetime
import json
from models import PromptLog

class PromptTracer:
    def __init__(self):
        self.stages: List[PromptLog] = []

    def add_stage(self, stage: str, system_prompt: str, user_prompt: str, raw_response: str, parsed_response: Any, token_usage: Dict[str, int] = None):
        if not isinstance(parsed_response, str):
            try:
                parsed_response = json.dumps(parsed_response, default=lambda x: getattr(x, '__dict__', str(x)))
            except Exception:
                parsed_response = str(parsed_response)

        log = PromptLog(
            stage=stage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            parsed_response=parsed_response,
            timestamp=datetime.utcnow().isoformat() + "Z",
            token_usage=token_usage
        )
        self.stages.append(log)
