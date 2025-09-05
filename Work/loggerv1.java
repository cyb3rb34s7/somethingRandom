// Updated AlertController.java methods

@PostMapping("/alert")
public ResponseDto raiseAlarm(@Valid @RequestBody AlertRequestDto request, 
                             HttpServletRequest httpRequest) {
    setupTraceContext(request, httpRequest);
    alertService.setupRequestContext("ALARM_REQUEST", request);
    
    long startTime = System.currentTimeMillis();
    StructuredLogger.logRequestReceived("Alarm request received");
    
    alertService.raiseAlarm(request);
    
    long duration = System.currentTimeMillis() - startTime;
    StructuredLogger.setDuration(duration);
    
    return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
        Constants.SUCCESS_MESSAGE_ALARM);
}

@PostMapping("/notification")
public ResponseDto sendNotification(@Valid @RequestBody AlertRequestDto request,
                                  HttpServletRequest httpRequest) {
    setupTraceContext(request, httpRequest);
    alertService.setupRequestContext("NOTIFICATION_REQUEST", request);
    
    long startTime = System.currentTimeMillis();
    StructuredLogger.logRequestReceived("Notification request received");
    
    alertService.sendNotification(request);
    
    long duration = System.currentTimeMillis() - startTime;
    StructuredLogger.setDuration(duration);
    
    return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY,
        Constants.SUCCESS_MESSAGE_NOTIFICATION);
}

@PostMapping("/alarm")
public ResponseDto raiseAlarmAndNotification(@Valid @RequestBody AlertRequestDto request,
                                           HttpServletRequest httpRequest) {
    setupTraceContext(request, httpRequest);
    alertService.setupRequestContext("ALARM_REQUEST", request);
    
    long startTime = System.currentTimeMillis();
    StructuredLogger.logRequestReceived("Combined alarm and notification request received");
    
    String resultMessage = alertService.raiseAlarmAndNotification(request);
    
    long duration = System.currentTimeMillis() - startTime;
    StructuredLogger.setDuration(duration);
    
    return ResponseHandler.processMethodResponse(Constants.RESPONSE_KEY, resultMessage);
}

private void setupTraceContext(AlertRequestDto request, HttpServletRequest httpRequest) {
    // Get or generate trace ID
    String traceId = httpRequest.getHeader(TRACE_ID_HEADER);
    if (traceId == null || !TraceIdGenerator.isValidTraceId(traceId)) {
        traceId = TraceIdGenerator.generate();
    }
    StructuredLogger.setTraceId(traceId);
}

// Updated AlertService.java methods

public void setupRequestContext(String operation, AlertRequestDto request) {
    StructuredLogger.setRequestContext(operation, request.getSourceService(), 
        env, request.getRegion(), request.getErrorType(), request.getErrorMessage());
}

public void raiseAlarm(AlertRequestDto request) {
    // Set operation context for alarm attempt
    StructuredLogger.setRequestContext("ALARM_ATTEMPT", request.getSourceService(), 
        env, request.getRegion(), request.getErrorType(), request.getErrorMessage());
    
    // RetryUtil will log each attempt, we just call it
    RetryUtil.retry(() -> {
        raiseAlarmInternal(request);
        return true;
    });
    
    // Log final success
    StructuredLogger.logOperationSuccess("Alarm attempt completed successfully");
}

public void sendNotification(AlertRequestDto request) {
    // Set operation context for notification attempt
    StructuredLogger.setRequestContext("NOTIFICATION_ATTEMPT", request.getSourceService(), 
        env, request.getRegion(), request.getErrorType(), request.getErrorMessage());
    
    // RetryUtil will log each attempt, we just call it
    RetryUtil.retry(() -> {
        sendNotificationInternal(request);
        return true;
    });
    
    // Log final success
    StructuredLogger.logOperationSuccess("Notification attempt completed successfully");
}

public String raiseAlarmAndNotification(AlertRequestDto request) {
    boolean alarmSuccess = false;
    boolean notificationSuccess = false;

    // Try to raise alarm
    try {
        raiseAlarm(request);
        alarmSuccess = true;
    } catch (Exception e) {
        log.error("Alarm component failed for source: {}", request.getSourceService(), e);
    }

    // Try to send notification
    try {
        sendNotification(request);
        notificationSuccess = true;
    } catch (Exception e) {
        log.error("Notification component failed for source: {}", request.getSourceService(), e);
    }

    // Return appropriate message based on results
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

// Updated RetryUtil.java to include success logging

public static <T> T retry(Supplier<T> supplier) {
    int retries = 0;
    while (retries < MAX_RETRIES) {
        try {
            T result = supplier.get();
            // Log success (will show retry attempt number if retries happened)
            if (retries > 0) {
                log.info("Operation succeeded on retry attempt: {}", retries + 1);
            } else {
                log.info("Operation succeeded on first attempt");
            }
            return result;
        } catch (Exception e) {
            retries++;
            log.error("Error occurred. Retry attempt: {}", retries, e);
            
            if (retries >= MAX_RETRIES) {
                log.error("Failed after {} retries.", MAX_RETRIES);
                throw new CustomException("Failed after " + MAX_RETRIES + " retries.");
            }
            
            try {
                TimeUnit.MILLISECONDS.sleep(RETRY_DELAY_MS);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                log.error("Retry interrupted.", ie);
                throw new CustomException("Retry interrupted");
            }
        }
    }
    
    throw new CustomException("Failed after " + MAX_RETRIES + " retries.");
}

// Add to StructuredLogger.java

public static void setRequestContext(String operation, String sourceService, 
                                   String environment, String region, String errorType, String errorMessage) {
    MDC.put(OPERATION, operation);
    MDC.put(SOURCE_SERVICE, sourceService);
    MDC.put(ENVIRONMENT, environment);
    MDC.put(REGION, region);
    MDC.put(ERROR_TYPE, errorType);
    MDC.put(ERROR_MESSAGE, errorMessage);
}