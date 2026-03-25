package com.example.dogservice.steps;

import com.example.dogservice.DogServiceApplication;
import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;

@CucumberContextConfiguration
@SpringBootTest(classes = DogServiceApplication.class, webEnvironment = WebEnvironment.RANDOM_PORT)
public class CucumberSpringConfig {
}
