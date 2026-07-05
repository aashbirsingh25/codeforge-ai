import json
import re
from typing import Any, Dict
from app.planner.exceptions import PlanningParseError


class PlanParser:
    """Parser responsible for extracting, repairing, and validating JSON output from LLM."""

    def extract_json(self, raw_text: str) -> str:
        """Finds the bounding braces `{` and `}` and extracts the inner substring.

        Raises PlanningParseError if no JSON-like structure is found.
        """
        # Find first '{' and last '}'
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        
        if start == -1 or end == -1 or start >= end:
            raise PlanningParseError("No valid JSON object boundaries ('{' and '}') found in response.")
        
        return raw_text[start:end+1]

    def repair_json(self, json_str: str) -> str:
        """Repairs common minor formatting issues returned by LLMs:

        1. Trims markdown code wraps.
        2. Removes trailing commas before closing braces/brackets.
        """
        # Trims spaces
        repaired = json_str.strip()

        # Remove markdown wrappers
        if repaired.startswith("```json"):
            repaired = repaired[7:]
        if repaired.endswith("```"):
            repaired = repaired[:-3]
        repaired = repaired.strip()

        # Remove trailing commas inside objects: e.g. "a": 1, } -> "a": 1 }
        repaired = re.sub(r',\s*\}', '}', repaired)
        # Remove trailing commas inside arrays: e.g. [1, 2, ] -> [1, 2]
        repaired = re.sub(r',\s*\]', ']', repaired)

        return repaired

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """Orchestrates JSON extraction and repair.

        Raises PlanningParseError if final decoding fails.
        """
        if not raw_text or not raw_text.strip():
            raise PlanningParseError("Received empty input text to parse.")

        # 1. Extract JSON object
        json_str = self.extract_json(raw_text)

        # 2. Repair minor formatting errors
        repaired_str = self.repair_json(json_str)

        # 3. Decode
        try:
            return json.loads(repaired_str)
        except json.JSONDecodeError as e:
            # Attempt a common quote repair if keys are wrapped in single quotes
            try:
                # Replace single quotes wrapping keys or values
                fixed_single_quotes = re.sub(r"'\s*([^']*?)\s*'", r'"\1"', repaired_str)
                return json.loads(fixed_single_quotes)
            except Exception:
                raise PlanningParseError(
                    f"Failed to parse LLM response as JSON. Error: {str(e)}\nRaw substring: {repaired_str}"
                ) from e
