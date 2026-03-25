package com.example.dogservice.repository;

import com.example.dogservice.model.Dog;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Repository
public class DogRepository {

    private final Map<Long, Dog> store = new ConcurrentHashMap<>();
    private final AtomicLong idCounter = new AtomicLong(1);

    public DogRepository() {
        // Seed data
        save(new Dog(null, "Rex", "German Shepherd", 3));
        save(new Dog(null, "Bella", "Golden Retriever", 5));
        save(new Dog(null, "Max", "Labrador", 2));
    }

    public List<Dog> findAll() {
        return new ArrayList<>(store.values());
    }

    public Optional<Dog> findById(Long id) {
        return Optional.ofNullable(store.get(id));
    }

    public Dog save(Dog dog) {
        if (dog.getId() == null) {
            dog.setId(idCounter.getAndIncrement());
        }
        store.put(dog.getId(), dog);
        return dog;
    }

    public boolean deleteById(Long id) {
        return store.remove(id) != null;
    }

    public boolean existsById(Long id) {
        return store.containsKey(id);
    }
}
