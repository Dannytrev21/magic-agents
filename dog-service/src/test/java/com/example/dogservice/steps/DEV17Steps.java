package com.example.dogservice.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import static org.assertj.core.api.Assertions.assertThat;

@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class DEV17Steps {

    @LocalServerPort
    private int port;

    private final TestRestTemplate restTemplate = new TestRestTemplate();
    private ResponseEntity<String> response;
    private String authToken = null;
    private String baseUrl;

    @Given("the API is running")
    public void theApiIsRunning() {
        baseUrl = "http://localhost:" + port;
    }

    @Given("a valid JWT token is available")
    public void aValidJwtTokenIsAvailable() {
        authToken = "test-valid-token";
    }

    @Given("an expired JWT token is available")
    public void anExpiredJwtTokenIsAvailable() {
        authToken = "test-expired-token";
    }

    @Given("a dog exists with ID {int}")
    public void aDogExistsWithId(int id) {
        // Seed data or assume test data exists
    }

    @When("I send a GET request to {string} with auth")
    public void iSendGetRequestWithAuth(String path) {
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + authToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);
        response = restTemplate.exchange(baseUrl + path, HttpMethod.GET, entity, String.class);
    }

    @When("I send a GET request to {string} without auth")
    public void iSendGetRequestWithoutAuth(String path) {
        response = restTemplate.getForEntity(baseUrl + path, String.class);
    }

    @Then("the response status should be {int}")
    public void theResponseStatusShouldBe(int status) {
        assertThat(response.getStatusCode().value()).isEqualTo(status);
    }

    @Then("the response should contain {string}")
    public void theResponseShouldContain(String field) {
        assertThat(response.getBody()).contains(field);
    }

    @Then("the response should not contain {string}")
    public void theResponseShouldNotContain(String field) {
        assertThat(response.getBody()).doesNotContain(field);
    }
}
