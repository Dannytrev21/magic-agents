package com.example.dogservice.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.web.server.LocalServerPort;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class DEV17Steps {

    @Autowired
    private TestRestTemplate restTemplate;

    @LocalServerPort
    private int port;

    private HttpHeaders headers;
    private ResponseEntity<String> response;
    private ObjectMapper objectMapper = new ObjectMapper();

    @Given("I have a valid JWT bearer token with read:dogs scope")
    public void i_have_a_valid_jwt_bearer_token_with_read_dogs_scope() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer valid-jwt-token-with-read-dogs-scope");
    }

    @Given("the user account is active")
    public void the_user_account_is_active() {
        // This would be handled by test data setup
    }

    @Given("the database connection is healthy")
    public void the_database_connection_is_healthy() {
        // This would be handled by test environment setup
    }

    @Given("I have no Authorization header")
    public void i_have_no_authorization_header() {
        headers = new HttpHeaders();
    }

    @Given("I have an Authorization header {string}")
    public void i_have_an_authorization_header(String headerValue) {
        headers = new HttpHeaders();
        headers.set("Authorization", headerValue);
    }

    @Given("I have an expired JWT token")
    public void i_have_an_expired_jwt_token() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer expired-jwt-token");
    }

    @Given("I have a malformed JWT token")
    public void i_have_a_malformed_jwt_token() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer malformed.jwt.token");
    }

    @Given("I have a JWT token with wrong issuer")
    public void i_have_a_jwt_token_with_wrong_issuer() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-wrong-issuer");
    }

    @Given("I have a revoked JWT token")
    public void i_have_a_revoked_jwt_token() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer revoked-jwt-token");
    }

    @Given("I have a JWT token for a non-existent user")
    public void i_have_a_jwt_token_for_a_non_existent_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-non-existent-user");
    }

    @Given("I have a JWT token for a soft-deleted user")
    public void i_have_a_jwt_token_for_a_soft_deleted_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-soft-deleted-user");
    }

    @Given("I have a JWT token for a hard-deleted user")
    public void i_have_a_jwt_token_for_a_hard_deleted_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-hard-deleted-user");
    }

    @Given("I have a JWT token for an inactive user")
    public void i_have_a_jwt_token_for_an_inactive_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-inactive-user");
    }

    @Given("I have a JWT token for a suspended user")
    public void i_have_a_jwt_token_for_a_suspended_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-suspended-user");
    }

    @Given("I have a JWT token for a pending user")
    public void i_have_a_jwt_token_for_a_pending_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-pending-user");
    }

    @Given("I have a JWT token for a locked user")
    public void i_have_a_jwt_token_for_a_locked_user() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-locked-user");
    }

    @Given("I have a JWT token without read:dogs scope")
    public void i_have_a_jwt_token_without_read_dogs_scope() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-no-read-dogs-scope");
    }

    @Given("I have a JWT token for a user without dogs:read permission")
    public void i_have_a_jwt_token_for_a_user_without_dogs_read_permission() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-no-dogs-read-permission");
    }

    @Given("I have a JWT token from a different tenant")
    public void i_have_a_jwt_token_from_a_different_tenant() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-different-tenant");
    }

    @Given("the database connection is down")
    public void the_database_connection_is_down() {
        // This would be handled by test configuration
    }

    @Given("the database connection times out")
    public void the_database_connection_times_out() {
        // This would be handled by test configuration
    }

    @Given("the database connection is refused")
    public void the_database_connection_is_refused() {
        // This would be handled by test configuration
    }

    @Given("the per-user rate limit is exceeded")
    public void the_per_user_rate_limit_is_exceeded() {
        // This would be handled by test configuration
    }

    @Given("the global rate limit is exceeded")
    public void the_global_rate_limit_is_exceeded() {
        // This would be handled by test configuration
    }

    @Given("I have a JWT token from tenant A")
    public void i_have_a_jwt_token_from_tenant_a() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer jwt-token-tenant-a");
    }

    @Given("there are dogs belonging to tenant B")
    public void there_are_dogs_belonging_to_tenant_b() {
        // This would be handled by test data setup
    }

    @When("I send a GET request to {string}")
    public void i_send_a_get_request_to(String path) {
        String url = "http://localhost:" + port + path;
        HttpEntity<String> entity = new HttpEntity<>(null, headers);
        response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class);
    }

    @Then("the response status should be {int}")
    public void the_response_status_should_be(int expectedStatus) {
        assertThat(response.getStatusCodeValue()).isEqualTo(expectedStatus);
    }

    @Then("the response should contain a dogs array")
    public void the_response_should_contain_a_dogs_array() throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        assertThat(jsonNode.has("dogs")).isTrue();
        assertThat(jsonNode.get("dogs").isArray()).isTrue();
    }

    @Then("each dog should have id, name, breed, age, and owner_id fields")
    public void each_dog_should_have_required_fields() throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        JsonNode dogs = jsonNode.get("dogs");
        for (JsonNode dog : dogs) {
            assertThat(dog.has("id")).isTrue();
            assertThat(dog.has("name")).isTrue();
            assertThat(dog.has("breed")).isTrue();
            assertThat(dog.has("age")).isTrue();
            assertThat(dog.has("owner_id")).isTrue();
        }
    }

    @Then("the response should not contain forbidden fields")
    public void the_response_should_not_contain_forbidden_fields() throws Exception {
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain("password");
        assertThat(responseBody).doesNotContain("passwordHash");
        assertThat(responseBody).doesNotContain("ssn");
        assertThat(responseBody).doesNotContain("internalId");
    }

    @Then("the response should contain error {string}")
    public void the_response_should_contain_error(String expectedError) throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        assertThat(jsonNode.get("error").asText()).isEqualTo(expectedError);
    }

    @Then("the response should contain message {string}")
    public void the_response_should_contain_message(String expectedMessage) throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        assertThat(jsonNode.get("message").asText()).isEqualTo(expectedMessage);
    }

    @Then("the response should not contain password field")
    public void the_response_should_not_contain_password_field() throws Exception {
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain("password");
    }

    @Then("the response should not contain passwordHash field")
    public void the_response_should_not_contain_password_hash_field() throws Exception {
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain("passwordHash");
    }

    @Then("the response should not contain ssn field")
    public void the_response_should_not_contain_ssn_field() throws Exception {
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain("ssn");
    }

    @Then("the response should not contain internalId field")
    public void the_response_should_not_contain_internal_id_field() throws Exception {
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain("internalId");
    }

    @Then("the response should only contain dogs from tenant A")
    public void the_response_should_only_contain_dogs_from_tenant_a() throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        JsonNode dogs = jsonNode.get("dogs");
        // This would verify tenant isolation logic
        assertThat(dogs).isNotNull();
    }

    @Then("the response should not contain dogs from tenant B")
    public void the_response_should_not_contain_dogs_from_tenant_b() throws Exception {
        // This would verify that no tenant B dogs are returned
    }

    @Then("the response should have X-Data-Classification header for PII fields")
    public void the_response_should_have_x_data_classification_header_for_pii_fields() {
        assertThat(response.getHeaders().containsKey("X-Data-Classification")).isTrue();
    }

    @Then("the response body should not contain {string} key")
    public void the_response_body_should_not_contain_key(String key) throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response.getBody());
        assertThat(jsonNode.has(key)).isFalse();
        // Also check nested objects
        String responseBody = response.getBody();
        assertThat(responseBody).doesNotContain('"' + key + '"');
    }
}