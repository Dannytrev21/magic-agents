package com.example.dogservice.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Dog {
    private Long id;
    private String name;
    private String breed;
    private Integer age;
}
