"""Cucumber Java Skill — bridges the existing CucumberJavaGenerator into the skill framework.

This wraps the LLM-powered CucumberJavaGenerator from verify.generators.cucumber_java
as a VerificationSkill, making it available through dispatch_skills().
"""

import os
import yaml

from verify.skills.framework import VerificationSkill, register_skill


class CucumberJavaSkill(VerificationSkill):
    """Bridges the CucumberJavaGenerator into the skill framework.

    This skill delegates to the existing LLM-powered generator but exposes
    the same interface as other verification skills.
    """

    skill_id = "cucumber_java"
    name = "Cucumber Java"
    description = "Generate Cucumber/Gherkin + Java step definitions from spec contracts"
    input_types = frozenset({"api_behavior"})
    output_format = ".feature"
    framework = "cucumber"
    version = "1.0.0"

    def generate(
        self,
        spec: dict,
        requirement: dict,
        constitution: dict,
    ) -> str:
        """Generate Cucumber feature file by delegating to the existing generator."""
        from verify.generators.cucumber_java import CucumberJavaGenerator
        from verify.llm_client import LLMClient

        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
            temp_spec_path = f.name

        try:
            generator = CucumberJavaGenerator()
            llm = LLMClient()
            generated_files = generator.generate(temp_spec_path, constitution, llm)

            generator.write(generated_files)

            for path, content in generated_files.files.items():
                if path.endswith(".feature"):
                    return content

            if generated_files.files:
                return next(iter(generated_files.files.values()))

            return ""
        finally:
            os.unlink(temp_spec_path)

    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the output path from the verification entry or construct one."""
        for ver in requirement.get("verification", []):
            if ver.get("skill") == self.skill_id:
                return ver.get("output", "")

        jira_key = spec.get("meta", {}).get("jira_key", "UNKNOWN")
        safe_key = jira_key.replace("-", "_")
        return f".verify/generated/{safe_key}.feature"


# Auto-register on import
_skill = CucumberJavaSkill()
register_skill(_skill)
