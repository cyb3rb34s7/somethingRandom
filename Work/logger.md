// build.gradle - Add these dependencies
dependencies {
    // Existing dependencies...
    
    // Log4j2 dependencies
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'
    implementation 'org.apache.logging.log4j:log4j-layout-template-json:2.20.0'
    
    // Exclude default logging
    configurations {
        all {
            exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
        }
    }
}

// src/main/resources/log4j2.xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Properties>
        <Property name="LOG_PATTERN">
            {
                "timestamp": "$${date:yyyy-MM-dd'T'HH:mm:ss.SSSZ}",
                "level": "$${level}",
                "traceId": "$${ctx:traceId:-}",
                "service": "cms-monitoring-service",
                "operation": "$${ctx:operation:-}",
                "sourceService": "$${ctx:sourceService:-}",
                "environment": "$${ctx:environment:-}",
                "region": "$${ctx:region:-}",
                "errorType": "$${ctx:errorType:-}",
                "success": "$${ctx:success:-}",
                "duration": "$${ctx:duration:-}",
                "retryAttempt": "$${ctx:retryAttempt:-}",
                "logger": "$${logger}",
                "thread": "$${thread}",
                "message": "$${message}",
                "exception": "$${exception:short}"
            }
        </Property>
    </Properties>

    <Appenders>
        <!-- Console Appender with JSON format -->
        <Console name="Console" target="SYSTEM_OUT">
            <JsonTemplateLayout eventTemplateUri="classpath:EcsLayout.json"/>
        </Console>

        <!-- File Appender with JSON format -->
        <RollingFile name="FileAppender"
                     fileName="logs/cms-monitoring.log"
                     filePattern="logs/cms-monitoring-%d{yyyy-MM-dd}-%i.log.gz">
            <JsonTemplateLayout eventTemplateUri="classpath:EcsLayout.json"/>
            <Policies>
                <TimeBasedTriggeringPolicy />
                <SizeBasedTriggeringPolicy size="100MB"/>
            </Policies>
            <DefaultRolloverStrategy max="10"/>
        </RollingFile>
    </Appenders>

    <Loggers>
        <!-- Your application logger -->
        <AsyncLogger name="com.cms_monitoring_system" level="INFO" additivity="false">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="FileAppender"/>
        </AsyncLogger>

        <!-- Spring Boot loggers -->
        <Logger name="org.springframework" level="WARN"/>
        <Logger name="org.apache.http" level="WARN"/>

        <Root level="INFO">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="FileAppender"/>
        </Root>
    </Loggers>
</Configuration>

// src/main/resources/EcsLayout.json
{
  "timestamp": {
    "$resolver": "timestamp",
    "pattern": {
      "format": "yyyy-MM-dd'T'HH:mm:ss.SSSZZZ",
      "timeZone": "UTC"
    }
  },
  "level": {
    "$resolver": "level",
    "field": "name"
  },
  "traceId": {
    "$resolver": "mdc",
    "key": "traceId"
  },
  "service": "cms-monitoring-service",
  "operation": {
    "$resolver": "mdc",
    "key": "operation"
  },
  "sourceService": {
    "$resolver": "mdc",
    "key": "sourceService"
  },
  "environment": {
    "$resolver": "mdc",
    "key": "environment"
  },
  "region": {
    "$resolver": "mdc",
    "key": "region"
  },
  "errorType": {
    "$resolver": "mdc",
    "key": "errorType"
  },
  "success": {
    "$resolver": "mdc",
    "key": "success"
  },
  "duration": {
    "$resolver": "mdc",
    "key": "duration"
  },
  "retryAttempt": {
    "$resolver": "mdc",
    "key": "retryAttempt"
  },
  "logger": {
    "$resolver": "logger",
    "field": "name"
  },
  "thread": {
    "$resolver": "thread",
    "field": "name"
  },
  "message": {
    "$resolver": "message",
    "stringified": true
  },
  "exception": {
    "$resolver": "exception",
    "field": "stackTrace",
    "stackTrace": {
      "stringified": true
    }
  }
}

// TraceIdGenerator.java
package com.cms_monitoring_system.common.util;

import java.security.SecureRandom;

public class TraceIdGenerator {
    
    private static final String CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
    private static final SecureRandom RANDOM = new SecureRandom();
    
    private TraceIdGenerator() {}
    
    public static String generate() {
        // 5 chars for timestamp + 5 chars random = 10 total
        String timestampPart = encodeTimestamp(System.currentTimeMillis() / 1000, 5);
        String randomPart = generateRandomString(5);
        return timestampPart + randomPart;
    }
    
    private static String encodeTimestamp(long timestamp, int length) {
        StringBuilder result = new StringBuilder();
        long value = timestamp;
        
        for (int i = 0; i < length; i++) {
            result.insert(0, CHARSET.charAt((int) (value % CHARSET.length())));
            value /= CHARSET.length();
        }
        
        return result.toString();
    }
    
    private static String generateRandomString(int length) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < length; i++) {
            result.append(CHARSET.charAt(RANDOM.nextInt(CHARSET.length())));
        }
        return result.toString();
    }
    
    public static boolean isValidTraceId(String traceId) {
        if (traceId == null || traceId.length() != 10) {
            return false;
        }
        
        for (char c : traceId.toCharArray()) {
            if (CHARSET.indexOf(c) == -1) {
                return false;
            }
        }
        
        return true;
    }
}

// StructuredLogger.java
package com.cms_monitoring_system.common.util;

import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;

@Slf4j
public class StructuredLogger {
    
    private static final String TRACE_ID = "traceId";
    private static final String OPERATION = "operation";
    private static final String SOURCE_SERVICE = "sourceService";
    private static final String ENVIRONMENT = "environment";
    private static final String REGION = "region";
    private static final String ERROR_TYPE = "errorType";
    private static final String SUCCESS = "success";
    private static final String DURATION = "duration";
    private static final String RETRY_ATTEMPT = "retryAttempt";
    
    private StructuredLogger() {}
    
    public static void setTraceId(String traceId) {
        MDC.put(TRACE_ID, traceId);
    }
    
    public static void setRequestContext(String operation, String sourceService, 
                                       String environment, String region, String errorType) {
        MDC.put(OPERATION, operation);
        MDC.put(SOURCE_SERVICE, sourceService);
        MDC.put(ENVIRONMENT, environment);
        MDC.put(REGION, region);
        MDC.put(ERROR_TYPE, errorType);
    }
    
    public static void setSuccess(boolean success) {
        MDC.put(SUCCESS, String.valueOf(success));
    }
    
    public static void setDuration(long duration) {
        MDC.put(DURATION, String.valueOf(duration));
    }
    
    public static void setRetryAttempt(int attempt) {
        MDC.put(RETRY_ATTEMPT, String.valueOf(attempt));
    }
    
    public static void clearRetryAttempt() {
        MDC.remove(RETRY_ATTEMPT);
    }
    
    public static void clearContext() {
        MDC.clear();
    }
    
    public static void logRequestReceived(String message) {
        log.info("REQUEST_RECEIVED: {}", message);
    }
    
    public static void logOperationStart(String message) {
        log.info("OPERATION_START: {}", message);
    }
    
    public static void logOperationSuccess(String message) {
        setSuccess(true);
        log.info("OPERATION_SUCCESS: {}", message);
    }
    
    public static void logOperationFailure(String message, Exception ex) {
        setSuccess(false);
        log.error("OPERATION_FAILURE: {}", message, ex);
    }
    
    public static void logRetryAttempt(String message, int attempt) {
        setRetryAttempt(attempt);
        log.warn("RETRY_ATTEMPT: {} (attempt: {})", message, attempt);
    }
    
    public static String getTraceId() {
        return MDC.get(TRACE_ID);
    }
}

// Updated AlertController.java
package com.cms_monitoring_system.alerts.controller;

import com.cms_monitoring_system.alerts.dto.AlertRequestDto;
import com.cms_monitoring_system.alerts.service.AlertService;
import com.cms_monitoring_system.common.constants.Constants;
import com.cms_monitoring_system.common.dto.ResponseDto;
import com.cms_monitoring_system.common.util.ResponseHandler;
import com.cms_monitoring_system.common.util.StructuredLogger;
import com.cms_monitoring_system.common.util.TraceIdGenerator;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;

@RestController
@RequestMapping("/cms/monitoring")
public class AlertController {

    private final AlertService alertService;
    private static final String TRACE_ID_HEADER = "X-Trace-ID";

    public AlertController(AlertService alertService) {
        this.alertService = alertService;
    }

    @PostMapping("/alert")
    public ResponseDto raiseAlarm(@Valid @RequestBody AlertRequestDto request, 
                                 HttpServletRequest httpRequest) {
        setupTraceContext(request, httpRequest, "ALARM");
        
        long startTime = System.currentTimeMillis();
        StructuredLogger.logRequestReceived("Alarm request received");
        
        try {
            alertService.raiseAlarm(request);
            long duration = System.currentTimeMillis() - startTime;
            StructuredLogger.setDuration(duration);
            StructuredLogger.logOperationSuccess("Alarm raised successfully");
            
            return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
                Constants.SUCCESS_MESSAGE_ALARM);
        } catch (Exception ex) {
            StructuredLogger.logOperationFailure("Failed to raise alarm", ex);
            throw ex;
        } finally {
            StructuredLogger.clearContext();
        }
    }

    @PostMapping("/notification")
    public ResponseDto sendNotification(@Valid @RequestBody AlertRequestDto request,
                                      HttpServletRequest httpRequest) {
        setupTraceContext(request, httpRequest, "NOTIFICATION");
        
        long startTime = System.currentTimeMillis();
        StructuredLogger.logRequestReceived("Notification request received");
        
        try {
            alertService.sendNotification(request);
            long duration = System.currentTimeMillis() - startTime;
            StructuredLogger.setDuration(duration);
            StructuredLogger.logOperationSuccess("Notification sent successfully");
            
            return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
                Constants.SUCCESS_MESSAGE_NOTIFICATION);
        } catch (Exception ex) {
            StructuredLogger.logOperationFailure("Failed to send notification", ex);
            throw ex;
        } finally {
            StructuredLogger.clearContext();
        }
    }

    @PostMapping("/alarm")
    public ResponseDto raiseAlarmAndNotification(@Valid @RequestBody AlertRequestDto request,
                                               HttpServletRequest httpRequest) {
        setupTraceContext(request, httpRequest, "COMBINED");
        
        long startTime = System.currentTimeMillis();
        StructuredLogger.logRequestReceived("Combined alarm and notification request received");
        
        try {
            String resultMessage = alertService.raiseAlarmAndNotification(request);
            long duration = System.currentTimeMillis() - startTime;
            StructuredLogger.setDuration(duration);
            StructuredLogger.logOperationSuccess("Combined operation completed");
            
            return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY, resultMessage);
        } catch (Exception ex) {
            StructuredLogger.logOperationFailure("Failed in combined operation", ex);
            throw ex;
        } finally {
            StructuredLogger.clearContext();
        }
    }
    
    private void setupTraceContext(AlertRequestDto request, HttpServletRequest httpRequest, String operation) {
        // Get or generate trace ID
        String traceId = httpRequest.getHeader(TRACE_ID_HEADER);
        if (traceId == null || !TraceIdGenerator.isValidTraceId(traceId)) {
            traceId = TraceIdGenerator.generate();
        }
        
        StructuredLogger.setTraceId(traceId);
        StructuredLogger.setRequestContext(operation, request.getSourceService(), 
            "CURRENT_ENV", request.getRegion(), request.getErrorType());
    }
}

// Updated AlertService.java (key additions)
package com.cms_monitoring_system.alerts.service;

import com.cms_monitoring_system.alerts.dto.AlertRequestDto;
import com.cms_monitoring_system.alerts.dto.NotificationDto;
import com.cms_monitoring_system.common.constants.Constants;
import com.cms_monitoring_system.common.util.HttpMethodHandler;
import com.cms_monitoring_system.common.util.RetryUtil;
import com.cms_monitoring_system.common.util.StructuredLogger;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RequestMethod;

@Service
@Slf4j
public class AlertService {

    private final HttpMethodHandler httpMethodHandler;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${BEARER_TOKEN}")
    private String token;

    @Value("${ALMANSY_ALARM_URL}")
    private String almansyAlarmURL;

    @Value("${ALMANSY_RESOURCE_NAME}")
    private String almansyResourceName;

    @Value("${CMS_NOTIFICATION_SVR_URL}")
    private String notificationServerUrl;

    @Value("${CMS_NOTIFICATION_API}")
    private String notificationApi;

    @Value("${env}")
    private String env;

    public AlertService(HttpMethodHandler httpMethodHandler) {
        this.httpMethodHandler = httpMethodHandler;
    }

    public void raiseAlarm(AlertRequestDto request) {
        StructuredLogger.logOperationStart("Starting alarm operation");

        RetryUtil.retry(() -> {
            try {
                raiseAlarmInternal(request);
                StructuredLogger.logOperationSuccess("Alarm raised successfully");
                return true;
            } catch (Exception e) {
                StructuredLogger.logOperationFailure("Failed to raise alarm", e);
                throw new RuntimeException(e);
            }
        });
    }

    public void sendNotification(AlertRequestDto request) {
        StructuredLogger.logOperationStart("Starting notification operation");

        RetryUtil.retry(() -> {
            try {
                sendNotificationInternal(request);
                StructuredLogger.logOperationSuccess("Notification sent successfully");
                return true;
            } catch (Exception e) {
                StructuredLogger.logOperationFailure("Failed to send notification", e);
                throw new RuntimeException(e);
            }
        });
    }

    public String raiseAlarmAndNotification(AlertRequestDto request) {
        boolean alarmSuccess = false;
        boolean notificationSuccess = false;

        StructuredLogger.logOperationStart("Starting combined alarm and notification operation");

        // Try to raise alarm
        try {
            StructuredLogger.setRequestContext("ALARM", request.getSourceService(), 
                env, request.getRegion(), request.getErrorType());
            raiseAlarm(request);
            alarmSuccess = true;
            StructuredLogger.logOperationSuccess("Alarm component succeeded");
        } catch (Exception e) {
            StructuredLogger.logOperationFailure("Alarm component failed", e);
        }

        // Try to send notification
        try {
            StructuredLogger.setRequestContext("NOTIFICATION", request.getSourceService(), 
                env, request.getRegion(), request.getErrorType());
            sendNotification(request);
            notificationSuccess = true;
            StructuredLogger.logOperationSuccess("Notification component succeeded");
        } catch (Exception e) {
            StructuredLogger.logOperationFailure("Notification component failed", e);
        }

        // Reset to combined context
        StructuredLogger.setRequestContext("COMBINED", request.getSourceService(), 
            env, request.getRegion(), request.getErrorType());

        // Return appropriate message
        if (alarmSuccess && notificationSuccess) {
            StructuredLogger.logOperationSuccess("Both alarm and notification succeeded");
            return Constants.SUCCESS_MESSAGE_COMBINED;
        } else if (alarmSuccess) {
            StructuredLogger.logOperationFailure("Partial success: alarm succeeded, notification failed", null);
            return Constants.PARTIAL_SUCCESS_MESSAGE + "Alarm raised, notification failed";
        } else if (notificationSuccess) {
            StructuredLogger.logOperationFailure("Partial success: notification succeeded, alarm failed", null);
            return Constants.PARTIAL_SUCCESS_MESSAGE + "Notification sent, alarm failed";
        } else {
            StructuredLogger.logOperationFailure("Both alarm and notification failed", null);
            return "Both alarm and notification failed";
        }
    }

    // Rest of the methods remain the same...
    // (raiseAlarmInternal, sendNotificationInternal, callArgusAlarm)
}

// Updated AlertRequestDto.java with validation
package com.cms_monitoring_system.alerts.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertRequestDto {

    @NotNull(message = "Source service cannot be null")
    @NotBlank(message = "Source service cannot be empty")
    private String sourceService;

    @NotNull(message = "Region cannot be null")
    @NotBlank(message = "Region cannot be empty")
    private String region;

    @NotNull(message = "Error message cannot be null")
    @NotBlank(message = "Error message cannot be empty")
    private String errorMessage;

    @NotNull(message = "Error type cannot be null")
    @NotBlank(message = "Error type cannot be empty")
    private String errorType;
}