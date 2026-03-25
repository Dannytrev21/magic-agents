---
skill_id: gherkin_scenario
name: Gherkin Scenario Generator
version: 1.0.0
description: >
  Generates Gherkin .feature files from EARS statements and spec contracts.
  Produces BDD scenarios tagged with spec refs for compliance verification.
trigger_terms:
  - gherkin
  - feature file
  - bdd
  - cucumber
  - scenario
  - compliance
input: Compiled spec YAML with EARS statements and contract
output: Tagged .feature file
---

# Gherkin Scenario Generator Skill

## Status: Planned (Epic 9 Stretch)

This skill will generate Gherkin `.feature` files from EARS statements.
Currently handled by the `cucumber_java` generator in `src/verify/generators/`.
