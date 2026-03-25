# Cucumber/Gherkin Generator Output Schema

## LLM Response Format

The Claude API call returns this JSON structure:

```json
{
  "feature_content": "string — complete .feature file content",
  "step_definition_content": "string — complete Java step definition class",
  "step_class_name": "string — Java class name (e.g., DEV17Steps)"
}
```

## Feature File Structure

```gherkin
@{JIRA_KEY} @{REQ_ID}
Feature: [REQ-001] {ac_text}
  {optional description}

  @{REQ_ID}.success
  Scenario: {happy path description}
    Given {precondition setup}
    When {action}
    Then {expected outcome}

  @{REQ_ID}.{FAIL_ID}
  Scenario: {failure mode description}
    Given {failure condition setup}
    When {action}
    Then {error response assertion}

  @{REQ_ID}.{INV_ID}
  Scenario: {invariant description}
    Given {standard setup}
    When {action}
    Then {invariant assertion}
```

## Tag-to-Spec Mapping

| Spec Element | Tag | Traced Via |
|-------------|-----|-----------|
| `requirements[].contract.success` | `@REQ-NNN.success` | `traceability.ac_mappings[].required_verifications[].ref` |
| `requirements[].contract.failures[].id` | `@REQ-NNN.FAIL-NNN` | `traceability.ac_mappings[].required_verifications[].ref` |
| `requirements[].contract.invariants[].id` | `@REQ-NNN.INV-NNN` | `traceability.ac_mappings[].required_verifications[].ref` |

## Step Definition Class Structure

```java
package {constitution.source_structure.package_root}.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import static org.assertj.core.api.Assertions.assertThat;

public class {JiraKey}Steps {

    @LocalServerPort
    private int port;

    private ResponseEntity<String> response;
    private HttpHeaders headers;

    // @Given methods — setup auth, preconditions
    // @When methods — HTTP requests
    // @Then methods — status code + body assertions
}
```

## Validation Rules

| Check | File Type | Rule |
|-------|----------|------|
| Feature declaration | `.feature` | Must contain `Feature:` |
| Scenario presence | `.feature` | Must contain at least one `Scenario:` |
| Spec ref tags | `.feature` | Must contain at least one `@REQ-\d+` pattern |
| Package declaration | `.java` | Must contain `package ` |
| Imports | `.java` | Must contain `import ` |
| Class declaration | `.java` | Must contain `public class ` |
| Step annotations | `.java` | Must contain at least one of `@Given`, `@When`, `@Then` |
