# Teisec Agent Custom Capabilities

## Overview

Teisec Agent is designed to enhance security operations by leveraging custom capabilities. These capabilities integrate with various plugins to perform specific tasks such as retrieving sign-in logs, investigating domains and IP addresses, and analyzing user behavior. By using Teisec Agent's custom capabilities, you can automate and streamline complex security operations.

## Available Custom Capabilities

### KQL-User_Investigation

This set of capabilities is designed to investigate user activity by retrieving sign-in logs, failed sign-in attempts, security alerts, audit logs, device events, and behavior analytics data.

#### Capabilities

1. **GetRecentSignInLogs**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve the most recent sign-in logs for a specific user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     SigninLogs | where UserPrincipalName == '{{userPrincipalName}}' | order by TimeGenerated desc | take 10 | project TimeGenerated, UserPrincipalName, IPAddress, ResultType, AppDisplayName
     ```

2. **GetFailedSignInAttempts24h**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve the failed sign-in attempts for a specific user within the last 24 hours.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     SigninLogs | where UserPrincipalName == '{{userPrincipalName}}' and ResultType != 0 and TimeGenerated > ago(24h) | order by TimeGenerated desc | project TimeGenerated, UserPrincipalName, IPAddress, ResultType, AppDisplayName
     ```

3. **GetUserSecurityAlerts**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve the security alerts generated in the last 7 days related to a user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     SecurityAlert | where TimeGenerated > ago(7d) | where Entities contains '{{userPrincipalName}}' | order by TimeGenerated desc | project TimeGenerated, AlertName, AlertSeverity, Description, Entities
     ```

4. **GetUserAuditLogs**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve the last 10 audit logs for a specific user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     AuditLogs | where InitiatedBy.user.userPrincipalName == '{{userPrincipalName}}' | order by TimeGenerated desc | take 10 | project TimeGenerated, OperationName, Category, Result, InitiatedBy
     ```

5. **GetUserDeviceEvents**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve device events for a specific user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     DeviceEvents | where AccountName == '{{userPrincipalName}}' | order by Timestamp desc | take 10 | project Timestamp, DeviceName, ActionType, FileName, FolderPath
     ```

6. **GetUserBehaviorAnalytics**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve behavior analytics data for a specific user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     BehaviorAnalytics | where UserPrincipalName == '{{userPrincipalName}}' | order by TimeGenerated desc | take 10 | project TimeGenerated, ActivityType, ActionType, UserName, SourceIPAddress, SourceIPLocation, ActivityInsights, DevicesInsights
     ```

7. **GetUserDeviceLogonEvents**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Retrieve device logon events for a specific user.
   - **Parameters:**
     - `userPrincipalName`: The user principal name of the user.
   - **KQL Query:**
     ```kql
     DeviceLogonEvents | where AccountName == '{{userPrincipalName}}' | order by Timestamp desc | take 10 | project Timestamp, DeviceName, ActionType, RemoteIP, LogonType
     ```

### KQL-IOC_Ingestigation

This set of capabilities is designed to investigate domains and IP addresses by correlating them to the ThreatIntelligenceIndicator table in Sentinel.

#### Capabilities

1. **InvestigateDomainListThreatIntelligence**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Investigate a list of domains by correlating them to the ThreatIntelligenceIndicator table in Sentinel.
   - **Parameters:**
     - `domains`: A comma-separated list of domains to be investigated. Each domain should be enclosed in single quotes.
   - **KQL Query:**
     ```kql
     datatable(domain:string) [{{domains}}] | join kind=leftouter (ThreatIntelligenceIndicator) on $left.domain==$right.DomainName | project domain, Description, Action, ConfidenceScore, ThreatType, ThreatSeverity, Tags
     ```

2. **InvestigateIPListThreatIntelligence**
   - **Plugin:** SentinelKQLPlugin
   - **Description:** Investigate a list of IP addresses by correlating them to the ThreatIntelligenceIndicator table in Sentinel.
   - **Parameters:**
     - `ipAddresses`: A comma-separated list of IP addresses to be investigated. Each IP address should be enclosed in single quotes.
   - **KQL Query:**
     ```kql
     datatable(NetworkSourceIP:string) [{{ipAddresses}}] | join kind=leftouter (ThreatIntelligenceIndicator) on $left.NetworkSourceIP==$right.NetworkSourceIP | project NetworkSourceIP, Description, Action, ConfidenceScore, ThreatType, ThreatSeverity, Tags
     ```

## How to Use Custom Capabilities

1. **Define Capabilities:**
   - Custom capabilities are defined in JSON files located in the `capabilities` folder. Each capability includes the plugin name, title, description, type, parameters, and KQL query.

2. **Invoke Capabilities:**
   - Capabilities can be invoked as part of workflows or directly through the Teisec Agent interface. Ensure that the required parameters are provided when invoking a capability.

3. **Monitor Results:**
   - The system will provide updates on the progress of each capability execution. Once the execution is complete, review the results and take appropriate actions.

## Conclusion

Teisec Agent's custom capabilities provide a powerful way to automate and enhance your security operations. By leveraging these capabilities, you can perform complex investigations and analyses with ease.
