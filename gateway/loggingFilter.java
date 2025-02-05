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

        log.info("Request: {} {} from {}", 
            request.getMethod(),
            request.getRequestURI(),
            request.getRemoteAddr());
        
        try {
            filterChain.doFilter(request, response);
        } finally {
            log.info("Response: Status {} - Took {}ms",
                response.getStatus(),
                System.currentTimeMillis() - startTime);
        }
    }
}