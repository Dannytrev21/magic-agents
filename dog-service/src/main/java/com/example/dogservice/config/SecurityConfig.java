package com.example.dogservice.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;

import java.io.IOException;

@Configuration
public class SecurityConfig {

    private static final String VALID_TOKEN = "valid-token";

    @Bean
    public FilterRegistrationBean<BearerTokenFilter> bearerTokenFilter() {
        FilterRegistrationBean<BearerTokenFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(new BearerTokenFilter());
        registration.addUrlPatterns("/api/*");
        registration.setOrder(1);
        return registration;
    }

    public static class BearerTokenFilter extends OncePerRequestFilter {

        @Override
        protected void doFilterInternal(HttpServletRequest request,
                                        HttpServletResponse response,
                                        FilterChain filterChain) throws ServletException, IOException {
            String authHeader = request.getHeader("Authorization");

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                response.setStatus(401);
                response.setContentType("application/json");
                response.getWriter().write(
                        "{\"error\":\"unauthorized\",\"message\":\"Missing or invalid authorization header\"," +
                        "\"timestamp\":\"" + java.time.Instant.now() + "\",\"path\":\"" + request.getRequestURI() + "\"}");
                return;
            }

            String token = authHeader.substring(7).trim();
            if (!VALID_TOKEN.equals(token)) {
                response.setStatus(401);
                response.setContentType("application/json");
                response.getWriter().write(
                        "{\"error\":\"unauthorized\",\"message\":\"Invalid token\"," +
                        "\"timestamp\":\"" + java.time.Instant.now() + "\",\"path\":\"" + request.getRequestURI() + "\"}");
                return;
            }

            filterChain.doFilter(request, response);
        }
    }
}
