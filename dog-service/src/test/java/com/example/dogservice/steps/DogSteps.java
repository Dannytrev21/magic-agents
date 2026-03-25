package com.example.dogservice.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

public class DogSteps {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    private ResponseEntity<String> lastResponse;
    private HttpHeaders headers = new HttpHeaders();

    private String baseUrl() {
        return "http://localhost:" + port + "/api/v1/dogs";
    }

    @Given("I have a valid auth token")
    public void i_have_a_valid_auth_token() {
        headers = new HttpHeaders();
        headers.set("Authorization", "Bearer valid-token");
        headers.setContentType(MediaType.APPLICATION_JSON);
    }

    @Given("I have no auth token")
    public void i_have_no_auth_token() {
        headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
    }

    @When("I request the list of dogs")
    public void i_request_the_list_of_dogs() {
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        lastResponse = restTemplate.exchange(baseUrl(), HttpMethod.GET, entity, String.class);
    }

    @When("I request dog with id {long}")
    public void i_request_dog_with_id(Long id) {
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        lastResponse = restTemplate.exchange(baseUrl() + "/" + id, HttpMethod.GET, entity, String.class);
    }

    @When("I create a dog with name {string} breed {string} age {int}")
    public void i_create_a_dog(String name, String breed, int age) {
        String body = String.format("{\"name\":\"%s\",\"breed\":\"%s\",\"age\":%d}", name, breed, age);
        HttpEntity<String> entity = new HttpEntity<>(body, headers);
        lastResponse = restTemplate.exchange(baseUrl(), HttpMethod.POST, entity, String.class);
    }

    @When("I delete dog with id {long}")
    public void i_delete_dog_with_id(Long id) {
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        lastResponse = restTemplate.exchange(baseUrl() + "/" + id, HttpMethod.DELETE, entity, String.class);
    }

    @Then("the response status should be {int}")
    public void the_response_status_should_be(int status) {
        assertThat(lastResponse.getStatusCode().value()).isEqualTo(status);
    }

    @Then("the response should contain {string}")
    public void the_response_should_contain(String text) {
        assertThat(lastResponse.getBody()).contains(text);
    }

    @Then("the response should not contain {string}")
    public void the_response_should_not_contain(String text) {
        assertThat(lastResponse.getBody()).doesNotContain(text);
    }
}
