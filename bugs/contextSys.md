# CMS Admin Portal - System Context and Requirements

## Overview

This document provides complete context about the CMS Admin Portal system, including current architecture, data structures, authentication flow, and requirements for the user name resolution feature. This information is intended for use by AI agents or architects to evaluate different architectural approaches.

## System Architecture

### Admin Backend

- **Technology Stack**: Java Spring Boot application
- **Database**: Relational database (likely MySQL/PostgreSQL)
- **Deployment**: Multiple container instances (5+ containers in production)
- **Authentication**: Integrated with IMS (Identity Management System)
- **Services**: Monolithic application handling all admin functions

### Admin Frontend

- **Technology Stack**: Angular application
- **Communication**: REST API calls to backend services
- **User Interface**: Web-based admin portal for content management
- **User Experience**: Requires fast response times for all interactions

## Current Data Storage Structure

### User Management Tables

#### cms_adm_user Table

Based on the `UserDetailsDto` class, the user data stored in the database includes:

- `userId`: System-generated UUID
- `guid`: IMS GUID (Global Unique Identifier)
- `userName`: Full name (First + Last) - TO BE REMOVED
- `emailId`: User's email address
- `superAdmin`: Flag indicating if user is a super admin
- `regrId`: User who registered this user
- `regrDate`: Registration date
- `reqDate`: Request date for approval
- `mdfrId`: User who last modified
- `approverUserName`: Name of approver
- `approverEmailId`: Email of approver
- `roleId`: Role identifier
- `roleName`: Role name
- `status`: User status
- `comment`: Approval comments
- `avatarUrl`: URL to user's avatar
- `prefCountryCodes`: Preferred country codes
- `prefUSCountryCodes`: Preferred US country codes
- `prefEUCountryCodes`: Preferred EU country codes
- `isSuperUser`: Flag indicating if user is super user
- `prefRegion`: Preferred region
- `appVersion`: Application version

#### Example Data in cms_adm_user

| userId                                 | guid                | userName     | emailId                  | superAdmin | status   |
| -------------------------------------- | ------------------- | ------------ | ------------------------ | ---------- | -------- |
| "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8" | "user-123-ims-guid" | "John Doe"   | "john.doe@company.com"   | false      | "Active" |
| "b2c3d4e5-f6g7-8901-h2i3-j4k5l6m7n8o9" | "user-456-ims-guid" | "Jane Smith" | "jane.smith@company.com" | true       | "Active" |

### History Tables

#### User History Table

- Stores user-related actions and changes
- Contains `user_id` fields that need user name resolution
- Millions of records in production

#### Asset Change History Tables

- Stores asset modification history
- Contains `updated_by` fields with user IDs
- Requires user name display in UI

## Authentication Flow

### Current Authentication Process

1. **User Access**: User navigates to admin portal
2. **IMS Redirect**: User redirected to IMS login page
3. **Token Generation**: IMS generates `LoginToken` after successful authentication
4. **Token Submission**: `LoginToken` submitted to backend via POST to `/login`
5. **Custom Filter Processing**: `CustomUsernamePasswordAuthenticationFilter` processes login
   - Extracts `LoginToken` from request parameters
   - Creates `UsernamePasswordAuthenticationToken`
   - Authenticates user through Spring Security
   - Sets authentication in security context
6. **User Details Retrieval**: System retrieves user details from database using GUID
7. **Session Creation**: HTTP session established with user information

### SecurityUser Object Structure

```java
public class SecurityUser extends User {
    private String serviceRegion;
    private String userId;        // System-generated UUID
    private String uuid;          // Same as userId
    private UserToken userToken;  // Contains guid, authToken, assoToken
    private String sessionId;
    private String userName;      // Retrieved from database
}
```

### UserToken Structure

```java
public class UserToken {
    private String guid;          // IMS GUID
    private String authToken;     // IMS authentication token
    private String assoToken;     // IMS association token
}
```

## Current User Name Handling

### Storage Approach

- User names are stored in `cms_adm_user.userName` column
- Names constructed during user approval process: `givenName + " " + familyName`
- Stored permanently in database until user record is deleted

### Display in UI

- Backend APIs return user names directly from database
- History services return user names (not user IDs) in API responses
- User history service converts user IDs to emails using `ImsEmailService`

### Example API Response (Current)

```json
{
  "historyRecords": [
    {
      "id": 12345,
      "userId": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
      "userName": "John Doe", // Directly from database
      "action": "ROLE_CHANGE",
      "timestamp": "2025-12-29T10:30:00Z"
    }
  ]
}
```

## IMS (Identity Management System) Integration

### IMS Connection Details

- **Domain**: Configured via `imsConfig.getIMSDetails().getImsDomain()`
- **Authentication**: Token-based using `authToken` and `assoToken`
- **User Identification**: Uses GUID (Global Unique Identifier) for user identification
- **Endpoints**: Multiple REST endpoints for different operations

### Key IMS Endpoints

#### User Details Endpoint

- **URL**: `{imsDomain}/ims/users/{guid}`
- **Method**: GET
- **Purpose**: Retrieve individual user details
- **Response**:

```json
{
  "stat": "ok",
  "accountInfo": {
    "guid": "user-123-ims-guid",
    "givenName": "John",
    "familyName": "Doe",
    "email": "john.doe@company.com",
    "superAdmin": "N",
    "approvalStatus": "A"
  }
}
```

#### Bulk User List Endpoint

- **URL**: `{imsDomain}/ims/users`
- **Method**: GET
- **Purpose**: Retrieve list of all user GUIDs
- **Response**:

```json
{
  "stat": "ok",
  "guidList": ["user-123-ims-guid", "user-456-ims-guid", "user-789-ims-guid"]
}
```

#### Bulk User Details Endpoint

- **URL**: `{imsDomain}/ims/users/all`
- **Method**: GET
- **Purpose**: Retrieve details for all users (bulk operation)
- **Response**:

```json
{
  "stat": "ok",
  "accountInfoList": [
    {
      "guid": "user-123-ims-guid",
      "givenName": "John",
      "familyName": "Doe",
      "email": "john.doe@company.com",
      "superAdmin": "N",
      "approvalStatus": "A"
    },
    {
      "guid": "user-456-ims-guid",
      "givenName": "Jane",
      "familyName": "Smith",
      "email": "jane.smith@company.com",
      "superAdmin": "Y",
      "approvalStatus": "A"
    }
  ]
}
```

### IMS Authentication Headers

```java
Map<String, String> headers = new HashMap<>();
headers.put("Accept", "application/json");
headers.put("ContentType", "application/json;charset=utf-8;");
headers.put("Cache-Control", "no-cache");
headers.put("ASSOToken", userToken.getAssoToken());
headers.put("AuthToken", userToken.getAuthToken());
```

## Requirements

### Functional Requirements

1. **User Name Resolution**

   - Convert user IDs to user names for display in UI
   - Support individual user name lookup
   - Support bulk user name lookup for history records
   - Handle user name changes in IMS within 5 minutes

2. **Data Consistency**

   - User names displayed in UI must be current (max 5-minute staleness)
   - Handle cases where users are deactivated in IMS
   - Graceful handling of IMS unavailability

3. **Integration Points**
   - Seamless integration with existing Admin Service APIs
   - No changes required in frontend/UI components
   - Backward compatibility with existing history services

### Non-Functional Requirements

1. **Performance**

   - Cache hit response time: < 1ms
   - Cache miss response time: < 100ms
   - Bulk operations (100 users): < 200ms
   - Support concurrent requests across multiple containers

2. **Scalability**

   - Support 1000+ active users
   - Handle peak loads during business hours
   - Efficient memory usage (target: 2-3MB cache per container)

3. **Reliability**

   - 99.9% availability for user name resolution
   - Graceful degradation when IMS is unavailable
   - Automatic recovery from failures

4. **Maintainability**
   - Minimal operational overhead
   - Clear monitoring and alerting
   - Simple deployment process

## Current Challenges

### Data Storage Issues

1. **Redundant Storage**: User names stored in database despite being available from IMS
2. **Synchronization Complexity**: Need to keep database names in sync with IMS
3. **Storage Overhead**: Additional database storage for user names

### Performance Concerns

1. **Database Queries**: Current approach requires database lookup for every user name
2. **History Loading**: Millions of history records require efficient user name resolution
3. **Pagination Impact**: Each page load requires user name resolution for visible records

### Scalability Limitations

1. **Container Multiplication**: 5+ containers each maintaining separate user data
2. **IMS Load**: Multiple containers refreshing data independently
3. **Memory Inefficiency**: Duplicate caching across containers

## Example Use Cases

### Individual User Name Lookup

```
UI requests user details for userId: "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
Admin Service needs to display user name
Process:
1. Check cache for user name
2. If cache miss:
   a. Lookup guid in cms_adm_user table
   b. Call IMS with guid to get user details
   c. Extract givenName + familyName
   d. Store in cache
3. Return user name to UI
```

### History Page Loading

```
UI requests history page (100 records)
Admin Service:
1. Query database for 100 history records (contains userIds)
2. Extract unique userIds (e.g., 50 unique users)
3. Bulk resolve user names for all userIds
4. Map user names to history records
5. Return completed records to UI
```

### Background Refresh

```
Every 5 minutes:
1. Get all active userIds from cms_adm_user table
2. Convert to guids
3. Call IMS bulk endpoint to get all user details
4. Update cache with fresh user names
5. Expire old cache entries
```

## Constraints and Limitations

### Technical Constraints

1. **No Distributed Cache**: Cannot use Redis or other distributed caching solutions
2. **Existing Infrastructure**: Must work within current deployment architecture
3. **IMS Rate Limits**: Need to be mindful of IMS service limits
4. **Memory Constraints**: Limited memory per container instance

### Business Constraints

1. **Data Freshness**: User names must be current (5-minute requirement)
2. **User Experience**: No degradation in UI response times
3. **Operational Simplicity**: Minimal operational overhead
4. **Cost Considerations**: Efficient resource utilization

## Success Criteria

### Performance Metrics

- Cache hit rate: > 95%
- Average response time: < 5ms
- 99th percentile response time: < 50ms
- Memory usage: < 3MB per container

### Reliability Metrics

- Uptime: 99.9%
- IMS call success rate: > 99.5%
- Error rate: < 0.1%
- Recovery time: < 30 seconds

### Operational Metrics

- Deployment simplicity
- Monitoring coverage: 100%
- Alerting effectiveness
- Troubleshooting ease

## Future Considerations

### Potential Scaling Needs

1. **User Growth**: System may need to support > 10,000 users
2. **Container Expansion**: May scale to 10+ containers
3. **Request Volume**: Increased history access patterns
4. **Geographic Distribution**: Multiple data centers/regions

### Evolution Path

1. **Phase 1**: Enhanced in-process caching solution
2. **Phase 2**: Monitoring and metrics collection
3. **Phase 3**: Evaluation for dedicated service based on metrics
4. **Phase 4**: Potential migration to dedicated service if needed

This comprehensive context should provide all necessary information for evaluating architectural approaches to the user name resolution requirement.