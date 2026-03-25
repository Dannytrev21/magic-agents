package com.example.dogservice.exception;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.Instant;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(DogNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(DogNotFoundException ex, HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
                "error", "not_found",
                "message", ex.getMessage(),
                "timestamp", Instant.now().toString(),
                "path", request.getRequestURI()
        ));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex, HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                "error", "bad_request",
                "message", ex.getMessage(),
                "timestamp", Instant.now().toString(),
                "path", request.getRequestURI()
        ));
    }

    public static class DogNotFoundException extends RuntimeException {
        public DogNotFoundException(Long id) {
            super("Dog not found with id: " + id);
        }
    }
}
