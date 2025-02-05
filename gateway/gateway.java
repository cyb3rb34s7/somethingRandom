// src/main/java/com/example/gateway/service/CacheService.java
package com.example.gateway.service;

import lombok.RequiredArgsConstructor;
import org.springframework.cache.CacheManager;
import org.springframework.stereotype.Service;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class CacheService {
    private final CacheManager cacheManager;
    private static final String CACHE_NAME = "apiResponses";

    public Optional<String> get(String key) {
        return Optional.ofNullable(cacheManager.getCache(CACHE_NAME))
                .map(cache -> cache.get(key, String.class));
    }

    public void put(String key, String value) {
        Optional.ofNullable(cacheManager.getCache(CACHE_NAME))
                .ifPresent(cache -> cache.put(key, value));
    }

    public String generateCacheKey(String method, String uri, String body) {
        return String.format("%s:%s:%s", method, uri, 
            body != null ? body.hashCode() : "null");
    }
}

// src/main/java/com/example/gateway/filter/LoggingFilter.java
package com.example.gateway.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.util.UUID;

@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class LoggingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, 
                                  HttpServletResponse response, 
                                  FilterChain filterChain) 
            throws ServletException, IOException {
        
        String requestId = UUID.randomUUID().toString();
        long startTime = System.currentTimeMillis();

        // Add request ID to MDC for correlation
        try {
            logRequest(request, requestId);
            response.addHeader("X-Request-ID", requestId);
            
            filterChain.doFilter(request, response);
        } finally {
            logResponse(response, requestId, startTime);
        }
    }

    private void logRequest(HttpServletRequest request, String requestId) {
        log.info("[{}] Request: {} {} from {} - Client: {}", 
            requestId,
            request.getMethod(),
            request.getRequestURI(),
            request.getRemoteAddr(),
            request.getHeader("X-Client-ID"));
    }

    private void logResponse(HttpServletResponse response, 
                           String requestId, 
                           long startTime) {
        long duration = System.currentTimeMillis() - startTime;
        log.info("[{}] Response: Status {} - Duration: {}ms",
            requestId,
            response.getStatus(),
            duration);
    }
}


// src/main/java/com/example/gateway/controller/GatewayController.java
package com.example.gateway.controller;

import com.example.gateway.model.ApiResponse;
import com.example.gateway.model.Route;
import com.example.gateway.service.CacheService;
import com.example.gateway.service.RouteService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;
import java.net.URI;
import java.util.Collections;
import java.util.Optional;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequiredArgsConstructor
public class GatewayController {

    private final RouteService routeService;
    private final CacheService cacheService;
    private final RestTemplate restTemplate;

    @RequestMapping(value = "/**", 
                   method = {RequestMethod.GET, RequestMethod.POST, 
                           RequestMethod.PUT, RequestMethod.DELETE})
    public ResponseEntity<?> handleRequest(
            @RequestBody(required = false) String body,
            HttpMethod method,
            HttpServletRequest request) {

        String path = request.getRequestURI();
        Optional<Route> routeOpt = routeService.findRoute(path, method);

        if (routeOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(ApiResponse.builder()
                            .status(HttpStatus.NOT_FOUND.value())
                            .message("No route found for path: " + path)
                            .build());
        }

        Route route = routeOpt.get();

        // Check cache for GET requests
        if (method == HttpMethod.GET && route.isCacheEnabled()) {
            String cacheKey = cacheService.generateCacheKey(
                method.name(), path, body);
            Optional<String> cachedResponse = cacheService.get(cacheKey);
            if (cachedResponse.isPresent()) {
                return ResponseEntity.ok(cachedResponse.get());
            }
        }

        // Forward the request
        try {
            URI uri = buildTargetUri(route, path, request.getQueryString());
            HttpHeaders headers = copyHeaders(request);
            ResponseEntity<String> response = executeRequest(
                uri, method, body, headers);

            // Cache successful GET responses if enabled
            if (method == HttpMethod.GET && route.isCacheEnabled() 
                    && response.getStatusCode().is2xxSuccessful()) {
                cacheService.put(
                    cacheService.generateCacheKey(method.name(), path, body),
                    response.getBody()
                );
            }

            return response;
        } catch (Exception e) {
            log.error("Error forwarding request: ", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.builder()
                            .status(HttpStatus.INTERNAL_SERVER_ERROR.value())
                            .message("Error forwarding request: " + e.getMessage())
                            .build());
        }
    }

    private URI buildTargetUri(Route route, String path, String queryString) {
        return UriComponentsBuilder.fromHttpUrl(route.getTargetUrl())
                .path(path)
                .query(queryString)
                .build()
                .toUri();
    }

    private HttpHeaders copyHeaders(HttpServletRequest request) {
        return Collections.list(request.getHeaderNames())
                .stream()
                .collect(Collectors.toMap(
                        headerName -> headerName,
                        headerName -> Collections.list(
                            request.getHeaders(headerName)),
                        (v1, v2) -> v1,
                        HttpHeaders::new
                ));
    }

    private ResponseEntity<String> executeRequest(
            URI uri, 
            HttpMethod method, 
            String body, 
            HttpHeaders headers) {
        HttpEntity<String> requestEntity = new HttpEntity<>(body, headers);
        return restTemplate.exchange(uri, method, requestEntity, String.class);
    }
}

// src/main/java/com/example/gateway/exception/GlobalExceptionHandler.java
package com.example.gateway.exception;

import com.example.gateway.model.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;

@Slf4j
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(GatewayException.class)
    public ResponseEntity<?> handleGatewayException(GatewayException ex) {
        log.error("Gateway error: ", ex);
        return ResponseEntity
                .status(ex.getStatusCode())
                .body(ApiResponse.builder()
                        .status(ex.getStatusCode())
                        .message(ex.getMessage())
                        .build());
    }

    @ExceptionHandler(HttpStatusCodeException.class)
    public ResponseEntity<?> handleHttpStatusCodeException(
            HttpStatusCodeException ex) {
        log.error("HTTP error from downstream service: ", ex);
        return ResponseEntity
                .status(ex.getStatusCode())
                .body(ApiResponse.builder()
                        .status(ex.getStatusCode().value())
                        .message(ex.getResponseBodyAsString())
                        .build());
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<?> handleResourceAccessException(
            ResourceAccessException ex) {
        log.error("Error accessing downstream service: ", ex);
        return ResponseEntity
                .status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.builder()
                        .status(HttpStatus.SERVICE_UNAVAILABLE.value())
                        .message("Service temporarily unavailable")
                        .build());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> handleGenericException(Exception ex) {
        log.error("Unexpected error: ", ex);
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.builder()
                        .status(HttpStatus.INTERNAL_SERVER_ERROR.value())
                        .message("Internal server error")
                        .build());
    }
}