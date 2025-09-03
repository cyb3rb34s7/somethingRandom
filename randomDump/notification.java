// Constants.java
package com.cms.monitoring.common.constants;

public class Constants {
    public static final String METHOD_POST = "POST";
    public static final String RESPONSE_KEY = "response";
    public static final String SUCCESS_MESSAGE_ALARM = "Alarm raised successfully";
    public static final String SUCCESS_MESSAGE_NOTIFICATION = "Notification sent successfully";
    public static final String SUCCESS_MESSAGE_COMBINED = "Alarm and notification processed successfully";
    public static final String PARTIAL_SUCCESS_MESSAGE = "Partial success: ";
    
    // Alarm Constants
    public static final String ARGUS_FAIL_ALERT = "FAIL";
    public static final String TRIGGER_MANUAL = "manual";
    public static final String TYPE_ALARM = "alarm";
    public static final String COMPONENT_TVPLUS_CMS = "TVPLUS_CMS";
    public static final String RESOURCE_VENDOR_AWS = "AWS";
    public static final String RESOURCE_TYPE_ECS = "ECS";
    public static final int ALARM_VALUE = 0;
    public static final int ALARM_THRESHOLD = 90;
    public static final String TASK_DESC_EXCEPTION = "Exception";
    
    private Constants() {}
}

// MonitoringRequest.java
package com.cms.monitoring.monitoring.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MonitoringRequest {
    private String sourceService;
    private String environment;
    private String region;
    private String errorMessage;
    private String errorType;
}

// ResponseDto.java
package com.cms.monitoring.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResponseDto {
    private String response;
    private String message;
}

// ResponseHandler.java
package com.cms.monitoring.common.util;

import com.cms.monitoring.common.model.ResponseDto;

public class ResponseHandler {
    
    private ResponseHandler() {}
    
    public static ResponseDto processMethodResponse(String responseKey, String message) {
        return ResponseDto.builder()
            .response(responseKey)
            .message(message)
            .build();
    }
}

// NotificationDto.java
package com.cms.monitoring.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationDto {
    private String messageSub;
    private String message;
}

// RetryUtil.java
package com.cms.monitoring.common.util;

import com.cms.monitoring.common.exception.CustomException;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class RetryUtil {

    private static final int MAX_RETRIES = 3;
    private static final long RETRY_DELAY_MS = 1000;

    private RetryUtil() {
    }

    public static <T> T retry(Supplier<T> supplier) {
        int retries = 0;
        while (retries < MAX_RETRIES) {
            try {
                return supplier.get();
            } catch (Exception e) {
                log.error("Error Occurred. Retrying...:{}", retries, e);
                retries++;
                try {
                    TimeUnit.MILLISECONDS.sleep(RETRY_DELAY_MS);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    log.error("Retry interrupted.", ie);
                }
            }
        }

        log.error("Failed after {} retries.", MAX_RETRIES);
        throw new CustomException("Failed after " + MAX_RETRIES + " retries.");
    }
}

// CustomException.java
package com.cms.monitoring.common.exception;

public class CustomException extends RuntimeException {
    public CustomException(String message) {
        super(message);
    }
}

// MonitoringController.java
package com.cms.monitoring.monitoring.controller;

import com.cms.monitoring.common.constants.Constants;
import com.cms.monitoring.common.model.ResponseDto;
import com.cms.monitoring.common.util.ResponseHandler;
import com.cms.monitoring.monitoring.model.MonitoringRequest;
import com.cms.monitoring.monitoring.service.MonitoringService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/cms/monitoring")
public class MonitoringController {

    private final MonitoringService monitoringService;

    public MonitoringController(MonitoringService monitoringService) {
        this.monitoringService = monitoringService;
    }

    @PostMapping("/alarm")
    public ResponseDto raiseAlarm(@RequestBody MonitoringRequest request) {
        monitoringService.raiseAlarm(request);
        return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
            Constants.SUCCESS_MESSAGE_ALARM);
    }

    @PostMapping("/notification")
    public ResponseDto sendNotification(@RequestBody MonitoringRequest request) {
        monitoringService.sendNotification(request);
        return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
            Constants.SUCCESS_MESSAGE_NOTIFICATION);
    }

    @PostMapping("/alert")
    public ResponseDto raiseAlarmAndNotification(@RequestBody MonitoringRequest request) {
        String resultMessage = monitoringService.raiseAlarmAndNotification(request);
        return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY, resultMessage);
    }
}

// MonitoringService.java
package com.cms.monitoring.monitoring.service;

import com.cms.monitoring.common.constants.Constants;
import com.cms.monitoring.common.model.NotificationDto;
import com.cms.monitoring.common.util.HttpMethodHandler;
import com.cms.monitoring.common.util.RetryUtil;
import com.cms.monitoring.monitoring.model.MonitoringRequest;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RequestMethod;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
public class MonitoringService {

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

    public MonitoringService(HttpMethodHandler httpMethodHandler) {
        this.httpMethodHandler = httpMethodHandler;
    }

    public void raiseAlarm(MonitoringRequest request) {
        log.info("Raising alarm for source: {} with error: {}", 
            request.getSourceService(), request.getErrorMessage());
        
        RetryUtil.retry(() -> {
            try {
                raiseAlarmInternal(request);
                return true;
            } catch (Exception e) {
                log.error("Failed to raise alarm", e);
                throw new RuntimeException(e);
            }
        });
    }

    public void sendNotification(MonitoringRequest request) {
        log.info("Sending notification for source: {} with error: {}", 
            request.getSourceService(), request.getErrorMessage());
        
        RetryUtil.retry(() -> {
            try {
                sendNotificationInternal(request);
                return true;
            } catch (Exception e) {
                log.error("Failed to send notification", e);
                throw new RuntimeException(e);
            }
        });
    }

    public String raiseAlarmAndNotification(MonitoringRequest request) {
        boolean alarmSuccess = false;
        boolean notificationSuccess = false;
        
        // Try to raise alarm
        try {
            raiseAlarm(request);
            alarmSuccess = true;
            log.info("Alarm raised successfully for source: {}", request.getSourceService());
        } catch (Exception e) {
            log.error("Failed to raise alarm for source: {}", request.getSourceService(), e);
        }
        
        // Try to send notification
        try {
            sendNotification(request);
            notificationSuccess = true;
            log.info("Notification sent successfully for source: {}", request.getSourceService());
        } catch (Exception e) {
            log.error("Failed to send notification for source: {}", request.getSourceService(), e);
        }
        
        // Return appropriate message
        if (alarmSuccess && notificationSuccess) {
            return Constants.SUCCESS_MESSAGE_COMBINED;
        } else if (alarmSuccess) {
            return Constants.PARTIAL_SUCCESS_MESSAGE + "Alarm raised, notification failed";
        } else if (notificationSuccess) {
            return Constants.PARTIAL_SUCCESS_MESSAGE + "Notification sent, alarm failed";
        } else {
            return "Both alarm and notification failed";
        }
    }

    private void raiseAlarmInternal(MonitoringRequest request) throws JsonProcessingException {
        String title = "Exception in " + request.getSourceService();
        String description = request.getErrorMessage();
        
        log.info("Raising Argus Alarm for {} with description {}", title, description);
        
        ObjectNode payload = objectMapper.createObjectNode();
        payload.put("trigger", Constants.TRIGGER_MANUAL);
        payload.put("type", Constants.TYPE_ALARM);
        payload.put("component", Constants.COMPONENT_TVPLUS_CMS);
        payload.put("stage", request.getEnvironment());
        payload.put("timestamp", Instant.now().toString());

        ObjectNode source = payload.putObject("source");
        source.put("resourceName", almansyResourceName);
        source.put("region", request.getRegion());
        source.put("resourceVendor", Constants.RESOURCE_VENDOR_AWS);
        source.put("resourceType", Constants.RESOURCE_TYPE_ECS);

        ObjectNode snippet = payload.putObject("snippet");
        snippet.put("detectionSystem", request.getSourceService());
        snippet.put("alertKind", Constants.ARGUS_FAIL_ALERT);
        snippet.put("value", Constants.ALARM_VALUE);
        snippet.put("threshold", Constants.ALARM_THRESHOLD);
        snippet.put("title", title);
        snippet.put("description", description);

        Map<String, String> headers = new HashMap<>();
        headers.put("Accept", "application/json");
        headers.put("Content-Type", "application/json");
        headers.put("Authorization", "Bearer " + token);

        String jsonPayload = objectMapper.writeValueAsString(payload);

        callArgusAlarm(RequestMethod.POST, almansyAlarmURL, headers, jsonPayload);
    }

    private void sendNotificationInternal(MonitoringRequest request) {
        String messageSub = request.getEnvironment().toUpperCase() + "-Error-In-" + request.getSourceService();
        String message = request.getErrorType() + " :: " + request.getErrorMessage();
        
        NotificationDto notification = NotificationDto.builder()
            .messageSub(messageSub)
            .message(message)
            .build();

        try {
            httpMethodHandler.handleHttpExchange(
                notificationServerUrl + notificationApi,
                Constants.METHOD_POST,
                new HttpEntity<>(notification),
                ResponseEntity.class
            );
            log.info("Notification: Mail successfully sent");
        } catch (Exception ex) {
            log.error("Notification Error: Error in sending mail", ex);
            throw ex;
        }
    }

    private void callArgusAlarm(RequestMethod method, String almansyURL,
                               Map<String, String> header, String body) {
        HttpHeaders headers = new HttpHeaders();
        header.forEach(headers::set);
        try {
            httpMethodHandler.handleHttpExchange(almansyURL,
                String.valueOf(method), new HttpEntity<>(body, headers),
                String.class);
        } catch (Exception e) {
            log.error("Error while calling argus alarm", e);
            throw e;
        }
    }
}