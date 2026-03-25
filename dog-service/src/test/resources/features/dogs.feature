Feature: Dog API

  Scenario: List all dogs with valid auth
    Given I have a valid auth token
    When I request the list of dogs
    Then the response status should be 200

  Scenario: Get dog by id with valid auth
    Given I have a valid auth token
    When I request dog with id 1
    Then the response status should be 200
    And the response should contain "Rex"

  Scenario: Get non-existent dog returns 404
    Given I have a valid auth token
    When I request dog with id 999
    Then the response status should be 404

  Scenario: List dogs without auth returns 401
    Given I have no auth token
    When I request the list of dogs
    Then the response status should be 401

  Scenario: Create a dog with valid auth
    Given I have a valid auth token
    When I create a dog with name "Buddy" breed "Poodle" age 4
    Then the response status should be 201
    And the response should contain "Buddy"

  Scenario: Delete a dog with valid auth
    Given I have a valid auth token
    When I delete dog with id 2
    Then the response status should be 204
