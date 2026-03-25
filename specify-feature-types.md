# SPECify Feature Type Taxonomy
## Every Type of Story, Every Way to Prove It

**Version:** 1.0
**Last Updated:** 2026-03-24

---

## How to Read This Document

For each feature type:
- **What it covers** — the kinds of Jira stories that map to this type
- **Example ACs** — real acceptance criteria you'd see on tickets
- **Contract shape** — what the spec captures (preconditions, postconditions, invariants)
- **Verification strategies** — how you PROVE correctness (ranked by strength)
- **Negotiation focus** — what the AI asks that humans forget to specify

---

## Category A: Backend Behavior

### Type 1: `api_behavior`
**REST/GraphQL/gRPC endpoint behavior**

What it covers: New endpoints, modified responses, new parameters, content negotiation,
pagination, filtering, sorting, HATEOAS links, GraphQL resolvers, gRPC service methods.

Example ACs:
- "User can view their profile"
- "Admin can search users by email with pagination"
- "API returns 429 when rate limit exceeded"
- "GraphQL query returns nested order items"

Contract shape:
  interface: { method, path, auth, content_type }
  preconditions: [ authentication, authorization, input_validation, data_existence ]
  success: { status, schema, constraints, headers }
  failures: [ per-precondition violation with exact status + body ]
  invariants: [ security, performance, idempotency, caching ]

Verification strategies (strongest → weakest):
  1. test_result (unit/integration) — MockMvc/supertest/httpx assertions
  2. test_result (contract)        — JSON Schema validation, Pact consumer tests
  3. test_result (property-based)  — QuickCheck/jqwik with random inputs
  4. cli_exit_code (openapi-diff)  — OpenAPI spec matches implementation
  5. api_health_probe              — Live endpoint returns expected response

Negotiation focus:
  - Exact error response bodies (not just status codes)
  - Field-level constraints (response.id == jwt.sub)
  - What fields are FORBIDDEN in the response
  - Content negotiation (Accept header handling)
  - Pagination contract (cursor vs offset, max page size)


### Type 2: `data_schema`
**Database migrations, schema changes, new tables/columns, index changes**

What it covers: ALTER TABLE, CREATE TABLE, CREATE INDEX, column type changes,
constraint additions/removals, enum expansions, foreign key changes, partitioning.

Example ACs:
- "Add last_login timestamp to users table"
- "Create orders table with foreign key to users"
- "Add composite index on (status, created_at)"
- "Expand role enum to include 'MODERATOR'"

Contract shape:
  interface: { migration_tool, migration_file, target_table, operation }
  schema_change: { before_schema, after_schema, diff }
  preconditions: [ schema_version, table_exists, no_conflicting_locks ]
  postconditions: [ column_exists, type_correct, constraint_applied, default_value ]
  failures: [ version_mismatch, duplicate_column, lock_timeout, disk_space ]
  invariants: [ backwards_compatibility, rollback_exists, no_data_loss, lock_duration ]

Verification strategies:
  1. migration_test           — Run migration on test DB, query information_schema
  2. rollback_test            — Run migration then undo, verify original schema restored
  3. cli_exit_code            — flyway validate / prisma migrate diff / alembic check
  4. backwards_compat_test    — Run existing app tests against migrated schema
  5. deployment_check         — Rollback migration file exists at expected path
  6. performance_test         — Migration completes within time budget on large table

Negotiation focus:
  - Nullable vs NOT NULL (NOT NULL on existing table = table lock + backfill)
  - Default values for existing rows
  - Index strategy (will this column be queried? filtered? sorted?)
  - Backwards compatibility during rolling deployment
  - Table lock duration for large tables (online DDL?)


### Type 3: `data_operation`
**CRUD logic, complex queries, stored procedures, data transformations, repository methods**

What it covers: New repository/DAO methods, complex SQL/HQL/JPQL, aggregations,
batch updates, CTEs, window functions, stored procedures, materialized view refreshes.

Example ACs:
- "System can find all users inactive for 90 days"
- "Report shows total revenue by month for the last 12 months"
- "Bulk deactivation processes up to 10,000 users per run"
- "Search returns results ranked by relevance"

Contract shape:
  interface: { layer, class, method, returns }
  query_contract: { input_params, sql_pattern, expected_plan }
  preconditions: [ required_indexes, data_existence, parameter_constraints ]
  postconditions: [ result_filtering, result_ordering, result_count, side_effects ]
  failures: [ empty_result_behavior, timeout, connection_failure, constraint_violation ]
  invariants: [ uses_index, parameterized, read_only_or_transactional, isolation_level ]

Verification strategies:
  1. test_result (repository test) — @DataJpaTest / test containers with real DB
  2. test_result (unit test)       — Mocked repository for service-layer logic
  3. query_plan_test               — EXPLAIN ANALYZE output shows index scan
  4. test_result (property-based)  — Random inputs always produce valid results
  5. performance_test              — Query completes within budget at expected data volume

Negotiation focus:
  - Empty result behavior (empty list vs null vs exception)
  - Pagination for unbounded queries
  - N+1 query detection (eager vs lazy loading)
  - SQL injection prevention (parameterized queries)
  - Transaction boundaries and isolation level
  - Performance at expected data volume (10K rows vs 10M rows)


### Type 4: `event_consumer`
**Message queue consumers — Kafka, SQS, SNS, RabbitMQ, NATS, Redis Streams**

What it covers: New message handlers, event-driven processing, saga participants,
CQRS read-model updaters, webhook receivers, CDC consumers.

Example ACs:
- "System processes order.placed events to reserve inventory"
- "Notification service sends email when user.verified event received"
- "Read model updates when product.price.changed event arrives"

Contract shape:
  interface: { broker, topic/queue, event_type, handler, consumer_group }
  message_schema: { format, required_fields, payload_schema }
  preconditions: [ valid_message, not_duplicate, referenced_data_exists ]
  postconditions: [ side_effect_completed, message_acked, dedup_recorded ]
  failures: [ poison_message, duplicate, missing_reference, downstream_unavailable, deserialization ]
  invariants: [ idempotency, ordering, at_least_once, observability, dlq_routing ]

Verification strategies:
  1. test_result (integration)    — Embedded Kafka/LocalStack + real handler
  2. test_result (unit)           — Handler tested with mock message objects
  3. test_result (idempotency)    — Send same message twice, assert single effect
  4. test_result (poison pill)    — Send malformed message, assert DLQ routing
  5. config_validation            — Consumer group config, DLQ config, partition key
  6. deployment_check             — DLQ topic/queue exists
  7. test_result (ordering)       — Send ordered messages, verify processing order

Negotiation focus:
  - Idempotency strategy (event_id dedup table? natural idempotency?)
  - DLQ routing rules (which failures go to DLQ vs retry?)
  - Retry policy (exponential backoff? max retries? retry topic?)
  - Ordering guarantees (partition key? single consumer?)
  - Schema evolution (what if producer adds/removes fields?)
  - Poison message handling (malformed JSON, unknown event type)
  - Commit strategy (auto-commit vs manual ack)


### Type 5: `event_producer`
**Publishing events/messages to queues, topics, or event buses**

What it covers: Domain event emission, change data capture setup, outbox pattern
implementation, webhook firing, notification dispatching.

Example ACs:
- "System publishes order.confirmed event after payment succeeds"
- "Profile update triggers user.profile.updated event"
- "All state changes emit audit events to the audit topic"

Contract shape:
  interface: { broker, topic/queue, event_type, trigger_condition }
  message_schema: { format, required_fields, payload }
  preconditions: [ trigger_operation_succeeded ]
  postconditions: [ event_published, schema_valid, correct_partition_key, correct_headers ]
  failures: [ broker_unavailable, serialization_error ]
  invariants: [ atomicity_with_db, schema_backwards_compatible, exactly_once_semantics ]

Verification strategies:
  1. test_result (integration)    — Embedded broker, capture published message, assert schema
  2. test_result (unit)           — Verify event construction logic
  3. test_result (outbox)         — Verify outbox record created in same transaction
  4. cli_exit_code                — Schema registry compatibility check
  5. config_validation            — Topic exists, partition count, replication factor
  6. deployment_check             — Outbox poller/CDC connector configured

Negotiation focus:
  - Atomicity: Is event publication in the same transaction as the DB write?
    (If not, you can lose events on crash — need outbox pattern or CDC)
  - Schema evolution: Can you add fields without breaking consumers?
  - Partition key: What determines message ordering?
  - Event granularity: One event per field change or one per operation?
  - Sensitive data: Does the event contain PII? Should it be encrypted in transit?


### Type 6: `scheduled_job`
**Cron jobs, batch processing, scheduled reports, cleanup tasks, data syncs**

What it covers: @Scheduled methods, Quartz jobs, AWS EventBridge rules, CloudWatch
scheduled events, data retention cleanup, report generation, cache warming.

Example ACs:
- "System deactivates users inactive for 90 days, nightly"
- "Daily report of failed transactions emailed to finance team"
- "Expired sessions cleaned up every 15 minutes"
- "Data warehouse sync runs hourly with incremental updates"

Contract shape:
  interface: { scheduler, schedule_expression, job_class, description }
  preconditions: [ not_already_running, database_available, not_maintenance_window ]
  postconditions: [ data_state_after, notifications_sent, metrics_recorded, lock_released ]
  failures: [ lock_contention, timeout, partial_completion, downstream_unavailable ]
  invariants: [ idempotency, mutual_exclusion, blast_radius, checkpointing, observability ]

Verification strategies:
  1. test_result (unit)           — Job logic tested with controlled time/data
  2. test_result (integration)    — Full job run against test DB
  3. test_result (idempotency)    — Run twice, assert same final state
  4. test_result (blast_radius)   — Assert max rows affected per run
  5. config_validation            — ShedLock/distributed lock config exists
  6. deployment_check             — Schedule expression valid, monitoring configured
  7. test_result (checkpoint)     — Kill mid-run, restart, assert correct resumption

Negotiation focus:
  - Mutual exclusion: What prevents two instances from running simultaneously?
  - Blast radius: Is there a max rows-affected limit per run?
  - Checkpointing: If it crashes mid-batch, does it resume or restart?
  - Idempotency: Running twice produces same result?
  - Timeout: What if it takes longer than the interval between runs?
  - Monitoring: How do you know if it silently stops running?
  - Data window: What's the lookback period? Can it miss data?


### Type 7: `external_integration`
**Calling third-party APIs, partner services, cloud provider APIs**

What it covers: Stripe charges, SendGrid emails, Twilio SMS, Google Maps geocoding,
AWS S3 uploads, OAuth token exchanges, partner API calls.

Example ACs:
- "System charges customer via Stripe when order is confirmed"
- "Verification email sent via SendGrid on registration"
- "Profile photo uploaded to S3 with CDN URL returned"
- "Address validated via Google Maps Geocoding API"

Contract shape:
  interface: { provider, operation, endpoint, client_class, client_method }
  request_contract: { params, headers, auth }
  response_contract: { success_shape, error_codes }
  preconditions: [ valid_params, api_key_configured, within_rate_limit ]
  postconditions: [ response_parsed, our_state_updated, receipt_recorded ]
  failures: [ timeout, rate_limit, auth_failure, provider_error, network_failure ]
  invariants: [ idempotency_key, no_secret_leakage, timeout_configured, circuit_breaker, tracing ]

Verification strategies:
  1. test_result (unit + mock)    — WireMock/nock/responses mocking provider responses
  2. test_result (contract)       — Validate our request matches provider's OpenAPI spec
  3. test_result (resilience)     — Simulate timeout, 429, 500 and verify our behavior
  4. test_result (circuit_breaker)— Trigger threshold, verify circuit opens
  5. config_validation            — Timeout configured, retry policy configured
  6. deployment_check             — API key exists in secrets manager (not value, just existence)
  7. api_health_probe             — Provider health endpoint responds (smoke test)

Negotiation focus:
  - Idempotency: If we retry, will the provider charge twice? (Idempotency key?)
  - Timeout: What's the max wait? What happens on timeout — retry or fail?
  - Circuit breaker: After N failures, do we stop calling and degrade gracefully?
  - Secret management: Where is the API key stored? (Never in code, env vars, or logs)
  - Cost: Does each call cost money? Should we cache results?
  - Rate limits: What's the provider's limit? Do we self-throttle below it?
  - Fallback: If provider is down, is there a degraded experience?
  - Sandbox: Are we testing against production or sandbox?


### Type 8: `state_transition`
**Business workflow state machines, approval flows, lifecycle management**

What it covers: Order lifecycle, user verification flow, document approval process,
payment state machine, subscription lifecycle, dispute resolution flow.

Example ACs:
- "Order moves from PENDING to CONFIRMED when payment succeeds"
- "User account transitions to ACTIVE after email verification"
- "Refund request requires manager approval before processing"
- "Subscription cancellation takes effect at end of billing period"

Contract shape:
  interface: { entity, transition, trigger, handler }
  state_machine: { all_valid_transitions, terminal_states }
  preconditions: [ current_state, trigger_condition, authorization ]
  postconditions: [ new_state, timestamp_set, event_published, side_effects ]
  failures: [ invalid_transition, concurrent_modification, trigger_condition_unmet ]
  invariants: [ only_valid_transitions, atomicity, audit_trail, optimistic_locking ]

Verification strategies:
  1. test_result (unit)           — Each valid transition tested
  2. test_result (negative)       — Each INVALID transition tested (must throw)
  3. test_result (full_lifecycle) — Walk through complete happy path lifecycle
  4. test_result (concurrency)    — Two threads race, exactly one wins
  5. test_result (event)          — State change emits correct domain event
  6. test_result (audit)          — History table records actor, timestamp, reason
  7. deployment_check             — State machine diagram matches code

Negotiation focus:
  - Complete state machine: Draw ALL states and ALL valid transitions
  - Invalid transitions: What happens when you try DELIVERED → PENDING?
  - Concurrent transitions: Two requests try to cancel the same order simultaneously
  - Compensation: If side effect fails after state change, do you roll back?
  - Time-based transitions: Can states expire? (pending → cancelled after 24h)
  - Authorization per transition: Can anyone cancel, or only the creator?


---

## Category B: Observability & Monitoring

### Type 9: `alerting_rule`
**APM alert conditions, PagerDuty rules, threshold-based alerts**

What it covers: New Relic NRQL alerts, Datadog monitors, CloudWatch alarms,
Prometheus alerting rules, PagerDuty escalation policies, Slack notifications.

Example ACs:
- "Alert fires when p99 latency exceeds 500ms for 5 minutes"
- "PagerDuty page when error rate exceeds 5% for 3 minutes"
- "Slack notification when disk usage exceeds 80%"
- "Alert when no orders received in 30-minute window (dead man's switch)"

Contract shape:
  interface: { provider, alert_type, target_metric }
  condition:
    query: "NRQL / PromQL / Datadog query string"
    threshold: { value, duration, comparison_operator }
    severity: critical | warning | info
  notification:
    channels: [ pagerduty, slack, email ]
    escalation_policy: "P1 → on-call, P2 → team channel"
  preconditions: [ metric_exists, data_flowing ]
  postconditions: [ alert_fires_when_threshold_breached, notification_sent ]
  invariants: [ no_alert_fatigue, actionable, has_runbook_link ]

Verification strategies:
  1. deployment_check             — Alert config file exists and is valid
  2. config_validation            — NRQL/PromQL query is syntactically valid
  3. schema_validation            — Config matches provider's alert schema
  4. simulation_test              — Inject synthetic data that triggers threshold, verify alert fires
  5. deployment_check             — Runbook document exists at linked URL
  6. integration_test             — Alert webhook reaches notification channel (staging)

Negotiation focus:
  - Threshold tuning: What's normal baseline? How did you pick 500ms?
  - Duration window: Spike for 1 second vs sustained for 5 minutes
  - Alert fatigue: Will this fire constantly in non-prod environments?
  - Runbook: What should the on-call engineer DO when this fires?
  - Auto-resolution: Does the alert auto-close when metric recovers?
  - Muting: Should it be muted during deployments?


### Type 10: `structured_logging`
**Log format requirements, audit logging, compliance logging**

What it covers: Adding structured log fields, audit trail logging, PII access logging,
log level changes, correlation ID propagation, log-based metrics.

Example ACs:
- "All profile access logged with user_id, timestamp, source_ip"
- "Failed login attempts logged with attempt count and lockout status"
- "All PII field access logged for GDPR compliance"
- "Request correlation ID propagated through all log entries"

Contract shape:
  interface: { logger, log_level, trigger_event, format }
  log_entry_schema:
    required_fields: [ timestamp, level, correlation_id, service, message ]
    context_fields: [ user_id, action, source_ip, response_status ]
    forbidden_fields: [ password, ssn, credit_card, full_request_body ]
  preconditions: [ event_occurred, logging_framework_configured ]
  postconditions: [ log_entry_emitted, all_required_fields_present ]
  invariants: [ no_pii_in_logs, structured_format, correlation_propagated ]

Verification strategies:
  1. test_result (unit)           — Capture log output, parse JSON, assert fields present
  2. test_result (negative)       — Trigger event, assert PII fields NOT in log
  3. config_validation            — Logback/log4j config has structured JSON appender
  4. test_result (correlation)    — Make request, assert correlation_id in all log entries
  5. cli_exit_code                — Log format linter (custom script or grok pattern test)
  6. deployment_check             — Log shipping config (Fluentd/Filebeat) exists

Negotiation focus:
  - What fields are REQUIRED in every log entry for this event?
  - What fields are FORBIDDEN? (passwords, tokens, PII that shouldn't be logged)
  - What log level? (INFO for success, WARN for client error, ERROR for server error?)
  - Correlation ID: Is it propagated from the incoming request header?
  - Log volume: Will this create excessive log volume? (Every request vs sampled?)
  - Retention: How long must these logs be retained? (Compliance requirement?)


### Type 11: `metric_emission`
**Custom application metrics, Prometheus counters/gauges/histograms, StatsD**

What it covers: New counters, gauges, histograms, timers, business metrics,
SLI definitions, error budget tracking.

Example ACs:
- "Track request duration histogram per endpoint"
- "Count failed payment attempts by failure reason"
- "Gauge current active WebSocket connections"
- "Business metric: orders_placed_total by region and product_category"

Contract shape:
  interface: { metrics_library, metric_type, metric_name }
  metric_definition:
    name: "http_request_duration_seconds"
    type: histogram | counter | gauge | summary
    labels: [ method, path, status_code ]
    buckets: [ 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0 ]  # for histograms
  preconditions: [ event_occurs ]
  postconditions: [ metric_recorded_with_correct_labels ]
  invariants: [ cardinality_bounded, naming_convention, no_pii_in_labels ]

Verification strategies:
  1. test_result (unit)           — Trigger event, scrape /metrics endpoint, assert metric exists
  2. test_result (label_check)    — Assert labels match expected values
  3. config_validation            — Micrometer/Prometheus config includes metric registration
  4. test_result (cardinality)    — Assert label cardinality stays within bounds
  5. deployment_check             — Grafana dashboard JSON references this metric
  6. api_health_probe             — /metrics endpoint includes the new metric name

Negotiation focus:
  - Metric type: Counter (monotonically increasing) vs gauge (goes up and down)?
  - Labels: What dimensions? (Be careful — high cardinality labels kill Prometheus)
  - Naming convention: Does it follow your org's metric naming standard?
  - Where recorded: In the handler? In middleware? In an interceptor?
  - Dashboard: Does a Grafana dashboard need updating to show this metric?
  - Alert: Should this metric trigger an alert at some threshold?


### Type 12: `distributed_tracing`
**OpenTelemetry spans, trace context propagation, span attributes**

What it covers: Adding OTel spans, propagating trace context across services,
adding span attributes, custom span events, trace-based sampling rules.

Example ACs:
- "Profile retrieval creates a span with user_id attribute"
- "External API call to Stripe creates a child span with duration"
- "Trace context propagated from API gateway through all downstream services"
- "Database queries appear as child spans with SQL statement"

Contract shape:
  interface: { tracing_library, span_name, span_kind }
  span_definition:
    name: "UserController.getUserProfile"
    kind: SERVER | CLIENT | INTERNAL | PRODUCER | CONSUMER
    attributes:
      required: [ user_id, http.method, http.route ]
      optional: [ http.status_code, db.statement ]
      forbidden: [ password, api_key, bearer_token ]
  preconditions: [ trace_context_exists_in_request ]
  postconditions: [ span_created, attributes_set, context_propagated_to_children ]
  invariants: [ no_sensitive_data_in_attributes, context_propagated, sampling_rate_respected ]

Verification strategies:
  1. test_result (unit)           — InMemorySpanExporter, assert span created with attributes
  2. config_validation            — OTel config has required instrumentation
  3. test_result (propagation)    — Multi-service test, assert same trace_id across services
  4. test_result (negative)       — Assert forbidden attributes never appear
  5. deployment_check             — OTel collector config routes to correct backend

Negotiation focus:
  - What attributes go on the span? (user_id yes, but NOT the JWT itself)
  - Span kind: Is this the server receiving a request or a client making one?
  - Context propagation: Does trace context flow to downstream HTTP calls? Kafka messages?
  - Sampling: 100% of traces or sampled? (Cost implications)
  - Sensitive data: OTel attributes end up in your tracing backend — no secrets


### Type 13: `health_endpoint`
**Readiness probes, liveness probes, health checks, dependency checks**

What it covers: Kubernetes readiness/liveness probes, Spring Actuator health,
custom health checks for databases/caches/queues, startup probes.

Example ACs:
- "Health endpoint checks database connectivity"
- "Readiness probe returns 503 when Kafka consumer is lagging > 1000"
- "Liveness probe returns 200 even if non-critical dependencies are down"
- "Health endpoint includes version, uptime, and dependency statuses"

Contract shape:
  interface: { path, probe_type, response_format }
  checks:
    - { name: database, critical: true, timeout_ms: 3000 }
    - { name: redis, critical: false, timeout_ms: 1000 }
    - { name: kafka, critical: true, check: "consumer_lag < 1000" }
  preconditions: [ endpoint_accessible ]
  postconditions: [ status_reflects_dependency_health, response_within_timeout ]
  failures:
    - { dependency_down: database, probe_response: 503 }
    - { dependency_down: redis, probe_response: 200, degraded: true }
  invariants: [ probe_fast_enough_for_k8s, no_auth_required, no_sensitive_info ]

Verification strategies:
  1. test_result (integration)    — Start app, hit /health, assert structure
  2. test_result (dependency_down)— Kill DB, hit /health, assert 503
  3. test_result (degraded)       — Kill Redis, hit /health, assert 200 + degraded flag
  4. api_health_probe             — Live /health returns 200
  5. config_validation            — K8s deployment YAML has correct probe config

Negotiation focus:
  - Critical vs non-critical dependencies: Which failures should make the probe fail?
  - Timeout: K8s kills pods if liveness probe takes too long (default 1s)
  - Authentication: Health endpoints should NOT require auth (K8s can't provide it)
  - Information exposure: Don't leak internal service names or versions to unauthenticated callers
  - Startup probe: Does the app need time to warm up before readiness checks begin?


### Type 14: `dashboard`
**Grafana dashboards, New Relic dashboards, monitoring visualizations**

What it covers: New dashboard panels, modified queries, threshold lines,
SLO burn rate displays, business KPI dashboards.

Example ACs:
- "Dashboard shows p50/p95/p99 latency for all API endpoints"
- "Error rate panel with threshold line at 1% SLO"
- "Business dashboard shows orders per hour by region"

Contract shape:
  interface: { provider, dashboard_name, panel_definitions }
  panels:
    - { title, query, visualization_type, thresholds }
  preconditions: [ metrics_exist, data_source_configured ]
  postconditions: [ dashboard_exists, panels_render_data ]
  invariants: [ queries_use_correct_metric_names, time_range_appropriate ]

Verification strategies:
  1. deployment_check             — Dashboard JSON file exists and is valid
  2. schema_validation            — Dashboard JSON matches Grafana schema
  3. config_validation            — All metric names in queries actually exist
  4. manual_gate                  — Visual review of dashboard layout

Negotiation focus:
  - What metrics does each panel query?
  - What time ranges? (Last 1h for real-time, last 30d for trends)
  - What thresholds/SLO lines should be visible?
  - Who is the audience? (Engineers vs product vs executives)


---

## Category C: Security & Compliance

### Type 15: `authentication`
**Auth mechanism changes, SSO integration, token handling, session management**

What it covers: JWT validation rules, OAuth2 flow implementation, SAML integration,
MFA enforcement, session timeout rules, token refresh logic.

Example ACs:
- "System validates JWT signature using RS256"
- "Refresh token rotation on every use"
- "Session expires after 30 minutes of inactivity"
- "MFA required for admin role users"

Contract shape:
  interface: { auth_mechanism, endpoint_or_filter, scope }
  token_contract:
    algorithm: RS256
    required_claims: [ sub, exp, iat, iss, aud ]
    issuer: "https://auth.example.com"
    audience: "user-service"
    max_lifetime: 3600
  preconditions: [ key_material_available, issuer_reachable ]
  postconditions: [ valid_token_accepted, invalid_token_rejected, claims_extracted ]
  failures: [ expired, wrong_issuer, wrong_audience, invalid_signature, missing_claims ]
  invariants: [ timing_safe_comparison, no_algorithm_confusion, key_rotation_supported ]

Verification strategies:
  1. test_result (unit)           — Test each validation rule with crafted tokens
  2. test_result (negative)       — Expired, malformed, wrong-alg tokens rejected
  3. test_result (security)       — Algorithm confusion attack (none alg) rejected
  4. config_validation            — JWKS endpoint configured, key rotation interval
  5. cli_exit_code                — Security scanner (OWASP ZAP auth test)
  6. penetration_test             — Attempt token forgery, session fixation

Negotiation focus:
  - Algorithm: RS256 vs HS256? (HS256 with shared secret is weaker)
  - Token lifetime: Short (minutes) vs long (hours)? Refresh strategy?
  - Revocation: Can tokens be revoked before expiry? (Blocklist? Short-lived tokens?)
  - Algorithm confusion: Does validation enforce expected algorithm?
  - Clock skew: How much clock drift tolerance for exp/iat?


### Type 16: `authorization`
**RBAC rules, permission checks, resource-level access control, scopes**

What it covers: Role assignments, permission matrices, resource ownership checks,
scope-based access, attribute-based access control (ABAC), tenant isolation.

Example ACs:
- "Only users with ADMIN role can access /api/v1/admin/*"
- "Users can only modify their own profile"
- "MANAGER role can view reports for their department only"
- "API scopes enforce read vs write access"

Contract shape:
  interface: { mechanism, enforcement_point }
  permission_matrix:
    - { role: USER, resource: /api/v1/users/me, actions: [GET, PUT] }
    - { role: ADMIN, resource: /api/v1/admin/*, actions: [GET, POST, PUT, DELETE] }
    - { role: MANAGER, resource: /api/v1/reports, actions: [GET], constraint: "department == user.department" }
  preconditions: [ user_authenticated, role_assigned ]
  postconditions: [ authorized_access_granted, unauthorized_access_denied ]
  failures: [ missing_role, wrong_scope, cross_tenant, cross_department ]
  invariants: [ deny_by_default, no_privilege_escalation, audit_logged ]

Verification strategies:
  1. test_result (matrix test)    — Test every role × resource × action combination
  2. test_result (negative)       — Verify each unauthorized combination returns 403
  3. test_result (escalation)     — Verify user cannot grant themselves higher role
  4. test_result (cross-tenant)   — Verify tenant A cannot access tenant B's resources
  5. cli_exit_code                — RBAC policy linter / OPA policy test
  6. deployment_check             — Permission config matches expected matrix

Negotiation focus:
  - Default deny: Is everything blocked unless explicitly allowed?
  - Privilege escalation: Can a user change their own role?
  - Resource ownership: How is "my resource" determined? (creator? assignee? department?)
  - Tenant isolation: In multi-tenant systems, is tenant ID enforced at the query level?
  - Audit: Are authorization decisions logged? (Both grants and denials?)


### Type 17: `encryption`
**Data encryption at rest, in transit, field-level encryption, key management**

What it covers: Column-level encryption, TLS configuration, KMS integration,
envelope encryption, PII field encryption, certificate rotation.

Example ACs:
- "SSN field encrypted at rest using AES-256"
- "All API traffic uses TLS 1.2 or higher"
- "Encryption keys rotated every 90 days without downtime"
- "PII fields encrypted before writing to database"

Contract shape:
  interface: { encryption_type, algorithm, key_management }
  encrypted_fields: [ { field, algorithm, key_ref } ]
  preconditions: [ key_available, key_not_expired ]
  postconditions: [ data_encrypted_at_rest, data_decryptable_by_authorized_service ]
  invariants: [ key_never_in_code, key_rotation_works, old_data_still_decryptable ]

Verification strategies:
  1. test_result (unit)           — Encrypt then decrypt, verify round-trip
  2. test_result (at_rest)        — Read raw DB column, verify it's not plaintext
  3. test_result (key_rotation)   — Rotate key, verify old data still decryptable
  4. config_validation            — KMS key ARN configured, rotation enabled
  5. cli_exit_code                — TLS scanner (testssl.sh, sslyze)
  6. deployment_check             — TLS cert not expiring within 30 days

Negotiation focus:
  - Which specific fields need encryption? (Not "all PII" — be specific)
  - Searchability: Can you search encrypted fields? (Need deterministic encryption or search index)
  - Key rotation: What happens to data encrypted with old key?
  - Performance: Encryption adds latency — is that acceptable?
  - Key management: AWS KMS? HashiCorp Vault? Application-level?


### Type 18: `data_privacy`
**GDPR compliance, data retention, right to erasure, consent management, data classification**

What it covers: PII inventory, data retention policies, erasure workflows,
consent records, data processing agreements, privacy impact assessments.

Example ACs:
- "User can request deletion of all their personal data"
- "Inactive user data purged after 2 years"
- "All API responses containing PII include X-Data-Classification header"
- "Consent preferences recorded and enforced for marketing communications"

Contract shape:
  interface: { regulation, data_subject_right, implementation }
  pii_inventory:
    - { field: email, classification: PII-STANDARD, retention: "account lifetime + 30 days" }
    - { field: ssn, classification: PII-SENSITIVE, retention: "required by law" }
  erasure_scope: [ user_table, order_history, audit_logs_anonymized, analytics_anonymized ]
  preconditions: [ identity_verified, request_authenticated ]
  postconditions: [ data_deleted_or_anonymized, confirmation_sent, erasure_logged ]
  invariants: [ no_pii_leakage_post_erasure, audit_logs_retained_anonymized, backup_purge_scheduled ]

Verification strategies:
  1. test_result (erasure)        — Request deletion, verify all tables purged
  2. test_result (anonymization)  — Verify anonymized records can't be re-identified
  3. test_result (header_check)   — Assert X-Data-Classification on PII responses
  4. test_result (retention)      — Verify aged-out data is actually deleted
  5. deployment_check             — Privacy policy document exists and is current
  6. config_validation            — Retention job schedule matches policy

Negotiation focus:
  - Erasure scope: What about backups? Event logs? Analytics? Third-party systems?
  - Anonymization vs deletion: Can you anonymize instead of delete for analytics?
  - Right to portability: Can users export their data? What format?
  - Consent granularity: Per-purpose consent or blanket consent?
  - Data processor agreements: Do you share data with third parties?


### Type 19: `vulnerability_remediation`
**CVE fixes, dependency updates, security patch application**

What it covers: Upgrading vulnerable dependencies, patching known CVEs,
addressing SAST/DAST findings, fixing penetration test findings.

Example ACs:
- "Upgrade log4j to 2.17.1 to remediate CVE-2021-44228"
- "Fix SQL injection in search endpoint (pentest finding PT-042)"
- "Remove hardcoded credentials from configuration files"
- "Upgrade Spring Boot to 3.2.1 to address CVE-2023-xxxxx"

Contract shape:
  interface: { cve_id, affected_component, remediation_action }
  preconditions: [ vulnerability_exists, fix_available ]
  postconditions: [ vulnerability_no_longer_present, existing_tests_still_pass ]
  invariants: [ no_regression, no_new_vulnerabilities_introduced ]

Verification strategies:
  1. cli_exit_code (dependency scan) — npm audit / OWASP dependency-check / Snyk
  2. cli_exit_code (SAST)            — SonarQube / Semgrep / CodeQL scan passes
  3. cli_exit_code (secret scan)     — gitleaks / truffleHog / detect-secrets
  4. test_result (regression)        — All existing tests still pass
  5. test_result (exploit_test)      — Specific test that exploited the vuln now fails
  6. penetration_test                — Re-test original finding, verify fixed

Negotiation focus:
  - Blast radius: What else does this dependency upgrade affect?
  - Regression risk: Does the fix change any behavior?
  - Verification: Can we write a test that would have caught this?
  - Disclosure: Is this CVE publicly known? Time pressure?


---

## Category D: Infrastructure & Deployment

### Type 20: `infrastructure_config`
**Terraform/CloudFormation changes, K8s manifests, Docker configuration**

What it covers: New cloud resources, modified resource configurations, scaling
policies, network rules, IAM policies, container definitions.

Example ACs:
- "Service scales to 10 replicas under load"
- "RDS instance uses encrypted storage with automated backups"
- "Container runs as non-root user"
- "VPC security group allows traffic only from load balancer"

Contract shape:
  interface: { iac_tool, resource_type, change_description }
  resource_spec:
    type: "aws_rds_instance"
    properties:
      encrypted: true
      backup_retention: 7
      multi_az: true
  preconditions: [ permissions_exist, budget_approved ]
  postconditions: [ resource_created_with_spec, accessible_by_application ]
  invariants: [ least_privilege, encrypted_by_default, tagged_with_cost_center ]

Verification strategies:
  1. cli_exit_code (plan)         — terraform plan / cdk diff shows expected changes
  2. cli_exit_code (lint)         — tflint / cfn-lint / kubeval passes
  3. cli_exit_code (security)     — checkov / tfsec / kube-score scan passes
  4. config_validation            — Resource has required tags, encryption, logging
  5. deployment_check             — Terraform state shows resource exists
  6. api_health_probe             — Resource is accessible after deployment

Negotiation focus:
  - Least privilege: Does the IAM policy grant only what's needed?
  - Cost: What's the estimated monthly cost of this resource?
  - Disaster recovery: Is this resource backed up? Multi-AZ? Cross-region?
  - Tagging: Does it have required cost-center, team, environment tags?
  - Security: Is encryption enabled? Is it in a private subnet?


### Type 21: `ci_cd_pipeline`
**Pipeline changes, build steps, deployment stages, quality gates**

What it covers: New GitHub Actions workflows, Jenkins pipeline changes,
deployment strategies (blue-green, canary), quality gate additions.

Example ACs:
- "PR builds must pass unit tests, SAST scan, and dependency audit"
- "Deployment uses blue-green strategy with automatic rollback"
- "Canary deployment rolls out to 5% of traffic before full release"
- "Build fails if test coverage drops below 80%"

Contract shape:
  interface: { ci_tool, pipeline_name, trigger }
  stages: [ { name, steps, quality_gates, failure_behavior } ]
  preconditions: [ code_pushed, branch_matches_pattern ]
  postconditions: [ artifact_built, tests_passed, deployed_successfully ]
  invariants: [ no_deploy_without_tests, rollback_tested, secrets_not_in_logs ]

Verification strategies:
  1. deployment_check             — Pipeline YAML file exists with required stages
  2. config_validation            — Quality gates defined (coverage, SAST, etc.)
  3. test_result (pipeline_test)  — Trigger pipeline on test repo, verify stages execute
  4. cli_exit_code                — Pipeline linter (actionlint for GitHub Actions)
  5. manual_gate                  — Pipeline run reviewed by team lead

Negotiation focus:
  - What quality gates are required before deployment?
  - Rollback strategy: Automatic on failure? Manual approval?
  - Secrets handling: How are deployment credentials managed?
  - Parallel stages: What can run concurrently?
  - Caching: Are build dependencies cached between runs?


### Type 22: `feature_flag`
**Feature toggle configuration, gradual rollouts, A/B testing setup**

What it covers: LaunchDarkly/Unleash/Split flag creation, rollout percentages,
user targeting rules, flag cleanup, kill switches.

Example ACs:
- "New checkout flow behind feature flag, enabled for 10% of users"
- "Kill switch to disable payment processing in emergency"
- "Feature available only to users in US and UK"
- "Flag cleaned up after feature fully rolled out"

Contract shape:
  interface: { flag_provider, flag_key, flag_type }
  flag_definition:
    key: "new-checkout-flow"
    type: boolean | multivariate
    default: false
    targeting:
      - { segment: "beta-users", value: true }
      - { segment: "us-uk-users", percentage: 10 }
  preconditions: [ flag_exists_in_provider, sdk_initialized ]
  postconditions: [ flag_evaluated_correctly, fallback_works_when_provider_down ]
  invariants: [ graceful_degradation_without_flag_service, no_stale_flags ]

Verification strategies:
  1. test_result (unit)           — Test both flag states (on/off) in code paths
  2. test_result (fallback)       — Mock flag service unavailable, verify default behavior
  3. config_validation            — Flag exists in provider with correct targeting
  4. deployment_check             — Flag key matches code references
  5. test_result (stale_flag)     — Assert flag has evaluation count > 0 in last 30 days

Negotiation focus:
  - Default value: What happens if the flag service is unreachable?
  - Targeting: Who sees it first? (Internal → beta → percentage → everyone)
  - Cleanup: When will the flag be removed? (Stale flags are tech debt)
  - Testing: Are both paths tested? (Most bugs hide in the disabled path)
  - Kill switch: Is there a way to instantly disable the feature?


### Type 23: `container_security`
**Docker image hardening, runtime security, supply chain security**

What it covers: Distroless images, non-root users, read-only filesystems,
image scanning, SBOM generation, signed images.

Example ACs:
- "Container runs as non-root user (UID 1000)"
- "No critical or high CVEs in container image"
- "Read-only root filesystem with writable /tmp only"
- "Image signed and SBOM published to registry"

Contract shape:
  interface: { container_runtime, image_name }
  security_posture:
    user: non-root
    uid: 1000
    read_only_rootfs: true
    writable_mounts: [ /tmp, /var/log ]
    capabilities_dropped: [ ALL ]
    capabilities_added: [ NET_BIND_SERVICE ]  # only if needed
  preconditions: [ base_image_exists ]
  postconditions: [ image_built, security_scan_passes, sbom_generated ]
  invariants: [ no_root, no_critical_cves, minimal_attack_surface ]

Verification strategies:
  1. cli_exit_code (image_scan)   — Trivy / Grype / Snyk container scan
  2. cli_exit_code (dockerfile)   — hadolint Dockerfile linting
  3. test_result (runtime)        — Start container, verify UID, verify read-only fs
  4. deployment_check             — SBOM artifact exists in registry
  5. config_validation            — K8s securityContext matches requirements

Negotiation focus:
  - Base image: distroless vs alpine vs debian-slim? (Attack surface tradeoff)
  - Non-root: Does the app actually work as non-root? (Port binding below 1024?)
  - Read-only: What needs to be writable? (temp files, logs, caches)
  - Supply chain: Is the base image from a trusted registry?


---

## Category E: Performance & Reliability

### Type 24: `performance_sla`
**Latency targets, throughput requirements, resource limits**

What it covers: p50/p95/p99 latency targets, requests-per-second requirements,
memory/CPU limits, connection pool sizing, query performance.

Example ACs:
- "API responds within 200ms at p95 under 1000 RPS"
- "Service uses no more than 512MB memory"
- "Database connection pool sized for 50 concurrent connections"

Contract shape:
  interface: { target, metric, threshold }
  sla:
    latency: { p50: 50ms, p95: 200ms, p99: 500ms }
    throughput: { target_rps: 1000 }
    resources: { max_memory: 512MB, max_cpu: 1.0 }
  preconditions: [ service_running, under_load ]
  postconditions: [ metrics_within_thresholds ]
  invariants: [ no_memory_leak, no_thread_leak, graceful_under_pressure ]

Verification strategies:
  1. test_result (load_test)      — k6/Gatling/Locust test against staging
  2. deployment_check             — NR/DD alert configured for SLA breach
  3. config_validation            — Resource limits set in K8s manifest
  4. config_validation            — Connection pool sized in application config
  5. test_result (stress_test)    — 2x expected load, verify graceful degradation
  6. metric_query                 — Live p99 from APM within threshold

Negotiation focus:
  - Percentile: p95 vs p99? (p99 is much harder to meet)
  - Load profile: Steady state vs bursty? What's the peak?
  - Resources: CPU and memory limits in K8s?
  - Connection pools: DB, HTTP client, Redis — all need sizing
  - Warm-up: Is cold start latency acceptable? (JVM warm-up, cache miss)


### Type 25: `caching`
**Cache implementation, invalidation strategy, TTL configuration**

What it covers: Redis/Memcached caching, HTTP caching headers, CDN caching,
local in-memory caching, cache warming, cache stampede prevention.

Example ACs:
- "User profile cached in Redis with 5-minute TTL"
- "Cache invalidated on profile update"
- "API returns Cache-Control headers for static resources"
- "Cache miss falls through to database transparently"

Contract shape:
  interface: { cache_provider, cache_key_pattern, ttl }
  cache_strategy:
    pattern: cache_aside | read_through | write_through | write_behind
    key: "user:profile:{user_id}"
    ttl: 300  # seconds
    invalidation_triggers: [ "profile.updated", "profile.deleted" ]
  preconditions: [ cache_available ]
  postconditions: [ cache_hit_returns_data, cache_miss_populates_cache ]
  failures: [ cache_unavailable_fallback, stale_data_served, stampede_on_expiry ]
  invariants: [ cache_consistent_with_source, no_stale_data_after_update, degraded_without_cache ]

Verification strategies:
  1. test_result (unit)           — Cache hit returns cached data
  2. test_result (miss)           — Cache miss queries DB and populates cache
  3. test_result (invalidation)   — Update triggers cache eviction
  4. test_result (fallback)       — Redis down → falls through to DB (no error)
  5. test_result (stampede)       — Concurrent misses don't all hit DB
  6. config_validation            — Redis/Memcached TTL config matches spec

Negotiation focus:
  - Invalidation: How is the cache invalidated? (Event-driven? TTL-only? Manual?)
  - Consistency: Is slightly stale data acceptable? For how long?
  - Cache-aside vs read-through: Who manages the cache? (App vs framework?)
  - Stampede: What prevents 1000 concurrent cache misses from hitting the DB?
  - Fallback: If cache service is down, does the app still work?
  - Serialization: What format in cache? (JSON, protobuf, Java serialization?)


### Type 26: `rate_limiting`
**Request throttling, quota enforcement, abuse prevention**

What it covers: Per-user rate limits, per-IP limits, API key quotas,
sliding window vs fixed window, rate limit headers, burst allowance.

Example ACs:
- "API limits to 100 requests per minute per user"
- "Rate limit headers returned on every response"
- "Burst of 20 requests allowed before throttling"
- "Admin endpoints have separate higher limit"

Contract shape:
  interface: { mechanism, scope, limit }
  rate_limit:
    algorithm: sliding_window | fixed_window | token_bucket | leaky_bucket
    default: { requests: 100, window: 60s }
    burst: 20
    scopes:
      - { pattern: "/api/v1/admin/*", limit: 500, window: 60s }
      - { pattern: "/api/v1/auth/login", limit: 10, window: 60s }
    headers:
      X-RateLimit-Limit: "100"
      X-RateLimit-Remaining: "73"
      X-RateLimit-Reset: "1616364000"
  preconditions: [ rate_limit_store_available ]
  postconditions: [ under_limit_allowed, over_limit_returns_429 ]
  failures: [ rate_limit_store_unavailable ]
  invariants: [ fail_open_or_closed, headers_always_present, no_bypass_without_auth ]

Verification strategies:
  1. test_result (unit)           — Send N+1 requests, assert 429 on N+1
  2. test_result (headers)        — Assert rate limit headers on every response
  3. test_result (burst)          — Send burst, verify allowed then throttled
  4. test_result (scope)          — Verify different endpoints have different limits
  5. test_result (failover)       — Redis down → verify fail-open or fail-closed behavior
  6. config_validation            — Rate limit config matches spec

Negotiation focus:
  - Algorithm: Sliding window (smooth) vs token bucket (allows bursts)?
  - Fail behavior: If Redis is down, allow all traffic or block all traffic?
  - Scope: Per-user, per-IP, per-API-key, or per-endpoint?
  - Headers: Should responses include rate limit information?
  - Bypass: Can internal services bypass rate limits?


### Type 27: `circuit_breaker`
**Resilience patterns, fallback behavior, degraded operation**

What it covers: Circuit breaker on external dependencies, bulkhead isolation,
retry with backoff, timeout configuration, fallback responses.

Example ACs:
- "Circuit breaker opens after 5 failures to payment service in 60 seconds"
- "When payment service is down, orders queued for later processing"
- "Half-open state allows 1 probe request every 30 seconds"

Contract shape:
  interface: { pattern, target_dependency }
  circuit_breaker:
    failure_threshold: 5
    window: 60s
    half_open_after: 30s
    probe_count: 1
  fallback: { behavior, response }
  preconditions: [ dependency_call_attempted ]
  postconditions: [ circuit_opens_on_threshold, fallback_served, circuit_recovers ]
  invariants: [ no_cascading_failure, fallback_acceptable_ux, metrics_emitted ]

Verification strategies:
  1. test_result (unit)           — Simulate failures, verify circuit opens
  2. test_result (half_open)      — Verify probe request after half-open delay
  3. test_result (recovery)       — Simulate recovery, verify circuit closes
  4. test_result (fallback)       — Verify fallback response during open circuit
  5. test_result (metrics)        — Verify circuit state changes emit metrics
  6. config_validation            — Resilience4j/Hystrix config matches spec

Negotiation focus:
  - Failure definition: Is a timeout a failure? A 500? A 429?
  - Fallback: Cached data? Degraded response? Queue for later? Error?
  - Granularity: Per-method circuit breaker or per-dependency?
  - Recovery: How quickly should it recover after dependency comes back?
  - Metrics: Do you need a dashboard showing circuit breaker state?


---

## Category F: Frontend & User Experience

### Type 28: `ui_component`
**New UI components, modified layouts, interactive elements**

What it covers: New pages, modified forms, responsive layouts, modals,
navigation changes, error displays, loading states.

Example ACs:
- "User sees loading spinner while profile data is fetching"
- "Error message displayed when form submission fails"
- "Profile page shows user avatar, name, and email"
- "Modal confirms before account deletion"

Contract shape:
  interface: { component, page, trigger }
  visual_contract:
    states: [ loading, success, error, empty ]
    elements: [ { selector, content, visibility_condition } ]
    interactions: [ { trigger, expected_behavior } ]
  preconditions: [ page_loaded, user_authenticated ]
  postconditions: [ correct_data_displayed, interactions_functional ]
  invariants: [ responsive, accessible, no_layout_shift ]

Verification strategies:
  1. test_result (component_test) — React Testing Library / Vue Test Utils
  2. test_result (e2e)            — Cypress / Playwright full flow test
  3. test_result (snapshot)       — Visual regression (Percy / Chromatic)
  4. cli_exit_code (a11y)         — axe-core / pa11y accessibility scan
  5. test_result (responsive)     — Test at mobile, tablet, desktop breakpoints
  6. manual_gate                  — Design review sign-off

Negotiation focus:
  - All states: What does it look like loading? Error? Empty data?
  - Responsive: What changes at mobile breakpoint?
  - Accessibility: Keyboard navigable? Screen reader friendly? Color contrast?
  - Error handling: How are API errors displayed to the user?
  - Loading: Skeleton loader? Spinner? Progressive rendering?


### Type 29: `accessibility`
**WCAG compliance, screen reader support, keyboard navigation**

What it covers: ARIA labels, focus management, color contrast, skip navigation,
form labels, image alt text, heading hierarchy, live regions.

Example ACs:
- "All form inputs have associated labels"
- "Color contrast ratio meets WCAG AA (4.5:1)"
- "All interactive elements reachable via keyboard"
- "Screen reader announces dynamic content updates"

Contract shape:
  interface: { wcag_level, scope }
  requirements:
    - { criterion: "1.1.1", description: "Non-text Content", requirement: "All images have alt text" }
    - { criterion: "1.4.3", description: "Contrast", requirement: "4.5:1 for normal text" }
    - { criterion: "2.1.1", description: "Keyboard", requirement: "All functionality keyboard accessible" }
  preconditions: [ page_rendered ]
  postconditions: [ zero_violations_at_target_level ]
  invariants: [ no_regression_from_baseline ]

Verification strategies:
  1. cli_exit_code (axe)          — axe-core automated scan (catches ~30% of issues)
  2. cli_exit_code (pa11y)        — pa11y-ci against all routes
  3. test_result (keyboard)       — Cypress/Playwright tab-order test
  4. test_result (screen_reader)  — ARIA attribute assertions
  5. cli_exit_code (lighthouse)   — Lighthouse accessibility score ≥ 90
  6. manual_gate                  — Manual screen reader testing (catches remaining 70%)

Negotiation focus:
  - WCAG level: A, AA, or AAA? (AA is standard, AAA is aspirational)
  - Dynamic content: Are ARIA live regions needed for updates?
  - Focus management: Where does focus go after modal open/close?
  - Color alone: Is information conveyed by color alone? (Color blindness)
  - Automated vs manual: Automated tools catch only ~30% of a11y issues


### Type 30: `internationalization`
**i18n/l10n, translation, locale-specific formatting, RTL support**

What it covers: New language support, date/number/currency formatting,
string extraction, RTL layout, pluralization rules, locale detection.

Example ACs:
- "Application supports English, Spanish, and French"
- "Dates formatted according to user's locale"
- "Currency displayed in user's local currency with correct symbol"
- "Right-to-left layout for Arabic locale"

Contract shape:
  interface: { i18n_framework, supported_locales }
  locale_contract:
    locales: [ en-US, es-MX, fr-FR, ar-SA ]
    string_extraction: { tool, format, location }
    formatting_rules:
      date: { en_US: "MM/DD/YYYY", fr_FR: "DD/MM/YYYY" }
      currency: { en_US: "$1,234.56", fr_FR: "1 234,56 €" }
  preconditions: [ locale_detected, translations_loaded ]
  postconditions: [ all_strings_translated, formatting_correct ]
  invariants: [ no_hardcoded_strings, rtl_layout_correct, fallback_to_default ]

Verification strategies:
  1. test_result (unit)           — Render component in each locale, assert translated strings
  2. test_result (formatting)     — Assert date/currency/number formatting per locale
  3. cli_exit_code (i18n_lint)    — Scan for hardcoded strings not in translation files
  4. test_result (rtl)            — Snapshot test in RTL locale
  5. test_result (missing_keys)   — Assert no missing translation keys
  6. manual_gate                  — Native speaker review of translations

Negotiation focus:
  - Pluralization: Does the language have complex plural rules? (Arabic has 6 forms)
  - Date formatting: Is it locale-aware or hardcoded?
  - Currency: Display only or actual conversion?
  - Fallback: What if a translation is missing? Show key? Fallback to English?
  - RTL: Does the layout mirror correctly?


---

## Category G: Data & Analytics

### Type 31: `data_pipeline`
**ETL jobs, data warehouse ingestion, data quality rules, transformations**

What it covers: Airflow DAGs, Spark jobs, dbt models, data quality checks,
schema evolution in data warehouse, SCD Type 2 updates.

Example ACs:
- "Daily ETL loads order data into warehouse with 4-hour SLA"
- "Data quality check rejects records with null customer_id"
- "SCD Type 2 tracks historical changes to customer addresses"

Contract shape:
  interface: { orchestrator, job_name, schedule }
  pipeline_contract:
    source: { system, table, incremental_key }
    destination: { system, table, schema }
    transformations: [ { step, logic, assertion } ]
    quality_rules:
      - { column: customer_id, rule: not_null }
      - { column: order_total, rule: ">= 0" }
      - { column: email, rule: "matches email regex" }
    sla: { max_latency: "4 hours", max_records_dropped: "0.1%" }
  preconditions: [ source_available, destination_writable, previous_run_completed ]
  postconditions: [ data_loaded, row_count_matches, quality_rules_pass ]
  invariants: [ idempotent_rerun, no_duplicates, schema_evolution_handled ]

Verification strategies:
  1. test_result (dbt_test)       — dbt test for data quality rules
  2. test_result (unit)           — Transformation logic tested with sample data
  3. cli_exit_code (great_expectations) — Data quality framework validation
  4. test_result (idempotency)    — Run pipeline twice, assert same row count
  5. deployment_check             — DAG/job definition exists in orchestrator
  6. metric_query                 — Pipeline completion time within SLA

Negotiation focus:
  - Idempotency: Can the pipeline be safely re-run? (INSERT vs UPSERT)
  - Late-arriving data: What if source data arrives after the pipeline runs?
  - Schema evolution: What if the source adds a column?
  - Data quality: What percentage of bad records is acceptable?
  - Backfill: Can the pipeline process historical data on demand?


### Type 32: `analytics_event`
**Product analytics tracking, Segment/Amplitude/Mixpanel events**

What it covers: New tracking events, event properties, user identification,
funnel tracking, experiment exposure events.

Example ACs:
- "Track 'profile_viewed' event with source and duration"
- "Track 'checkout_started' with cart value and item count"
- "Experiment exposure event fires on feature flag evaluation"

Contract shape:
  interface: { analytics_provider, event_name }
  event_schema:
    name: "profile_viewed"
    properties:
      required: [ user_id, source, timestamp ]
      optional: [ duration_ms, referrer ]
    identity: { user_id: "authenticated user ID" }
  preconditions: [ analytics_sdk_initialized, user_consented ]
  postconditions: [ event_sent_to_provider, properties_correct ]
  invariants: [ no_pii_in_properties, consent_respected, event_deduped ]

Verification strategies:
  1. test_result (unit)           — Mock analytics SDK, assert event fired with properties
  2. test_result (integration)    — Capture events in test, assert schema
  3. config_validation            — Tracking plan in Segment/Avo matches code
  4. test_result (consent)        — Verify no events fire when consent not given
  5. deployment_check             — Tracking plan document matches implementation

Negotiation focus:
  - What properties? Be specific — analytics debt is hard to fix retroactively
  - PII: Never put email, name, or phone in event properties
  - Consent: Does this require cookie consent? GDPR opt-in?
  - Deduplication: Can the same event fire twice on page reload?
  - Timing: When exactly does the event fire? (Page load? Button click? After API response?)


---

## Category H: Documentation & Contracts

### Type 33: `api_documentation`
**OpenAPI spec updates, README changes, API reference documentation**

What it covers: New endpoint documentation, example updates, schema changes,
deprecation notices, migration guides, changelog entries.

Example ACs:
- "OpenAPI spec updated to include new /users/me endpoint"
- "API changelog includes breaking change notice for v2"
- "README includes authentication setup instructions"

Contract shape:
  interface: { doc_format, doc_location }
  documentation:
    openapi_path: "docs/openapi.yaml"
    changelog_path: "CHANGELOG.md"
    sections_required: [ endpoint, auth, examples, errors ]
  preconditions: [ code_change_exists ]
  postconditions: [ docs_match_implementation ]
  invariants: [ no_undocumented_endpoints, examples_are_runnable ]

Verification strategies:
  1. cli_exit_code (openapi_diff) — OpenAPI spec matches live implementation
  2. cli_exit_code (spectral)     — OpenAPI linting (Spectral)
  3. deployment_check             — Documentation file exists and is non-empty
  4. test_result (example_test)   — Code examples in docs actually compile/run
  5. config_validation            — All endpoints in code have OpenAPI entries

Negotiation focus:
  - Do the examples use real or mock data?
  - Are error responses documented?
  - Is there a changelog entry for this change?
  - Are breaking changes clearly marked with migration instructions?


### Type 34: `api_versioning`
**API version transitions, deprecation, backwards compatibility**

What it covers: New API version introduction, old version deprecation schedule,
content negotiation, version routing, migration period.

Example ACs:
- "v2 endpoint accepts new field format while v1 remains unchanged"
- "v1 returns Deprecation header with sunset date"
- "Both v1 and v2 active during 6-month migration period"

Contract shape:
  interface: { versioning_strategy, versions_active }
  version_contract:
    strategy: url_path | header | query_param | content_negotiation
    active_versions: [ v1, v2 ]
    deprecated: [ { version: v1, sunset_date: "2026-09-01", deprecation_header: true } ]
    breaking_changes: [ { field, v1_behavior, v2_behavior } ]
  preconditions: [ version_specified_in_request ]
  postconditions: [ correct_version_served, deprecation_headers_present ]
  invariants: [ v1_unchanged, v2_fully_documented, migration_guide_exists ]

Verification strategies:
  1. test_result (v1)             — All existing v1 tests still pass unchanged
  2. test_result (v2)             — New v2 behavior tested
  3. test_result (header)         — Deprecation + Sunset headers present on v1
  4. test_result (routing)        — Correct version served based on request
  5. deployment_check             — Migration guide document exists

Negotiation focus:
  - Strategy: URL path (/v1/ vs /v2/) or header (Accept-Version)?
  - Sunset timeline: How long do both versions coexist?
  - Breaking changes: What exactly changed between versions?
  - Default: What happens if no version is specified?


---

## Category I: Testing & Quality Infrastructure

### Type 35: `test_infrastructure`
**Test fixtures, test containers, mock services, test data management**

What it covers: Shared test fixtures, Testcontainers setup, WireMock stubs,
test database seeding, factory classes, test environment setup.

Example ACs:
- "Integration tests use Testcontainers for PostgreSQL"
- "WireMock stubs for Stripe API available in test suite"
- "Test data factory can generate valid user entities"

Contract shape:
  interface: { test_framework, infrastructure_component }
  test_contract:
    containers: [ { image, config, ports } ]
    mocks: [ { service, stub_file, scenarios } ]
    fixtures: [ { entity, factory_class, variations } ]
  preconditions: [ docker_available, test_config_exists ]
  postconditions: [ tests_use_real_dependencies, no_flaky_external_calls ]
  invariants: [ tests_isolated, no_shared_state, deterministic ]

Verification strategies:
  1. test_result (meta_test)      — The test infrastructure itself is tested
  2. test_result (isolation)      — Tests pass in any order (no ordering dependency)
  3. cli_exit_code                — Docker compose up / Testcontainers startup succeeds
  4. config_validation            — WireMock stubs match actual API responses
  5. test_result (deterministic)  — Same tests pass on repeated runs

Negotiation focus:
  - Isolation: Can tests run in parallel without interfering?
  - Determinism: Are there time-dependent or order-dependent tests?
  - Speed: How long does container startup add to test suite?
  - Fidelity: Do mock services accurately represent real APIs?


---

## Category J: Migration & Refactoring

### Type 36: `code_refactoring`
**Internal restructuring with no behavior change**

What it covers: Extracting classes/methods, renaming, moving packages,
reducing duplication, pattern standardization, dependency cleanup.

Example ACs:
- "Extract payment logic from OrderService into PaymentService"
- "Standardize all controllers to use ResponseEntity pattern"
- "Replace manual JSON parsing with Jackson annotations"

Contract shape:
  interface: { refactoring_type, scope }
  behavior_preservation:
    existing_tests: "ALL must continue to pass"
    new_tests: "None required (behavior unchanged)"
    coverage_delta: ">= 0 (must not decrease)"
  preconditions: [ existing_test_coverage_sufficient ]
  postconditions: [ all_existing_tests_pass, no_behavior_change ]
  invariants: [ test_coverage_not_decreased, no_new_warnings ]

Verification strategies:
  1. test_result (existing)       — 100% of existing tests pass without modification
  2. cli_exit_code (coverage)     — Coverage >= before refactoring
  3. cli_exit_code (lint)         — No new lint warnings introduced
  4. test_result (smoke)          — Manual smoke test of affected flows
  5. deployment_check             — No API contract changes (OpenAPI diff clean)

Negotiation focus:
  - Is there sufficient test coverage to guarantee behavior preservation?
  - If not, should tests be written BEFORE the refactoring?
  - Are there integration tests that cover the affected flows?


### Type 37: `dependency_upgrade`
**Library/framework version upgrades, language version upgrades**

What it covers: Spring Boot 3.1→3.2, Node 18→20, React 17→18, database driver
upgrades, ORM upgrades, build tool upgrades.

Example ACs:
- "Upgrade Spring Boot from 3.1 to 3.2"
- "Migrate from Java 17 to Java 21"
- "Replace deprecated WebSecurityConfigurerAdapter"

Contract shape:
  interface: { dependency, from_version, to_version }
  upgrade_contract:
    breaking_changes: [ { api, old_usage, new_usage } ]
    deprecated_apis_replaced: [ { old, new } ]
    config_changes: [ { file, change } ]
  preconditions: [ code_compiles_with_old_version ]
  postconditions: [ code_compiles_with_new_version, all_tests_pass, no_deprecation_warnings ]
  invariants: [ no_behavior_change, no_new_vulnerabilities ]

Verification strategies:
  1. test_result (existing)       — All existing tests pass
  2. cli_exit_code (compile)      — Clean compilation with zero warnings
  3. cli_exit_code (dependency)   — No new CVEs introduced (dependency scan)
  4. cli_exit_code (deprecation)  — No deprecation warnings from upgraded dependency
  5. test_result (smoke)          — Key user flows work end-to-end

Negotiation focus:
  - Breaking changes: What APIs changed between versions?
  - Deprecations: What needs replacing before the next upgrade?
  - Transitive dependencies: What else gets pulled in?
  - Compatibility: Do other dependencies work with the new version?


### Type 38: `data_migration`
**One-time data transformations, backfills, data format changes**

What it covers: Backfilling new columns, migrating data between tables,
format conversions, data cleanup, deduplication, data merging.

Example ACs:
- "Backfill last_login column from audit_log table"
- "Merge duplicate customer records by email"
- "Convert all phone numbers to E.164 format"

Contract shape:
  interface: { migration_type, scope, strategy }
  data_contract:
    source: { table, query, row_count_estimate }
    destination: { table, column, transformation }
    batch_size: 1000
    strategy: online | offline | dual_write
  preconditions: [ source_data_exists, destination_column_exists ]
  postconditions: [ all_rows_migrated, data_valid, no_duplicates ]
  failures: [ partial_migration, data_conflict, timeout ]
  invariants: [ idempotent, reversible, no_downtime, progress_tracked ]

Verification strategies:
  1. test_result (unit)           — Transformation logic tested with edge cases
  2. test_result (dry_run)        — Run migration in read-only mode, verify expected changes
  3. test_result (idempotency)    — Run twice, same result
  4. test_result (count_match)    — Source rows == destination rows
  5. test_result (validation)     — All migrated data passes validation rules
  6. deployment_check             — Rollback script exists

Negotiation focus:
  - Batch size: How many rows per batch? (Too many = lock contention)
  - Idempotency: Can it be safely re-run if interrupted?
  - Validation: How do you verify the migrated data is correct?
  - Rollback: Can you undo the migration if something goes wrong?
  - Downtime: Does this require a maintenance window?
  - Progress: How do you track how far along the migration is?


---

## Category K: Cross-Cutting Concerns

### Type 39: `error_handling`
**Error response standardization, exception hierarchy, error recovery**

What it covers: Global exception handlers, error response format standardization,
custom exception classes, error code registry, error page customization.

Example ACs:
- "All API errors return consistent JSON format with error code"
- "Unhandled exceptions return 500 with generic message (no stack trace)"
- "Error codes documented in error registry"

Contract shape:
  interface: { error_handler_type, scope }
  error_format:
    standard_body: { error_code, message, timestamp, path, request_id }
    forbidden_in_response: [ stack_trace, sql_query, internal_class_name ]
  error_registry:
    - { code: "AUTH_001", status: 401, message: "Authentication required" }
    - { code: "AUTH_002", status: 401, message: "Token expired" }
  preconditions: [ exception_thrown ]
  postconditions: [ consistent_error_format, appropriate_status_code, request_id_included ]
  invariants: [ no_information_leakage, all_exceptions_handled, errors_logged ]

Verification strategies:
  1. test_result (unit)           — Each error code returns correct status + body
  2. test_result (negative)       — Force unhandled exception, verify generic 500 (no leak)
  3. test_result (format)         — All error responses match standard schema
  4. deployment_check             — Error registry document exists
  5. test_result (request_id)     — Error response includes correlation/request ID

Negotiation focus:
  - Information leakage: What's safe to show the user vs what stays in logs?
  - Error codes: Are error codes unique across the application? Documented?
  - Retryable: Which errors should the client retry?
  - Localization: Should error messages be translated?


### Type 40: `idempotency`
**Idempotent API operations, deduplication, exactly-once processing**

What it covers: Idempotency key handling, request deduplication, safe retries,
exactly-once event processing, upsert patterns.

Example ACs:
- "POST /orders accepts Idempotency-Key header for safe retries"
- "Duplicate order submissions within 24h return original response"
- "Event processing records event_id to prevent double-processing"

Contract shape:
  interface: { mechanism, scope }
  idempotency_contract:
    key_source: header | payload_field | computed
    key_header: "Idempotency-Key"
    storage: redis | database
    ttl: 86400  # 24 hours
    response_on_duplicate: original_response | 409_conflict
  preconditions: [ idempotency_key_provided ]
  postconditions: [ first_request_processed, duplicate_returns_cached_response ]
  invariants: [ no_double_processing, no_double_charging, key_expires_after_ttl ]

Verification strategies:
  1. test_result (unit)           — Send request twice with same key, assert single effect
  2. test_result (race)           — Two simultaneous requests with same key, assert one wins
  3. test_result (different_key)  — Different keys create separate resources
  4. test_result (expired_key)    — After TTL, same key creates new resource
  5. config_validation            — Redis TTL or DB cleanup job configured

Negotiation focus:
  - Key source: Client-generated UUID? Or derived from request body?
  - Storage: Where are keys stored? Redis? Database? In-memory?
  - TTL: How long is the deduplication window?
  - Response: Return original response? Or 409 Conflict?
  - Scope: Per-user or global?


### Type 41: `deprecation`
**Removing old features, sunsetting endpoints, migration from legacy**

What it covers: Endpoint deprecation, feature removal, library removal,
legacy system decommission, migration deadline enforcement.

Example ACs:
- "v1 profile endpoint returns Deprecation header starting March 1"
- "Legacy password hash migrated to bcrypt on next login"
- "Old notification system decommissioned after all users migrated"

Contract shape:
  interface: { deprecated_component, sunset_date, replacement }
  deprecation_plan:
    deprecated: "/api/v1/users/profile"
    replacement: "/api/v2/users/me"
    sunset_date: "2026-09-01"
    headers:
      Deprecation: "true"
      Sunset: "Sat, 01 Sep 2026 00:00:00 GMT"
      Link: "</api/v2/users/me>; rel=\"successor-version\""
    migration_guide: "docs/migration/v1-to-v2.md"
  preconditions: [ replacement_available, migration_guide_published ]
  postconditions: [ deprecation_headers_present, logging_active, docs_updated ]
  invariants: [ deprecated_endpoint_still_functional, usage_tracked ]

Verification strategies:
  1. test_result (headers)        — Deprecation + Sunset headers present
  2. test_result (functional)     — Deprecated endpoint still works correctly
  3. test_result (replacement)    — Replacement endpoint handles all use cases
  4. deployment_check             — Migration guide exists
  5. metric_query                 — Usage tracking shows migration progress
  6. config_validation            — Sunset date is in the future (not expired)

Negotiation focus:
  - Timeline: How long is the deprecation period? (30 days? 6 months?)
  - Communication: How are consumers notified? (Headers? Email? Changelog?)
  - Usage tracking: How do you know when it's safe to remove?
  - Fallback: If the replacement breaks, can you un-deprecate?


---

## The Complete Type Enum

```yaml
# All 41 feature types organized by category

feature_types:

  # Category A: Backend Behavior
  - api_behavior              # 1.  REST/GraphQL/gRPC endpoint behavior
  - data_schema               # 2.  Database migrations, schema changes
  - data_operation            # 3.  CRUD logic, complex queries, stored procedures
  - event_consumer            # 4.  Message queue consumers
  - event_producer            # 5.  Publishing events/messages
  - scheduled_job             # 6.  Cron jobs, batch processing
  - external_integration      # 7.  Third-party API calls
  - state_transition          # 8.  Business workflow state machines

  # Category B: Observability & Monitoring
  - alerting_rule             # 9.  APM alerts, PagerDuty rules
  - structured_logging        # 10. Log format, audit logging
  - metric_emission           # 11. Custom metrics (counters/gauges/histograms)
  - distributed_tracing       # 12. OTel spans, trace propagation
  - health_endpoint           # 13. Readiness/liveness probes
  - dashboard                 # 14. Grafana/NR dashboards

  # Category C: Security & Compliance
  - authentication            # 15. Auth mechanisms, SSO, token handling
  - authorization             # 16. RBAC, permissions, resource access
  - encryption                # 17. Data encryption at rest/transit
  - data_privacy              # 18. GDPR, retention, erasure
  - vulnerability_remediation # 19. CVE fixes, dependency patches

  # Category D: Infrastructure & Deployment
  - infrastructure_config     # 20. Terraform/K8s/Docker changes
  - ci_cd_pipeline            # 21. Pipeline changes, quality gates
  - feature_flag              # 22. Feature toggles, gradual rollout
  - container_security        # 23. Image hardening, supply chain

  # Category E: Performance & Reliability
  - performance_sla           # 24. Latency targets, throughput
  - caching                   # 25. Cache implementation, invalidation
  - rate_limiting             # 26. Request throttling, quotas
  - circuit_breaker           # 27. Resilience patterns, fallbacks

  # Category F: Frontend & User Experience
  - ui_component              # 28. UI components, pages, layouts
  - accessibility             # 29. WCAG compliance, a11y
  - internationalization      # 30. i18n/l10n, translations

  # Category G: Data & Analytics
  - data_pipeline             # 31. ETL, data warehouse, data quality
  - analytics_event           # 32. Product analytics tracking

  # Category H: Documentation & Contracts
  - api_documentation         # 33. OpenAPI specs, README, changelogs
  - api_versioning            # 34. Version transitions, deprecation

  # Category I: Testing & Quality
  - test_infrastructure       # 35. Test fixtures, containers, mocks

  # Category J: Migration & Refactoring
  - code_refactoring          # 36. Internal restructuring, no behavior change
  - dependency_upgrade        # 37. Library/framework version upgrades
  - data_migration            # 38. One-time data transformations, backfills

  # Category K: Cross-Cutting Concerns
  - error_handling            # 39. Error format, exception hierarchy
  - idempotency               # 40. Dedup, safe retries, exactly-once
  - deprecation               # 41. Sunsetting features, migration paths
```

---

## Verification Strategy Master Matrix

Every verification strategy available in SPECify, with the types that use them:

```
VERIFICATION STRATEGY         │ USED BY TYPES                    │ STRENGTH
──────────────────────────────┼──────────────────────────────────┼──────────
test_result (unit)            │ 1-8, 10-12, 15-16, 25-32,       │ Strongest
                              │ 35-36, 38-41                     │
test_result (integration)     │ 1, 4-5, 7, 13, 32, 35           │ Strongest
test_result (contract)        │ 1, 7, 34                         │ Strongest
test_result (property-based)  │ 1, 3, 8                          │ Strong
test_result (e2e)             │ 28-30                            │ Strong
test_result (snapshot/visual) │ 28, 30                           │ Strong
test_result (load)            │ 24, 26                           │ Strong
test_result (security)        │ 15-16, 18                        │ Strong
test_result (migration)       │ 2, 38                            │ Strong
test_result (idempotency)     │ 4, 6, 38, 40                    │ Strong
test_result (concurrency)     │ 8, 40                            │ Strong
query_plan_test               │ 3                                │ Strong
cli_exit_code (SAST)          │ 19                               │ Strong
cli_exit_code (dependency)    │ 19, 23, 37                       │ Strong
cli_exit_code (secret_scan)   │ 19                               │ Strong
cli_exit_code (lint)          │ 20-21, 23, 33, 36                │ Medium
cli_exit_code (a11y)          │ 29                               │ Medium
cli_exit_code (migration)     │ 2                                │ Medium
cli_exit_code (openapi_diff)  │ 1, 33, 34                        │ Medium
config_validation             │ 4, 5, 9, 11-12, 20-22,          │ Medium
                              │ 24-27, 32, 34, 41                │
deployment_check              │ 2, 5, 9, 13-14, 17, 20-21, 23,  │ Medium
                              │ 31, 33-34, 38, 41                │
schema_validation             │ 9, 14                            │ Medium
api_health_probe              │ 1, 7, 11, 13, 20                 │ Weaker
metric_query                  │ 24, 31, 41                       │ Weaker
simulation_test               │ 9                                │ Weaker
manual_gate                   │ 14, 28-30                        │ Weakest
penetration_test              │ 15, 19                           │ Context
```

---

## Implementation Priority

For SPECify production launch, implement types in this order based on
frequency of Jira tickets and verification complexity:

Tier 1 — Launch (covers ~60% of tickets):
  api_behavior, data_schema, data_operation, error_handling

Tier 2 — Fast follow (covers ~80%):
  event_consumer, event_producer, state_transition, authentication,
  authorization, structured_logging

Tier 3 — Full coverage (covers ~95%):
  scheduled_job, external_integration, feature_flag, performance_sla,
  caching, rate_limiting, alerting_rule, metric_emission

Tier 4 — Complete (covers ~100%):
  Everything else
