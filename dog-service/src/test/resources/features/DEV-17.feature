@DEV-17 @REQ-001
Feature: Dog Service CRUD API
  As a user
  I want to list all dogs via GET /api/v1/dogs
  So that I can view available dogs in the system

  @REQ-001.success
  Scenario: Successfully list all dogs with valid authentication
    Given I have a valid JWT bearer token with read:dogs scope
    And the user account is active
    And the database connection is healthy
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 200
    And the response should contain a dogs array
    And each dog should have id, name, breed, age, and owner_id fields
    And the response should not contain forbidden fields

  @REQ-001.FAIL-001
  Scenario: Request without Authorization header
    Given I have no Authorization header
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "unauthorized"
    And the response should contain message "Authorization header required"

  @REQ-001.FAIL-002
  Scenario: Authorization header without Bearer prefix
    Given I have an Authorization header "InvalidToken"
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "unauthorized"
    And the response should contain message "Bearer token required"

  @REQ-001.FAIL-003
  Scenario: Bearer header with no token
    Given I have an Authorization header "Bearer "
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "unauthorized"
    And the response should contain message "Bearer token required"

  @REQ-001.FAIL-004
  Scenario: Expired JWT token
    Given I have an expired JWT token
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "token_expired"
    And the response should contain message "JWT token has expired"

  @REQ-001.FAIL-005
  Scenario: Malformed JWT token
    Given I have a malformed JWT token
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "invalid_token"
    And the response should contain message "Invalid JWT token format"

  @REQ-001.FAIL-006
  Scenario: JWT token with wrong issuer
    Given I have a JWT token with wrong issuer
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "invalid_token"
    And the response should contain message "JWT token from invalid issuer"

  @REQ-001.FAIL-007
  Scenario: Revoked JWT token
    Given I have a revoked JWT token
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 401
    And the response should contain error "token_revoked"
    And the response should contain message "JWT token has been revoked"

  @REQ-001.FAIL-008
  Scenario: JWT references non-existent user
    Given I have a JWT token for a non-existent user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 404
    And the response should contain error "not_found"
    And the response should contain message "User not found"

  @REQ-001.FAIL-009
  Scenario: JWT references soft-deleted user
    Given I have a JWT token for a soft-deleted user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 404
    And the response should contain error "not_found"
    And the response should contain message "User not found"

  @REQ-001.FAIL-010
  Scenario: JWT references hard-deleted user
    Given I have a JWT token for a hard-deleted user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 404
    And the response should contain error "not_found"
    And the response should contain message "User not found"

  @REQ-001.FAIL-011
  Scenario: User account is inactive
    Given I have a JWT token for an inactive user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "account_inactive"
    And the response should contain message "User account is inactive"

  @REQ-001.FAIL-012
  Scenario: User account is suspended
    Given I have a JWT token for a suspended user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "account_suspended"
    And the response should contain message "User account is suspended"

  @REQ-001.FAIL-013
  Scenario: User account is pending
    Given I have a JWT token for a pending user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "account_pending"
    And the response should contain message "User account is pending activation"

  @REQ-001.FAIL-014
  Scenario: User account is locked
    Given I have a JWT token for a locked user
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "account_locked"
    And the response should contain message "User account is locked"

  @REQ-001.FAIL-015
  Scenario: JWT missing required scope
    Given I have a JWT token without read:dogs scope
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "insufficient_scope"
    And the response should contain message "Token does not have required scope: read:dogs"

  @REQ-001.FAIL-016
  Scenario: User missing dogs:read permission
    Given I have a JWT token for a user without dogs:read permission
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "forbidden"
    And the response should contain message "Insufficient permissions to access dog data"

  @REQ-001.FAIL-017
  Scenario: Wrong tenant access attempt
    Given I have a JWT token from a different tenant
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 403
    And the response should contain error "forbidden"
    And the response should contain message "Access denied for this tenant"

  @REQ-001.FAIL-018
  Scenario: Database connection is down
    Given the database connection is down
    And I have a valid JWT bearer token with read:dogs scope
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 500
    And the response should contain error "service_unavailable"
    And the response should contain message "Database connection unavailable"

  @REQ-001.FAIL-019
  Scenario: Database connection timeout
    Given the database connection times out
    And I have a valid JWT bearer token with read:dogs scope
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 500
    And the response should contain error "service_timeout"
    And the response should contain message "Database connection timeout"

  @REQ-001.FAIL-020
  Scenario: Database connection refused
    Given the database connection is refused
    And I have a valid JWT bearer token with read:dogs scope
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 500
    And the response should contain error "service_unavailable"
    And the response should contain message "Database connection refused"

  @REQ-001.FAIL-021
  Scenario: Per-user rate limit exceeded
    Given I have a valid JWT bearer token with read:dogs scope
    And the per-user rate limit is exceeded
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 429
    And the response should contain error "rate_limit_exceeded"
    And the response should contain message "Request rate limit exceeded for user"

  @REQ-001.FAIL-022
  Scenario: Global rate limit exceeded
    Given I have a valid JWT bearer token with read:dogs scope
    And the global rate limit is exceeded
    When I send a GET request to "/api/v1/dogs"
    Then the response status should be 429
    And the response should contain error "rate_limit_exceeded"
    And the response should contain message "Global request rate limit exceeded"

  @REQ-001.INV-001
  Scenario: Response never exposes forbidden fields
    Given I have a valid JWT bearer token with read:dogs scope
    And the user account is active
    When I send a GET request to "/api/v1/dogs"
    Then the response should not contain password field
    And the response should not contain passwordHash field
    And the response should not contain ssn field
    And the response should not contain internalId field

  @REQ-001.INV-002
  Scenario: No cross-tenant data access allowed
    Given I have a JWT token from tenant A
    And there are dogs belonging to tenant B
    When I send a GET request to "/api/v1/dogs"
    Then the response should only contain dogs from tenant A
    And the response should not contain dogs from tenant B

  @REQ-001.INV-003
  Scenario: PII fields have X-Data-Classification header
    Given I have a valid JWT bearer token with read:dogs scope
    And the user account is active
    When I send a GET request to "/api/v1/dogs"
    Then the response should have X-Data-Classification header for PII fields

  @REQ-001.INV-004
  Scenario: Response must not contain forbidden fields
    Given I have a valid JWT bearer token with read:dogs scope
    And the user account is active
    When I send a GET request to "/api/v1/dogs"
    Then the response body should not contain "password" key
    And the response body should not contain "password_hash" key
    And the response body should not contain "ssn" key
    And the response body should not contain "internalId" key