@DEV-17 @REQ-001
Feature: Dog CRUD API verification

  @REQ-001.success
  Scenario: Successfully retrieve a dog by ID
    Given the API is running
    And a valid JWT token is available
    And a dog exists with ID 1
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 200
    And the response should contain "name"
    And the response should contain "breed"
    And the response should not contain "password"
    And the response should not contain "internalId"

  @REQ-001.FAIL-001
  Scenario: Reject request without auth token
    Given the API is running
    When I send a GET request to "/api/v1/dogs/1" without auth
    Then the response status should be 401
    And the response should contain "unauthorized"

  @REQ-001.FAIL-002
  Scenario: Reject request with expired token
    Given the API is running
    And an expired JWT token is available
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 401

  @REQ-001.FAIL-003
  Scenario: Return 404 for non-existent dog
    Given the API is running
    And a valid JWT token is available
    When I send a GET request to "/api/v1/dogs/99999" with auth
    Then the response status should be 404

  @REQ-001.INV-001
  Scenario: Response never exposes forbidden fields
    Given the API is running
    And a valid JWT token is available
    And a dog exists with ID 1
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 200
    And the response should not contain "password"
    And the response should not contain "internalId"
    And the response should not contain "ssn"
