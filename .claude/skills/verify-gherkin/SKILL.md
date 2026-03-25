---
name: verify-cucumber-java
description: >
  Generate Java Cucumber/Gherkin tests from a compiled SPECify verification spec.
  Takes a spec YAML + project constitution and produces a .feature file with tagged
  scenarios and a Java step definition class. Use when the user wants to generate
  BDD tests, Cucumber features, or Gherkin scenarios from a spec. Triggers on
  "generate tests", "cucumber", "gherkin", "feature file", "step definitions".
---

# Cucumber/Gherkin Test Generator for Java Spring Boot

Generate a Gherkin `.feature` file and a Java step definition class from a SPECify verification spec.

## Input

- **Spec YAML** — compiled from negotiation, contains `meta`, `requirements[]`, and `traceability.ac_mappings[]`
- **Constitution YAML** — project conventions: framework, auth mechanism, error format, source structure, security invariants

## Output

Two files:

1. **`.feature` file** — Gherkin scenarios tagged with spec refs, written to the constitution's test resources directory
2. **Java step definition class** — implements all Given/When/Then steps, written to the constitution's test source directory

## Tagging Contract (MUST follow exactly)

Tags are how the evaluation engine traces test results back to Jira AC checkboxes. Every tag maps to an entry in `traceability.ac_mappings[].required_verifications[].ref`.

| Level | Tag Format | Example |
|-------|-----------|---------|
| Feature | `@{jira_key} @{req_id}` | `@DEV-17 @REQ-001` |
| Scenario (happy path) | `@{req_id}.success` | `@REQ-001.success` |
| Scenario (failure mode) | `@{req_id}.{fail_id}` | `@REQ-001.FAIL-001` |
| Scenario (invariant) | `@{req_id}.{inv_id}` | `@REQ-001.INV-001` |

**Coverage rule:** EVERY ref in the spec's `traceability.ac_mappings[].required_verifications[]` MUST have a corresponding tagged scenario. Missing tags = missing test coverage = AC checkbox cannot be verified.

## Scenario Generation Rules

### From `contract.success` (happy path)
```gherkin
@REQ-001.success
Scenario: Happy path - authenticated user retrieves resource
  Given I have a valid Bearer token
  When I send a GET request to "/api/v1/dogs/1"
  Then the response status should be 200
  And the response should contain "name"
  And the response should contain "breed"
```

### From `contract.failures[]` (one scenario per failure mode)
```gherkin
@REQ-001.FAIL-001
Scenario: No auth token returns 401
  Given I have no authorization header
  When I send a GET request to "/api/v1/dogs/1"
  Then the response status should be 401
  And the response should contain "unauthorized"
```

### From `contract.invariants[]` (security/cross-cutting)
```gherkin
@REQ-001.INV-001
Scenario: Response never contains forbidden fields
  Given I have a valid Bearer token
  When I send a GET request to "/api/v1/dogs/1"
  Then the response status should be 200
  And the response should not contain "password"
  And the response should not contain "ssn"
  And the response should not contain "internalId"
```

## Step Definition Rules

- **Package:** `{constitution.source_structure.package_root}.steps`
- **Class name:** `{JiraKey}Steps` — e.g., `DEV17Steps` for ticket DEV-17
- **Spring integration:** Use `@CucumberContextConfiguration` + `@SpringBootTest(webEnvironment = RANDOM_PORT)` OR a separate config class with those annotations
- **HTTP client:** `TestRestTemplate` with `@LocalServerPort`
- **Auth:** Set `Authorization` header with `Bearer {token}` per the constitution's `api.auth` config
- **Assertions:** AssertJ — `assertThat(response.getStatusCode().value()).isEqualTo(200)`
- **Coverage:** Every `Given`, `When`, `Then` step in the `.feature` file MUST have a matching `@Given`, `@When`, `@Then` method

## Constitution Context Used

| Constitution Field | How It's Used |
|-------------------|---------------|
| `source_structure.test` | Base directory for step definition Java files |
| `source_structure.package_root` | Package declaration in step definitions |
| `api.auth.mechanism` | Determines how auth tokens are sent in steps |
| `api.auth.token_header` | Header name for auth (default: `Authorization`) |
| `api.auth.token_prefix` | Token prefix (default: `Bearer `) |
| `api.error_format` | Expected error response structure in Then steps |
| `api.base_path` | API base path for URL construction |
| `verification_standards.security_invariants` | Forbidden fields checked in invariant scenarios |

## File Output Locations

Derived from the constitution's `source_structure`:

| File | Location Pattern |
|------|-----------------|
| Feature | `{source_structure.test}/../resources/features/{jira_key}.feature` |
| Step defs | `{source_structure.test}/{package_root_as_path}/steps/{JiraKey}Steps.java` |

Example for dog-service with `DEV-17`:
- `dog-service/src/test/resources/features/DEV-17.feature`
- `dog-service/src/test/java/com/example/dogservice/steps/DEV17Steps.java`

## Validation

After generation, structural validation checks:

**Feature file:**
- Has `Feature:` declaration
- Has at least one `Scenario:`
- Has at least one `@REQ-NNN` spec ref tag

**Java step definition:**
- Has `package` declaration
- Has `import` statements
- Has `public class` declaration
- Has at least one `@Given`, `@When`, or `@Then` annotation

This is NOT compilation — just structural checks. The generated code runs through `./gradlew test` for full validation.

## Implementation

The generator is implemented in `src/verify/generators/cucumber_java.py` and registered as `cucumber_java` in the generator registry (`src/verify/generators/__init__.py`).

Called via:
```python
from verify.generators import get_generator
generator = get_generator("cucumber_java")
files = generator.generate(spec_path, constitution, llm)
generator.validate(files)
generator.write(files)
```

## Adding New Languages/Frameworks

The generator registry is pluggable. To add a new verification type:

1. Create `src/verify/generators/{name}.py`
2. Subclass `BaseGenerator` from `src/verify/generators/base.py`
3. Decorate with `@register("{generator_id}")`
4. Implement `generate()` and `validate()`
5. Create a corresponding skill in `.claude/skills/verify-{name}/SKILL.md`
