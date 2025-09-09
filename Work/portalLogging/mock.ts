// src/data/mockLogs.ts

export interface LogEntry {
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR";
  traceId: string;
  service: string;
  operation: "ALARM_REQUEST" | "NOTIFICATION_REQUEST" | "ALARM_ATTEMPT" | "NOTIFICATION_ATTEMPT";
  sourceService: string;
  environment: string;
  region: string;
  errorType: string;
  errorMessage: string;
  success?: boolean;
  duration?: number;
  retryAttempt?: number;
  message: string;
}

export const mockLogs: LogEntry[] = [
  {
    timestamp: "2025-09-09T10:30:15.123Z",
    level: "INFO",
    traceId: "A1B2Cx7k9m",
    service: "cms-monitoring-service",
    operation: "ALARM_REQUEST",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Database connection timeout during user authentication",
    message: "Alarm request received"
  },
  {
    timestamp: "2025-09-09T10:30:15.456Z",
    level: "INFO",
    traceId: "A1B2Cx7k9m",
    service: "cms-monitoring-service",
    operation: "ALARM_ATTEMPT",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Database connection timeout during user authentication",
    success: true,
    duration: 150,
    message: "Alarm attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T10:30:15.789Z",
    level: "INFO",
    traceId: "A1B2Cx7k9m",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_ATTEMPT",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Database connection timeout during user authentication",
    success: true,
    duration: 230,
    message: "Notification attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T10:45:22.334Z",
    level: "INFO",
    traceId: "X9Y8Z7W6V5",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_REQUEST",
    sourceService: "CMS-HISTORY",
    environment: "PROD",
    region: "US_REGION",
    errorType: "BAD_REQUEST",
    errorMessage: "Invalid content ID format in request payload",
    message: "Notification request received"
  },
  {
    timestamp: "2025-09-09T10:45:22.567Z",
    level: "INFO",
    traceId: "X9Y8Z7W6V5",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_ATTEMPT",
    sourceService: "CMS-HISTORY",
    environment: "PROD",
    region: "US_REGION",
    errorType: "BAD_REQUEST",
    errorMessage: "Invalid content ID format in request payload",
    success: true,
    duration: 95,
    message: "Notification attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T11:15:33.445Z",
    level: "ERROR",
    traceId: "M4N5P6Q7R8",
    service: "cms-monitoring-service",
    operation: "ALARM_REQUEST",
    sourceService: "CMS-API",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Redis cache unavailable - connection refused",
    message: "Alarm request received"
  },
  {
    timestamp: "2025-09-09T11:15:33.678Z",
    level: "ERROR",
    traceId: "M4N5P6Q7R8",
    service: "cms-monitoring-service",
    operation: "ALARM_ATTEMPT",
    sourceService: "CMS-API",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Redis cache unavailable - connection refused",
    success: false,
    retryAttempt: 3,
    message: "Alarm attempt failed after retries"
  },
  {
    timestamp: "2025-09-09T11:15:34.012Z",
    level: "WARN",
    traceId: "M4N5P6Q7R8",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_ATTEMPT",
    sourceService: "CMS-API",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "Redis cache unavailable - connection refused",
    success: true,
    duration: 445,
    message: "Notification attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T11:30:45.123Z",
    level: "INFO",
    traceId: "K2L3M4N5P6",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_REQUEST",
    sourceService: "CMS-WORKER",
    environment: "STAGING",
    region: "EU_REGION",
    errorType: "TIMEOUT_ERROR",
    errorMessage: "External API call timeout after 30 seconds",
    message: "Notification request received"
  },
  {
    timestamp: "2025-09-09T11:30:45.456Z",
    level: "WARN",
    traceId: "K2L3M4N5P6",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_ATTEMPT",
    sourceService: "CMS-WORKER",
    environment: "STAGING",
    region: "EU_REGION",
    errorType: "TIMEOUT_ERROR",
    errorMessage: "External API call timeout after 30 seconds",
    success: true,
    duration: 890,
    retryAttempt: 2,
    message: "Notification attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T12:00:12.789Z",
    level: "INFO",
    traceId: "F7G8H9J0K1",
    service: "cms-monitoring-service",
    operation: "ALARM_REQUEST",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "VALIDATION_ERROR",
    errorMessage: "Missing required field: user_id in request body",
    message: "Alarm request received"
  },
  {
    timestamp: "2025-09-09T12:00:13.012Z",
    level: "INFO",
    traceId: "F7G8H9J0K1",
    service: "cms-monitoring-service",
    operation: "ALARM_ATTEMPT",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "VALIDATION_ERROR",
    errorMessage: "Missing required field: user_id in request body",
    success: true,
    duration: 120,
    message: "Alarm attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T12:00:13.345Z",
    level: "INFO",
    traceId: "F7G8H9J0K1",
    service: "cms-monitoring-service",
    operation: "NOTIFICATION_ATTEMPT",
    sourceService: "CMS-ADMIN",
    environment: "PROD",
    region: "US_REGION",
    errorType: "VALIDATION_ERROR",
    errorMessage: "Missing required field: user_id in request body",
    success: true,
    duration: 178,
    message: "Notification attempt completed successfully"
  },
  {
    timestamp: "2025-09-09T12:15:25.567Z",
    level: "ERROR",
    traceId: "T5U6V7W8X9",
    service: "cms-monitoring-service",
    operation: "ALARM_REQUEST",
    sourceService: "CMS-HISTORY",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "OutOfMemoryError: Java heap space exceeded during large query processing",
    message: "Alarm request received"
  },
  {
    timestamp: "2025-09-09T12:15:25.890Z",
    level: "ERROR",
    traceId: "T5U6V7W8X9",
    service: "cms-monitoring-service",
    operation: "ALARM_ATTEMPT",
    sourceService: "CMS-HISTORY",
    environment: "PROD",
    region: "US_REGION",
    errorType: "INTERNAL_SERVER_ERROR",
    errorMessage: "OutOfMemoryError: Java heap space exceeded during large query processing",
    success: true,
    duration: 89,
    message: "Alarm attempt completed successfully"
  }
];

// Helper functions for filtering and processing logs
export const getLogsByLevel = (level: LogEntry['level']) => {
  return mockLogs.filter(log => log.level === level);
};

export const getLogsBySourceService = (sourceService: string) => {
  return mockLogs.filter(log => log.sourceService === sourceService);
};

export const getLogsByOperation = (operation: LogEntry['operation']) => {
  return mockLogs.filter(log => log.operation === operation);
};

export const getLogsByTraceId = (traceId: string) => {
  return mockLogs.filter(log => log.traceId === traceId);
};

export const getLogsByTimeRange = (startTime: string, endTime: string) => {
  return mockLogs.filter(log => 
    log.timestamp >= startTime && log.timestamp <= endTime
  );
};

// Statistics helpers
export const getLogStats = () => {
  const total = mockLogs.length;
  const byLevel = {
    INFO: getLogsByLevel('INFO').length,
    WARN: getLogsByLevel('WARN').length,
    ERROR: getLogsByLevel('ERROR').length,
  };
  
  const byOperation = {
    ALARM_REQUEST: getLogsByOperation('ALARM_REQUEST').length,
    NOTIFICATION_REQUEST: getLogsByOperation('NOTIFICATION_REQUEST').length,
    ALARM_ATTEMPT: getLogsByOperation('ALARM_ATTEMPT').length,
    NOTIFICATION_ATTEMPT: getLogsByOperation('NOTIFICATION_ATTEMPT').length,
  };

  const bySourceService = {
    'CMS-ADMIN': getLogsBySourceService('CMS-ADMIN').length,
    'CMS-HISTORY': getLogsBySourceService('CMS-HISTORY').length,
    'CMS-API': getLogsBySourceService('CMS-API').length,
    'CMS-WORKER': getLogsBySourceService('CMS-WORKER').length,
  };

  const successRate = mockLogs
    .filter(log => log.success !== undefined)
    .reduce((acc, log) => acc + (log.success ? 1 : 0), 0) / 
    mockLogs.filter(log => log.success !== undefined).length * 100;

  return {
    total,
    byLevel,
    byOperation,
    bySourceService,
    successRate: Math.round(successRate * 100) / 100
  };
};