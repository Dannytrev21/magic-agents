"""Cucumber Java Skill — bridges the existing CucumberJavaGenerator into the skill framework.

This wraps the LLM-powered CucumberJavaGenerator from verify.generators.cucumber_java
as a VerificationSkill, making it available through dispatch_skills().
"""

import os
import yaml

from verify.skills.framework import VerificationSkill, register_skill


@register_skill
class CucumberJavaSkill(VerificationSkill):
    """Bridges the CucumberJavaGenerator into the skill framework.

    This skill delegates to the existing LLM-powered generator but exposes
    the same interface as other verification skills.
    """

    skill_id = "cucumber_java"
    name = "Cucumber Java Generator"
    description = "Generate Cucumber feature files and Java step definitions from spec contracts."
    input_types = frozenset({"api_behavior", "compliance"})
    output_format = ".feature"
    framework = "cucumber"
    version = "1.0.0"

    def generate(
        self,
        spec: dict,
        requirement: dict,
        constitution: dict,
    ) -> str:
        """Generate Cucumber feature file by delegating to the existing generator.

        Note: The CucumberJavaGenerator produces TWO files (.feature + .java).
        This skill generates the .feature content; the .java file is written
        as a side effect via the generator's write() method.
        """
        from verify.generators.cucumber_java import CucumberJavaGenerator
        from verify.llm_client import LLMClient

        # The existing generator needs a spec file path, so we write a temp spec
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

            # Write all generated files (feature + step defs)
            generator.write(generated_files)

            # Return the feature file content (the primary output)
            for path, content in generated_files.files.items():
                if path.endswith(".feature"):
                    return content

            # Fallback: return the first file's content
            if generated_files.files:
                return next(iter(generated_files.files.values()))

            return ""
        finally:
            os.unlink(temp_spec_path)

    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the feature output path from the verification block."""
        for verification in requirement.get("verification", []):
            output = verification.get("output")
            if output:
                return output

        jira_key = spec.get("meta", {}).get("jira_key", "unknown")
        safe_key = jira_key.lower().replace("-", "_")
        return f".verify/generated/{safe_key}.feature"
