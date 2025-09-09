# CMS Monitoring System - Project Context

## 🎯 Project Overview

A comprehensive monitoring and alerting system consisting of a **Spring Boot backend service** and **React dashboard frontend** for centralizing error monitoring across CMS services.

### Purpose
- **Centralize monitoring**: Replace scattered alarm/notification utilities across multiple services
- **Unified alerting**: Single API for raising alarms (Argus) and sending notifications (email)
- **Visual dashboard**: Beautiful UI to view logs, analytics, and generate reports
- **CloudWatch integration**: Future integration with AWS CloudWatch for log aggregation

---

## 🏗️ Backend Architecture (Spring Boot)

### Service Purpose
Centralized monitoring service that exposes REST APIs for:
1. **Alarm-only**: `/cms/monitoring/alarm` - Raises alarm via Argus API
2. **Notification-only**: `/cms/monitoring/notification` - Sends email notifications  
3. **Combined**: `/cms/monitoring/alert` - Raises both alarm and notification

### Key Features
- **Structured JSON logging** (Log4j2 with console output only for containers)
- **TraceId tracking** (10-char format: 5 timestamp + 5 random characters)
- **Retry mechanism** with exponential backoff
- **Field validation** using Bean Validation
- **Dynamic source service identification**

### Technology Stack
```gradle
- Spring Boot 3.4.5
- Java 17
- Log4j2 (JSON structured logging)
- Spring Validation
- Spring Retry
- Lombok
- HttpClient5
```

### Request/Response Structure
**Request DTO:**
```json
{
  "sourceService": "CMS-ADMIN",
  "region": "US_REGION", 
  "errorMessage": "Database connection timeout",
  "errorType": "INTERNAL_SERVER_ERROR"
}
```

**Log Output Examples:**
```json
{"timestamp":"2025-09-09T10:30:15.123Z","level":"INFO","traceId":"A1B2Cx7k9m","service":"cms-monitoring-service","operation":"ALARM_REQUEST","sourceService":"CMS-ADMIN","environment":"PROD","region":"US_REGION","errorType":"INTERNAL_SERVER_ERROR","errorMessage":"Database connection timeout","message":"Alarm request received"}

{"timestamp":"2025-09-09T10:30:15.456Z","level":"INFO","traceId":"A1B2Cx7k9m","service":"cms-monitoring-service","operation":"ALARM_ATTEMPT","sourceService":"CMS-ADMIN","success":true,"duration":150,"message":"Alarm attempt completed successfully"}
```

### Log Structure & Operations
**Request Types:**
- `ALARM_REQUEST` - /alarm endpoint (raises both alarm + notification)  
- `NOTIFICATION_REQUEST` - /notification endpoint (notification only)

**Operation Types:**
- `ALARM_ATTEMPT` - Actual Argus alarm API call
- `NOTIFICATION_ATTEMPT` - Actual notification service call

**Log Flow Example:**
1. `/alarm` → `ALARM_REQUEST` (controller)
2. → `ALARM_ATTEMPT` (service operation) 
3. → `NOTIFICATION_ATTEMPT` (service operation)

### Current Status
✅ Backend service is implemented and ready
✅ Structured logging configured
✅ Container-ready (no file logging, stdout only)

---

## 🎨 Frontend Architecture (React Dashboard)

### Purpose
Modern monitoring dashboard to visualize logs, metrics, and system health with the ability to:
- View real-time log streams
- Analyze error trends and service health
- Generate weekly error reports  
- Search and filter logs
- Display beautiful charts and analytics

### Technology Stack
```json
{
  "core": ["React 19", "TypeScript", "Vite"],
  "styling": ["Tailwind CSS v4", "ShadCN UI", "Lucide Icons"],
  "routing": ["React Router DOM"],
  "charts": ["Recharts"],
  "http": ["Axios"],
  "utils": ["date-fns", "clsx", "tailwind-merge"]
}
```

### Design Philosophy
- **Modern & Professional**: Clean, corporate monitoring dashboard aesthetic
- **Smooth Transitions**: Fade-in animations, slide-in sidebar, hover effects
- **Responsive Design**: Mobile-first approach with responsive layouts
- **Dark Mode Ready**: Built-in dark theme support
- **Glass Effects**: Modern UI patterns with backdrop-blur
- **Accessibility**: Proper contrast, semantic markup

### UI Layout Structure

#### 🎛️ **Sidebar Navigation**
```
🏠 Overview Dashboard    - Main metrics, charts, system overview
📊 Analytics            - Deep-dive performance insights  
🔍 Logs Explorer        - Searchable, filterable log viewer
📋 Reports              - Weekly/monthly report generation
⚙️ Service Health       - Individual service status monitoring
🔧 Settings             - Configuration and preferences
```

#### 📱 **Header Components**
- **Time Range Selector**: 1h, 6h, 24h, 7d, 30d
- **Refresh Button**: Manual data refresh
- **Notifications**: Alert badge with count
- **Current Time**: Live clock display
- **Page Title & Subtitle**: Dynamic based on current page

### Page Specifications

#### 1. **Overview Dashboard** (`/`)
**Purpose**: Real-time system health and key metrics
**Components**:
- **Metrics Cards**: Total requests, alarm success rate, notification success rate, avg response time
- **Timeline Chart**: 24-hour request/error trends (Recharts line chart)
- **Service Status Cards**: Health indicators for each CMS service
- **Recent Errors**: Latest error entries with trace IDs

#### 2. **Analytics Dashboard** (`/analytics`) 
**Purpose**: Performance insights and trend analysis
**Components**:
- **Request Type Distribution**: Pie chart (ALARM_REQUEST vs NOTIFICATION_REQUEST)
- **Success Rate Trends**: Multi-line charts for alarm vs notification success
- **Error Type Analysis**: Bar chart of most common error types
- **Service Performance**: Response time distributions by service
- **Retry Analysis**: Frequency and success rate of retry attempts

#### 3. **Logs Explorer** (`/logs`)
**Purpose**: Search, filter, and view system logs
**Components**:
- **Advanced Filters**: Service selector, time range, log level, operation type
- **Search Box**: Free-text search across log messages
- **Data Table**: Paginated logs with sortable columns
- **Log Detail Modal**: Expanded view with full trace information
- **Export Options**: CSV/JSON export functionality

#### 4. **Reports** (`/reports`)
**Purpose**: Generate and download automated reports
**Components**:
- **Report Generator**: Date range picker, service selector, template chooser
- **Report Templates**: Error summary, performance summary, service health
- **Download Options**: PDF (executive), Excel (detailed), CSV (raw data)
- **Scheduled Reports**: Future feature for automatic report generation
- **Report History**: Previously generated reports

#### 5. **Service Health** (`/health`) - Future
**Purpose**: Individual service monitoring and alerting
**Components**:
- **Service Overview**: Status indicators, uptime percentages
- **Error Rate Monitoring**: Configurable thresholds and alerts
- **Performance Metrics**: P95, P99 response times
- **Dependency Health**: Status of downstream services (Argus, notification)

### Mock Data Strategy

#### 📋 **Mock Logs** (`mockLogs.ts`)
- 15 realistic log entries with various scenarios
- Proper traceId grouping (request → attempts)
- Different source services, error types, environments
- Success/failure cases with retry attempts
- Helper functions for filtering and statistics

#### 📊 **Mock Metrics** (`mockMetrics.ts`) 
- Dashboard KPI cards with trend indicators
- 24-hour timeline data for charts
- Service health status with uptime/performance metrics
- Error type distribution data for pie charts
- Realistic numbers and percentages

### Development Approach

#### **Phase 1: Mock Data Development** ✅
- Build complete UI with realistic mock data
- Perfect the design, animations, and user experience
- Test all components and interactions
- Ensure responsive design works across devices

#### **Phase 2: Backend Integration** 🔄
- Replace mock data with AWS CloudWatch API calls
- Implement real-time log fetching
- Add authentication and authorization
- Error handling and loading states

#### **Phase 3: Advanced Features** 📈
- Real-time WebSocket updates
- Advanced analytics and alerting
- Report scheduling and automation
- User management and team features

### Color Palette & Theme
```css
/* Primary monitoring colors */
--primary: #0ea5e9 (blue)
--success: #22c55e (green)  
--warning: #f59e0b (amber)
--error: #ef4444 (red)

/* Professional grays */
--background: #ffffff
--card: #f8fafc  
--muted: #64748b
--border: #e2e8f0
```

### Animation Specifications
- **Page Transitions**: 300ms fade-in with slight vertical translation
- **Sidebar**: Slide-in animation from left
- **Hover Effects**: Subtle elevation and shadow changes
- **Loading States**: Skeleton loaders instead of spinners
- **Chart Animations**: Progressive data reveals
- **Status Indicators**: Pulse animations for active states

---

## 🔄 Integration Architecture

### Current Flow
```
CMS Services → Monitoring Backend → Structured Logs → Console/CloudWatch
                                 ↓
                         React Dashboard (Mock Data)
```

### Future Flow  
```
CMS Services → Monitoring Backend → CloudWatch Logs
                                        ↓
                              React Dashboard ← AWS SDK
                                        ↓
                              Report Generation (PDF/Excel)
```

### CloudWatch Integration Plan
- **AWS SDK**: Use CloudWatch Logs API to fetch log data
- **Structured Queries**: Leverage JSON log format for efficient filtering
- **Batch Processing**: Aggregate data for analytics and reports
- **Cost Optimization**: Smart caching and query optimization

---

## 🚀 Current Status & Next Steps

### ✅ **Completed**
- Backend monitoring service (Spring Boot)
- Structured JSON logging with traceId
- Frontend project setup (Vite + React + Tailwind + ShadCN)
- Mock data structure (logs + metrics)
- Layout system (Sidebar + Header + Routing)

### 🔄 **In Progress**  
- Completing ShadCN UI configuration
- Building Overview Dashboard with charts
- Implementing responsive design

### 📋 **Next Priorities**
1. **Complete UI Components**: Metric cards, charts, data tables
2. **Logs Explorer**: Advanced filtering and search functionality  
3. **Reports Module**: PDF/Excel generation capabilities
4. **CloudWatch Integration**: Replace mock data with real API calls
5. **Deployment**: Container deployment with proper configurations

---

## 📝 Development Notes

### Key Decisions Made
- **Container-friendly logging**: Console output only, no file logging
- **TraceId format**: 10-character (5 timestamp + 5 random) for readability
- **CSS-first Tailwind v4**: Modern configuration approach
- **Mock-first development**: Perfect UI before backend integration
- **ShadCN UI**: Component library for consistent, professional design

### Architecture Principles
- **Separation of Concerns**: Clean backend API, independent frontend
- **Scalability**: Designed to handle multiple CMS services
- **Maintainability**: Structured logging, proper error handling
- **User Experience**: Modern, intuitive dashboard interface
- **Performance**: Efficient data fetching, smart caching strategies

This context serves as the complete project checkpoint for continuing development in any new session.