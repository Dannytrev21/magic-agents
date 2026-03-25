---
skill_id: newrelic_alert_config
name: New Relic Alert Config Generator
version: 1.0.0
description: >
  Generates NRQL alert condition JSON from performance_sla requirements.
  Proves verification goes beyond unit tests into infrastructure monitoring.
trigger_terms:
  - newrelic
  - nrql
  - alert
  - performance sla
  - monitoring
input: Compiled spec YAML with performance_sla requirements
output: NRQL alert condition JSON
---

# New Relic Alert Config Generator Skill

## Status: Planned (Epic 9 Stretch)

This skill will generate New Relic NRQL alert conditions from `performance_sla` specs.
