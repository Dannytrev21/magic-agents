package com.example.dogservice.controller;

import com.example.dogservice.exception.GlobalExceptionHandler.DogNotFoundException;
import com.example.dogservice.model.Dog;
import com.example.dogservice.repository.DogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/dogs")
@RequiredArgsConstructor
public class DogController {

    private final DogRepository dogRepository;

    @GetMapping
    public ResponseEntity<List<Dog>> listDogs() {
        return ResponseEntity.ok(dogRepository.findAll());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Dog> getDog(@PathVariable Long id) {
        Dog dog = dogRepository.findById(id)
                .orElseThrow(() -> new DogNotFoundException(id));
        return ResponseEntity.ok(dog);
    }

    @PostMapping
    public ResponseEntity<Dog> createDog(@RequestBody Dog dog) {
        if (dog.getName() == null || dog.getName().isBlank()) {
            throw new IllegalArgumentException("Dog name is required");
        }
        if (dog.getBreed() == null || dog.getBreed().isBlank()) {
            throw new IllegalArgumentException("Dog breed is required");
        }
        dog.setId(null); // ensure new ID is assigned
        Dog saved = dogRepository.save(dog);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Dog> updateDog(@PathVariable Long id, @RequestBody Dog dog) {
        if (!dogRepository.existsById(id)) {
            throw new DogNotFoundException(id);
        }
        if (dog.getName() == null || dog.getName().isBlank()) {
            throw new IllegalArgumentException("Dog name is required");
        }
        dog.setId(id);
        Dog updated = dogRepository.save(dog);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDog(@PathVariable Long id) {
        if (!dogRepository.deleteById(id)) {
            throw new DogNotFoundException(id);
        }
        return ResponseEntity.noContent().build();
    }
}
