"""Jira Cloud REST API client for reading tickets and writing updates.

All Jira operations are 100% deterministic — zero AI.
"""

from __future__ import annotations

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for Jira Cloud REST API v3."""

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        self.auth = (self.email, self.api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # ── Read operations ──

    def fetch_ticket(self, jira_key: str) -> dict:
        """Fetch a Jira issue by key. Returns the raw issue JSON."""
        url = f"{self.base_url}/rest/api/3/issue/{jira_key}"
        response = requests.get(url, auth=self.auth, headers=self.headers)

        if response.status_code == 401:
            raise JiraAuthError(f"Authentication failed for {self.base_url}. Check JIRA_EMAIL and JIRA_API_TOKEN.")
        if response.status_code == 404:
            raise JiraNotFoundError(f"Ticket {jira_key} not found.")
        response.raise_for_status()

        return response.json()

    def get_acceptance_criteria(self, jira_key: str) -> list[dict]:
        """Fetch a ticket and extract its acceptance criteria checkboxes."""
        issue = self.fetch_ticket(jira_key)
        return self.extract_acceptance_criteria(issue)

    def extract_acceptance_criteria(self, issue: dict) -> list[dict]:
        """Extract AC checkboxes from a Jira issue.

        Tries ADF taskList parsing first, falls back to markdown checkbox parsing.
        """
        description = issue.get("fields", {}).get("description")
        if description is None:
            return []

        # Jira Cloud uses ADF (Atlassian Document Format)
        if isinstance(description, dict):
            result = self._parse_adf_checkboxes(description)
            if result:
                return result
            # Fallback: extract plain text from ADF and parse as markdown
            plain_text = self._adf_to_plain_text(description)
            return self.parse_markdown_checkboxes(plain_text)

        # Plain text / markdown description
        if isinstance(description, str):
            return self.parse_markdown_checkboxes(description)

        return []

    # ── Write operations ──

    def tick_checkbox(self, jira_key: str, checkbox_index: int) -> None:
        """Tick a specific AC checkbox on the Jira ticket.

        Fetches the current description, modifies the checkbox, and PUTs it back.
        """
        issue = self.fetch_ticket(jira_key)
        description = issue.get("fields", {}).get("description")

        if isinstance(description, dict):
            updated = self._tick_adf_checkbox(description, checkbox_index)
        elif isinstance(description, str):
            updated = self.tick_markdown_checkbox(description, checkbox_index)
        else:
            logger.warning(f"Cannot tick checkbox: unknown description format for {jira_key}")
            return

        self._update_description(jira_key, updated)

    def tick_checkboxes(self, jira_key: str, indices: list[int]) -> None:
        """Tick multiple AC checkboxes in a single description update."""
        issue = self.fetch_ticket(jira_key)
        description = issue.get("fields", {}).get("description")

        if isinstance(description, dict):
            updated = description
            for idx in indices:
                updated = self._tick_adf_checkbox(updated, idx)
        elif isinstance(description, str):
            updated = description
            for idx in indices:
                updated = self.tick_markdown_checkbox(updated, idx)
        else:
            logger.warning(f"Cannot tick checkboxes: unknown description format for {jira_key}")
            return

        self._update_description(jira_key, updated)

    def post_comment(self, jira_key: str, comment: str) -> dict:
        """Post a comment to a Jira ticket."""
        url = f"{self.base_url}/rest/api/3/issue/{jira_key}/comment"

        # Wrap plain text in ADF paragraph for Jira Cloud API v3
        body = {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        response = requests.post(url, auth=self.auth, headers=self.headers, json=body)
        response.raise_for_status()
        return response.json()

    def get_transitions(self, jira_key: str) -> list[dict]:
        """Get available transitions for a ticket."""
        url = f"{self.base_url}/rest/api/3/issue/{jira_key}/transitions"
        response = requests.get(url, auth=self.auth, headers=self.headers)
        response.raise_for_status()
        return [
            {"id": t["id"], "name": t["name"]}
            for t in response.json().get("transitions", [])
        ]

    def transition_ticket(self, jira_key: str, target_status: str) -> bool:
        """Transition a ticket to a target status (e.g., 'Done').

        Returns True if successful, False if no matching transition found.
        """
        transitions = self.get_transitions(jira_key)
        match = next(
            (t for t in transitions if t["name"].lower() == target_status.lower()),
            None,
        )

        if match is None:
            available = [t["name"] for t in transitions]
            logger.warning(
                f"No transition '{target_status}' available for {jira_key}. "
                f"Available: {available}"
            )
            return False

        url = f"{self.base_url}/rest/api/3/issue/{jira_key}/transitions"
        body = {"transition": {"id": match["id"]}}
        response = requests.post(url, auth=self.auth, headers=self.headers, json=body)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.warning(f"Transition failed for {jira_key}: {e}")
            return False

        return True

    # ── Parsing helpers (static for testability) ──

    @staticmethod
    def parse_markdown_checkboxes(text: str) -> list[dict]:
        """Parse markdown-style checkboxes from text.

        Matches:  - [ ] unchecked item
                  - [x] checked item
                  * [ ] also works with asterisks
        """
        pattern = r"[-*]\s+\[([ xX])\]\s+(.+)"
        results = []
        for i, match in enumerate(re.finditer(pattern, text)):
            checked = match.group(1).lower() == "x"
            results.append({
                "index": i,
                "text": match.group(2).strip(),
                "checked": checked,
            })
        return results

    @staticmethod
    def tick_markdown_checkbox(description: str, checkbox_index: int) -> str:
        """Tick the nth markdown checkbox in a description string.

        Idempotent — ticking an already-checked box is a no-op.
        """
        pattern = r"([-*]\s+\[)([ xX])(\]\s+)"
        count = 0

        def replacer(match):
            nonlocal count
            current_index = count
            count += 1
            if current_index == checkbox_index:
                return match.group(1) + "x" + match.group(3)
            return match.group(0)

        return re.sub(pattern, replacer, description)

    # ── Evidence formatting ──

    @staticmethod
    def format_evidence_comment(verdicts: list[dict], spec_path: str) -> str:
        """Format evaluator verdicts as a Jira-readable evidence comment."""
        lines = [
            "h3. Verification Pipeline Results",
            f"Spec: {{{{{spec_path}}}}}",
            "",
        ]

        all_passed = all(v["passed"] for v in verdicts)
        lines.append(
            f"*Overall: {'(/) ALL PASSED' if all_passed else '(x) FAILURES DETECTED'}*"
        )
        lines.append("")

        for verdict in verdicts:
            icon = "(/)" if verdict["passed"] else "(x)"
            lines.append(f'h4. {icon} AC: "{verdict["ac_text"]}"')
            lines.append(
                f"Condition: {verdict['pass_condition']} | Result: {verdict['summary']}"
            )
            lines.append("")
            lines.append("||Ref||Description||Type||Result||")

            for ev in verdict["evidence"]:
                status = "(/)" if ev["passed"] else "(x)"
                desc = ev.get("description", "")
                ver_type = ev.get("verification_type", "test_result")
                lines.append(f"|{ev['ref']}|{desc}|{ver_type}|{status}|")

            lines.append("")

        lines.extend([
            "----",
            "_Generated by Intent-to-Verification Pipeline_",
            "_Traceability: result -> spec ref -> AC checkbox -> business intent_",
        ])

        return "\n".join(lines)

    # ── Private helpers ──

    def _update_description(self, jira_key: str, description) -> None:
        """PUT an updated description back to the ticket."""
        url = f"{self.base_url}/rest/api/3/issue/{jira_key}"
        body = {"fields": {"description": description}}
        response = requests.put(url, auth=self.auth, headers=self.headers, json=body)
        response.raise_for_status()

    @staticmethod
    def _parse_adf_checkboxes(adf: dict) -> list[dict]:
        """Parse ADF taskList nodes into checkbox dicts."""
        results = []
        index = 0

        def walk(node):
            nonlocal index
            if not isinstance(node, dict):
                return

            if node.get("type") == "taskItem":
                state = node.get("attrs", {}).get("state", "TODO")
                text_parts = []
                for child in node.get("content", []):
                    if child.get("type") == "text":
                        text_parts.append(child.get("text", ""))
                text = " ".join(text_parts).strip()
                if text:
                    results.append({
                        "index": index,
                        "text": text,
                        "checked": state == "DONE",
                    })
                    index += 1

            for child in node.get("content", []):
                walk(child)

        walk(adf)
        return results

    @staticmethod
    def _tick_adf_checkbox(adf: dict, checkbox_index: int) -> dict:
        """Tick the nth taskItem in an ADF document."""
        import copy
        adf = copy.deepcopy(adf)
        count = 0

        def walk(node):
            nonlocal count
            if not isinstance(node, dict):
                return

            if node.get("type") == "taskItem":
                if count == checkbox_index:
                    node.setdefault("attrs", {})["state"] = "DONE"
                count += 1

            for child in node.get("content", []):
                walk(child)

        walk(adf)
        return adf

    @staticmethod
    def _adf_to_plain_text(adf: dict) -> str:
        """Extract plain text from an ADF document for fallback parsing."""
        parts = []

        def walk(node):
            if not isinstance(node, dict):
                return
            if node.get("type") == "text":
                parts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)

        walk(adf)
        return "\n".join(parts)


class JiraAuthError(Exception):
    pass


class JiraNotFoundError(Exception):
    pass
