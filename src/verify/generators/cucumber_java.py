"""Cucumber/Gherkin + Java step definition generator — AI-powered."""

import json
import os
import re

import yaml

from verify.generators import register
from verify.generators.base import BaseGenerator, GeneratedFiles
from verify.llm_client import LLMClient

SYSTEM_PROMPT = """\
You are a Cucumber/Gherkin test generator for a Java Spring Boot application.

Given a verification spec YAML and a project constitution, generate TWO files:

1. A Gherkin .feature file with tagged scenarios
2. A Java step definition class that implements the Given/When/Then steps

TAGGING RULES (MUST follow exactly):
- Feature-level tags: @{{jira_key}} @{{first_req_id}}
- Each Scenario tag: @{{req_id}}.{{element_id}}
  - For happy path: @REQ-001.success
  - For failure modes: @REQ-001.FAIL-001
  - For invariants: @REQ-001.INV-001
- These tags are how the evaluation engine traces test results back to Jira AC checkboxes.
- EVERY spec ref in the traceability map MUST have a corresponding tagged scenario.

STEP DEFINITION RULES:
- Package: {package_root}.steps
- Class name: {{JiraKey}}Steps (e.g., DEV17Steps for DEV-17)
- Use @CucumberContextConfiguration with @SpringBootTest(webEnvironment = RANDOM_PORT)
  OR inject TestRestTemplate and @LocalServerPort
- Use the auth mechanism from the constitution (Bearer token in Authorization header)
- Use AssertJ assertions: assertThat(...)
- The step definition class MUST handle all Given/When/Then steps from the .feature file

CONSTITUTION CONTEXT:
- Auth: {auth_mechanism} with token header "{token_header}" and prefix "{token_prefix}"
- Error format: {error_format}
- API base path: {base_path}
- Security invariants: {security_invariants}

Respond with ONLY this JSON structure (no markdown fences, no commentary):
{{
  "feature_content": "the complete .feature file content as a string",
  "step_definition_content": "the complete Java step definition class as a string",
  "step_class_name": "the Java class name (e.g., DEV17Steps)"
}}"""


def _build_system_prompt(constitution: dict) -> str:
    """Inject constitution values into the system prompt."""
    api = constitution.get("api", {})
    auth = api.get("auth", {})
    security = (
        constitution.get("verification_standards", {})
        .get("security_invariants", [])
    )
    source = constitution.get("source_structure", {})
    return SYSTEM_PROMPT.format(
        package_root=source.get("package_root", "com.example"),
        auth_mechanism=auth.get("mechanism", "jwt_bearer"),
        token_header=auth.get("token_header", "Authorization"),
        token_prefix=auth.get("token_prefix", "Bearer "),
        error_format=json.dumps(api.get("error_format", {})),
        base_path=api.get("base_path", "/api/v1"),
        security_invariants="; ".join(security) if security else "None specified",
    )


def _build_user_message(spec: dict, constitution: dict) -> str:
    """Build the user message with trimmed spec + constitution context.

    Only sends the fields the generator needs — meta, requirements, traceability.
    Strips large nested objects to stay within token limits.
    """
    # Trim spec to essential fields
    trimmed_spec = {
        "meta": spec.get("meta", {}),
        "requirements": spec.get("requirements", []),
        "traceability": spec.get("traceability", {}),
    }

    # Trim constitution to what matters for test generation
    trimmed_const = {
        "project": constitution.get("project", {}),
        "source_structure": constitution.get("source_structure", {}),
        "api": constitution.get("api", {}),
        "testing": {
            "unit_framework": constitution.get("testing", {}).get("unit_framework"),
            "assertion_library": constitution.get("testing", {}).get("assertion_library"),
        },
        "verification_standards": constitution.get("verification_standards", {}),
    }

    return (
        "SPEC YAML:\n```yaml\n"
        + yaml.dump(trimmed_spec, default_flow_style=False, sort_keys=False)
        + "```\n\nCONSTITUTION YAML:\n```yaml\n"
        + yaml.dump(trimmed_const, default_flow_style=False, sort_keys=False)
        + "```"
    )


@register("cucumber_java")
class CucumberJavaGenerator(BaseGenerator):
    """Generates Cucumber .feature files + Java step definitions via Claude API."""

    def generate(
        self,
        spec_path: str,
        constitution: dict,
        llm: LLMClient,
        max_retries: int = 1,
    ) -> GeneratedFiles:
        spec = self.load_spec(spec_path)
        jira_key = spec.get("meta", {}).get("jira_key", "UNKNOWN")
        source = constitution.get("source_structure", {})
        package_root = source.get("package_root", "com.example.dogservice")

        system = _build_system_prompt(constitution)
        user_msg = _build_user_message(spec, constitution)

        for attempt in range(max_retries + 1):
            response = llm.chat(system, user_msg, response_format="json", max_tokens=8192)

            if not isinstance(response, dict):
                if attempt < max_retries:
                    user_msg += "\n\nYour previous response was not valid JSON. Please respond with ONLY the JSON structure."
                    continue
                raise ValueError(f"LLM returned non-JSON response: {response!r}")

            feature_content = response.get("feature_content", "")
            step_content = response.get("step_definition_content", "")
            step_class = response.get("step_class_name", f"{_class_name(jira_key)}Steps")

            files = GeneratedFiles()

            # Feature file → test resources
            test_dir = source.get("test", "dog-service/src/test/java")
            # Derive resources path from test java path
            resources_base = test_dir.replace("/java", "/resources")
            feature_path = os.path.join(resources_base, "features", f"{jira_key}.feature")
            files.add(feature_path, feature_content)

            # Step definition → test java
            package_path = package_root.replace(".", "/")
            step_path = os.path.join(test_dir, package_path, "steps", f"{step_class}.java")
            files.add(step_path, step_content)

            # Validate and retry if needed
            valid, errors = self.validate(files)
            if valid:
                return files

            if attempt < max_retries:
                user_msg += (
                    f"\n\nYour previous output had validation errors:\n"
                    + "\n".join(f"- {e}" for e in errors)
                    + "\n\nPlease fix and try again."
                )
                continue

            # Return what we have even if validation failed
            return files

        return files

    def validate(self, generated: GeneratedFiles) -> tuple[bool, list[str]]:
        errors: list[str] = []

        for path, content in generated.files.items():
            if not content or not content.strip():
                errors.append(f"{path}: file is empty")
                continue

            if path.endswith(".feature"):
                self._validate_feature(path, content, errors)
            elif path.endswith(".java"):
                self._validate_java(path, content, errors)

        return len(errors) == 0, errors

    @staticmethod
    def _validate_feature(path: str, content: str, errors: list[str]) -> None:
        if "Feature:" not in content:
            errors.append(f"{path}: missing 'Feature:' declaration")
        if "Scenario:" not in content:
            errors.append(f"{path}: no Scenario found")
        # Check for at least one spec ref tag
        if not re.search(r"@REQ-\d+", content):
            errors.append(f"{path}: no spec ref tags (@REQ-NNN) found")

    @staticmethod
    def _validate_java(path: str, content: str, errors: list[str]) -> None:
        if "package " not in content:
            errors.append(f"{path}: missing 'package' declaration")
        if "import " not in content:
            errors.append(f"{path}: no import statements")
        if "public class " not in content:
            errors.append(f"{path}: missing 'public class' declaration")
        # Check for at least one step annotation
        step_annotations = ["@Given", "@When", "@Then"]
        if not any(ann in content for ann in step_annotations):
            errors.append(f"{path}: no Cucumber step annotations (@Given/@When/@Then)")


def _class_name(jira_key: str) -> str:
    """Convert 'DEV-17' to 'Dev17'."""
    return jira_key.replace("-", "").title() if jira_key else "Generated"
