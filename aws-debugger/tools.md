# 🛠️ **Comprehensive AWS Debugging Tools for Multi-Region, Multi-AZ Infrastructure**

Based on your stack (ECS, API Gateway, NLB, ALB, SQS, SNS, RDS, Lambda, EventBridge, CloudWatch) across EU and US regions with multiple AZs, here's a complete tool list organized by category:

---

## **1. ECS & Container Tools** (6 tools)

### `get_ecs_service_info`
**Purpose:** Get overall health status of an ECS service  
**What it returns:** Running/desired task counts, deployment status, task definition ARN, load balancer configuration, service events (last 10), network configuration (VPC, subnets, security groups)  
**Use case:** "Is my monitoring-service running? Are all tasks healthy?"

### `get_ecs_task_details`
**Purpose:** Get detailed information about specific ECS tasks  
**What it returns:** Task status, container status, health check results, ENI (network interface) details, stopped reason (if failed), exit codes  
**Use case:** "Why did this specific task fail? What was the exit code?"

### `get_ecs_task_logs`
**Purpose:** Fetch recent CloudWatch logs for a specific task  
**What it returns:** Last N log entries from the task's containers, timestamps, log stream names  
**Use case:** "Show me the logs from the failed task to see application errors"

### `get_ecs_service_deployments`
**Purpose:** Check deployment history and rollout status  
**What it returns:** Active deployments, rollout state, failed deployment reasons, task definition changes  
**Use case:** "Did the latest deployment succeed? Is it still rolling out?"

### `list_ecs_tasks_by_status`
**Purpose:** List all tasks in a service filtered by status  
**What it returns:** Task ARNs grouped by status (RUNNING, STOPPED, PENDING), stopped reasons summary  
**Use case:** "Show me all stopped tasks in the last hour to find patterns"

### `check_ecs_capacity`
**Purpose:** Check ECS cluster capacity and resource availability  
**What it returns:** Cluster CPU/memory utilization, registered container instances, pending tasks due to insufficient resources  
**Use case:** "Are tasks failing because the cluster is out of capacity?"

---

## **2. Load Balancer Tools (NLB/ALB)** (5 tools)

### `get_alb_target_health`
**Purpose:** Check health of targets registered to an Application Load Balancer  
**What it returns:** Health status per target, health check configuration, unhealthy targets with reasons, availability zone distribution  
**Use case:** "Why is my ALB marking ECS tasks as unhealthy?"

### `get_nlb_target_health`
**Purpose:** Check health of targets registered to a Network Load Balancer  
**What it returns:** Health status per target, health check configuration, connection draining status  
**Use case:** "Are my NLB targets healthy across all AZs?"

### `get_alb_listener_rules`
**Purpose:** Get ALB listener configuration and routing rules  
**What it returns:** Listener ports, SSL certificates, routing rules (path/host patterns), target groups, default actions  
**Use case:** "Is traffic being routed to the correct target group?"

### `get_load_balancer_metrics`
**Purpose:** Get recent CloudWatch metrics for ALB/NLB  
**What it returns:** Request count, target response time, HTTP error codes (4xx, 5xx), active connections, healthy/unhealthy host counts  
**Use case:** "Are we seeing increased 5xx errors from the load balancer?"

### `compare_lb_across_regions`
**Purpose:** Compare load balancer configurations between regions  
**What it returns:** Configuration diffs (listeners, health checks, attributes), target group differences  
**Use case:** "Why does my ALB work in US but not EU?"

---

## **3. API Gateway Tools** (5 tools)

### `get_api_gateway_stage_info`
**Purpose:** Get API Gateway stage configuration  
**What it returns:** Stage name, deployment ID, throttling settings, cache configuration, stage variables, integration endpoints  
**Use case:** "What's the current deployment on the prod stage?"

### `get_api_gateway_integration_config`
**Purpose:** Get integration configuration for API resources  
**What it returns:** Integration type (Lambda, HTTP, AWS service), endpoints/ARNs, timeout settings, VPC link configuration, request/response mappings  
**Use case:** "Is my API Gateway pointing to the correct Lambda ARN in this region?"

### `get_api_gateway_logs`
**Purpose:** Fetch recent execution logs from CloudWatch  
**What it returns:** Request/response logs, integration latency, errors, request IDs for tracing  
**Use case:** "Show me failed API requests in the last hour"

### `get_api_gateway_authorizer_info`
**Purpose:** Check Lambda authorizer or Cognito authorizer configuration  
**What it returns:** Authorizer type, Lambda function ARN, token source, caching configuration, validation errors  
**Use case:** "Is the authorizer rejecting requests? Is it configured correctly?"

### `check_api_gateway_throttling`
**Purpose:** Check if requests are being throttled  
**What it returns:** Throttle limits (burst, rate), current usage, throttled request count, API key usage if applicable  
**Use case:** "Are API calls being rate-limited?"

---

## **4. Lambda Tools** (5 tools)

### `get_lambda_function_info`
**Purpose:** Get Lambda function configuration  
**What it returns:** Runtime, handler, memory, timeout, environment variables, IAM role, VPC configuration, layers, concurrent executions limit  
**Use case:** "Is the Lambda configured with correct environment variables and IAM role?"

### `get_lambda_recent_invocations`
**Purpose:** Get recent invocation metrics and errors  
**What it returns:** Invocation count, error count, duration metrics, throttled invocations, concurrent execution count  
**Use case:** "How many times did this Lambda fail in the last hour?"

### `get_lambda_error_logs`
**Purpose:** Fetch error logs from CloudWatch  
**What it returns:** Error messages, stack traces, request IDs, timestamps  
**Use case:** "Show me the actual errors from Lambda executions"

### `check_lambda_permissions`
**Purpose:** Check Lambda resource policy and IAM permissions  
**What it returns:** Resource policy (who can invoke), IAM role permissions, VPC endpoint access if in VPC  
**Use case:** "Can API Gateway/EventBridge actually invoke this Lambda?"

### `compare_lambda_across_regions`
**Purpose:** Compare Lambda function configurations between regions  
**What it returns:** Configuration diffs (code version, environment variables, VPC settings, IAM roles)  
**Use case:** "Why does the same Lambda work in US but not EU?"

---

## **5. Messaging Tools (SNS/SQS)** (6 tools)

### `get_sns_topic_info`
**Purpose:** Get SNS topic configuration and subscriptions  
**What it returns:** Topic ARN, display name, subscriptions (protocol, endpoint, status), delivery policies, region  
**Use case:** "Does this SNS topic have email subscriptions configured?"

### `get_sns_subscription_details`
**Purpose:** Check specific subscription status and filters  
**What it returns:** Subscription ARN, confirmation status, filter policy, delivery status, dead-letter queue  
**Use case:** "Why aren't messages being delivered to this subscription?"

### `trace_sns_message_delivery`
**Purpose:** Track SNS message delivery status  
**What it returns:** Publish timestamp, delivery attempts, successful/failed deliveries per subscription, failure reasons  
**Use case:** "Was the message actually published? Did it reach subscribers?"

### `get_sqs_queue_info`
**Purpose:** Get SQS queue configuration and metrics  
**What it returns:** Queue URL/ARN, message count (visible/in-flight/delayed), retention period, visibility timeout, redrive policy (DLQ config), message age  
**Use case:** "Are messages stuck in the queue? Is the DLQ configured?"

### `get_sqs_dlq_messages`
**Purpose:** Check dead-letter queue for failed messages  
**What it returns:** DLQ message count, sample messages (body, attributes), approximate receive count, timestamps  
**Use case:** "What messages failed processing and ended up in the DLQ?"

### `check_sns_sqs_permissions`
**Purpose:** Validate SNS can publish to SQS queue  
**What it returns:** SQS queue policy, SNS topic permissions, cross-region publishing permissions  
**Use case:** "Can SNS in US region publish to SQS in EU region?"

---

## **6. EventBridge Tools** (4 tools)

### `get_eventbridge_rule_info`
**Purpose:** Get EventBridge rule configuration  
**What it returns:** Event pattern, schedule expression, state (ENABLED/DISABLED), targets (Lambda/SQS/SNS), IAM role for targets  
**Use case:** "Is the EventBridge rule enabled? What's the event pattern?"

### `get_eventbridge_rule_targets`
**Purpose:** List and validate targets for a rule  
**What it returns:** Target ARNs, input transformers, dead-letter config, retry policy, target health  
**Use case:** "Is the EventBridge rule invoking the correct Lambda?"

### `check_eventbridge_invocations`
**Purpose:** Check rule invocation metrics  
**What it returns:** Invocation count, failed invocations, matched events, throttled invocations  
**Use case:** "How many times did this rule trigger? Did any fail?"

### `validate_event_pattern`
**Purpose:** Test if an event pattern matches sample events  
**What it returns:** Match result, event pattern explanation, sample events that would match  
**Use case:** "Will my event pattern actually match the events I'm sending?"

---

## **7. RDS Tools** (4 tools)

### `get_rds_instance_info`
**Purpose:** Get RDS instance configuration and status  
**What it returns:** Instance status, endpoint, port, engine version, multi-AZ status, backup retention, parameter group, security groups, VPC/subnets  
**Use case:** "Is the database instance running? Is it multi-AZ?"

### `get_rds_connection_metrics`
**Purpose:** Get database connection and performance metrics  
**What it returns:** Active connections, CPU utilization, read/write IOPS, storage space, failed connection attempts  
**Use case:** "Is the database overloaded? Are connections failing?"

### `check_rds_security_groups`
**Purpose:** Check security group rules for RDS access  
**What it returns:** Inbound rules, allowed CIDR blocks/security groups, port configuration  
**Use case:** "Can my ECS tasks reach the database?"

### `get_rds_error_logs`
**Purpose:** Fetch recent error logs from RDS  
**What it returns:** Recent error messages, slow query logs if enabled, connection errors  
**Use case:** "Are there any database errors or slow queries?"

---

## **8. CloudWatch & Observability Tools** (6 tools)

### `get_cloudwatch_logs`
**Purpose:** Search CloudWatch Logs with filters  
**What it returns:** Log entries matching filter pattern, timestamps, log streams  
**Use case:** "Show me all ERROR level logs from the last 2 hours"

### `get_cloudwatch_alarms`
**Purpose:** Get active alarms for a service/resource  
**What it returns:** Alarm state (OK/ALARM/INSUFFICIENT_DATA), metric, threshold, evaluation periods, recent state changes  
**Use case:** "What alarms are firing right now?"

### `get_cloudwatch_metrics`
**Purpose:** Get specific CloudWatch metrics  
**What it returns:** Metric values over time window, statistics (avg/min/max/sum), dimensions  
**Use case:** "Show me CPU utilization for this ECS service over the last hour"

### `search_logs_across_services`
**Purpose:** Search logs across multiple log groups (correlation)  
**What it returns:** Correlated logs from different services based on trace ID or timestamp  
**Use case:** "Find all logs related to request ID xyz across API Gateway, Lambda, and ECS"

### `get_xray_trace`
**Purpose:** Get X-Ray trace for a request (if enabled)  
**What it returns:** Full trace with segments, subsegments, service map, latency breakdown, errors  
**Use case:** "Show me the complete path of this failed request across services"

### `check_log_group_configuration`
**Purpose:** Validate CloudWatch Logs configuration  
**What it returns:** Log group retention, subscription filters, metric filters, encryption  
**Use case:** "Are logs being retained? Are there any subscription filters set up?"

---

## **9. Cross-Region & Multi-AZ Tools** (5 tools)

### `compare_service_config_across_regions`
**Purpose:** Compare service configurations between US and EU regions  
**What it returns:** Configuration diffs for ECS services, Lambda functions, API Gateways, load balancers  
**Use case:** "Why does the service work in US but not EU?"

### `check_cross_region_connectivity`
**Purpose:** Test network connectivity between regions  
**What it returns:** VPC peering status, transit gateway configuration, route table entries, security group rules  
**Use case:** "Can services in US region communicate with resources in EU?"

### `get_multi_az_distribution`
**Purpose:** Check resource distribution across availability zones  
**What it returns:** Resources per AZ (ECS tasks, RDS replicas, load balancer targets), AZ health status  
**Use case:** "Are tasks distributed evenly across AZs? Is one AZ having issues?"

### `detect_region_specific_issues`
**Purpose:** Find issues that only occur in specific regions  
**What it returns:** Error patterns, metric anomalies, configuration differences per region  
**Use case:** "Why do I see errors only in eu-west-1?"

### `check_resource_tagging`
**Purpose:** List resources by tags across regions  
**What it returns:** Resources matching tags, region distribution, missing tags  
**Use case:** "Find all resources for the monitoring-service across all regions"

---

## **10. IAM & Permissions Tools** (4 tools)

### `check_iam_role_permissions`
**Purpose:** Validate IAM role has required permissions  
**What it returns:** Attached policies, inline policies, simulated policy evaluation for specific actions  
**Use case:** "Can the ECS task role actually publish to SNS?"

### `check_resource_policy`
**Purpose:** Check resource-based policies (SNS, SQS, Lambda, API Gateway)  
**What it returns:** Resource policy document, who can access, cross-account permissions  
**Use case:** "Can Lambda in US invoke API Gateway in EU?"

### `validate_service_permissions`
**Purpose:** End-to-end permission validation for a service flow  
**What it returns:** Permission check results for each step (ECS → API Gateway → Lambda → SNS → SQS)  
**Use case:** "Are all permissions in place for this service to work?"

### `get_iam_policy_simulator_results`
**Purpose:** Simulate IAM policy evaluation for actions  
**What it returns:** Allow/deny results, conflicting policies, reasons for denial  
**Use case:** "Why is this action being denied?"

---

## **11. Network & VPC Tools** (4 tools)

### `check_security_group_rules`
**Purpose:** Check security group inbound/outbound rules  
**What it returns:** Rules allowing/blocking traffic, port ranges, source/destination CIDR or SG  
**Use case:** "Can the load balancer reach ECS tasks? Is port 8080 open?"

### `check_vpc_endpoints`
**Purpose:** Check VPC endpoints for AWS services  
**What it returns:** Endpoint type (interface/gateway), service name, subnet associations, security groups  
**Use case:** "Is there a VPC endpoint for SNS/SQS? Do services need internet access?"

### `check_nat_gateway_status`
**Purpose:** Check NAT Gateway health and metrics  
**What it returns:** State, connections count, bytes processed, error rate  
**Use case:** "Is the NAT gateway causing connectivity issues?"

### `trace_network_path`
**Purpose:** Trace network path between two resources  
**What it returns:** Route table entries, network ACLs, security groups along the path, potential blocks  
**Use case:** "Why can't Lambda reach RDS?"

---

## **12. Diagnostic & Utility Tools** (5 tools)

### `get_service_health_overview`
**Purpose:** High-level health check for a service across all components  
**What it returns:** Status summary for ECS, ALB, Lambda, SQS, SNS, RDS, CloudWatch alarms  
**Use case:** "Give me a quick health status of monitoring-service"

### `find_recent_errors`
**Purpose:** Find errors across all services in a time window  
**What it returns:** Aggregated errors from CloudWatch Logs, Lambda, API Gateway, ECS task failures  
**Use case:** "Show me all errors from the last hour across all services"

### `check_service_dependencies`
**Purpose:** Map service dependencies and check their health  
**What it returns:** Dependency graph, health status of each dependency  
**Use case:** "Is the monitoring-service failing because SNS is down?"

### `validate_deployment_configuration`
**Purpose:** Pre-deployment validation of configurations  
**What it returns:** Configuration validation results, missing resources, permission issues  
**Use case:** "Check if everything is configured correctly before deploying"

### `get_cost_anomalies`
**Purpose:** Detect cost anomalies that might indicate issues  
**What it returns:** Unusual spending patterns, services with spike in usage  
**Use case:** "Is there an infinite loop causing Lambda invocations to spike?"

---

## 📊 **Summary by Priority**

### **Tier 1 (Must-Have - 20 tools):** Core debugging for your services
- All ECS tools (6)
- All Load Balancer tools (5)
- API Gateway: stage info, integration config, logs (3)
- Lambda: function info, recent invocations, error logs (3)
- SNS/SQS: topic info, queue info, DLQ messages (3)

### **Tier 2 (High-Value - 15 tools):** Cross-region and multi-service debugging
- EventBridge tools (4)
- RDS tools (4)
- Cross-region tools (5)
- IAM permissions tools (2)

### **Tier 3 (Nice-to-Have - 20 tools):** Deep diagnostics and utilities
- CloudWatch tools (6)
- Network/VPC tools (4)
- Diagnostic utilities (5)
- Remaining API Gateway/Lambda/SNS tools (5)

---

## 🎯 **Recommended Starting Set (15 Tools for POC)**

For your initial POC, I'd recommend starting with these 15 tools that cover 80% of common debugging scenarios:

1. `get_ecs_service_info`
2. `get_ecs_task_logs`
3. `get_alb_target_health`
4. `get_api_gateway_integration_config`
5. `get_api_gateway_logs`
6. `get_lambda_function_info`
7. `get_lambda_error_logs`
8. `get_sns_topic_info`
9. `get_sqs_queue_info`
10. `get_sqs_dlq_messages`
11. `get_cloudwatch_logs`
12. `get_cloudwatch_alarms`
13. `compare_service_config_across_regions`
14. `check_iam_role_permissions`
15. `get_service_health_overview`

---

Would you like me to now **discuss the detailed implementation approach** for these tools, including:
1. Input/output schemas for each tool
2. Specific boto3 APIs to call
3. Error handling patterns
4. How to structure the MCP server code

Or would you prefer to refine this tool list first?