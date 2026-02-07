# ITSM Feature Pack - Example Usage Scenarios

## Example 1: Creating an Issue and Linking to a Problem

### Step 1: Create an Issue
```json
{
  "name": "Database Server Slow Response",
  "description": "Users reporting slow response times from the main database server",
  "priority": "High",
  "status": "Open",
  "assignee": "John Doe",
  "reporter": "Jane Smith",
  "created_date": "2024-01-15",
  "category": "Performance",
  "impact": "High",
  "urgency": "High"
}
```

### Step 2: Create Related Problem
```json
{
  "name": "Database Query Optimization Issue",
  "description": "Inefficient queries causing performance degradation",
  "priority": "High",
  "status": "Investigating",
  "assignee": "DBA Team",
  "created_date": "2024-01-15",
  "root_cause": "Missing indexes on frequently queried tables",
  "workaround": "Use read replicas for reporting queries",
  "category": "Database"
}
```

### Step 3: Link Issue to Problem
Create relationship: `Issue -[CAUSED_BY]-> Problem`

**Result in ITSM Details Tab:**
The Issue will now show the related Problem under "Related Problems" section.

---

## Example 2: Change Management Workflow

### Step 1: Create a Change
```json
{
  "name": "Add Database Indexes for Performance",
  "description": "Add missing indexes identified in performance analysis",
  "priority": "High",
  "status": "Approved",
  "change_type": "Standard",
  "assignee": "DBA Team",
  "requester": "John Doe",
  "created_date": "2024-01-16",
  "scheduled_date": "2024-01-20",
  "risk_level": "Medium",
  "approval_status": "Approved",
  "rollback_plan": "Drop indexes if performance degrades",
  "impact_assessment": "5 minute downtime during index creation"
}
```

### Step 2: Link Change to Problem and Issue
- Create: `Change -[FIXES]-> Problem`
- Create: `Change -[RESOLVES]-> Issue`

### Step 3: Link to Affected Device
- Create: `Change -[IMPACTS]-> Device` (e.g., "db-server-01")

**Result in ITSM Details Tab:**
The Change will show:
- Fixes Problems: "Database Query Optimization Issue"
- Resolves Issues: "Database Server Slow Response"
- Impacted Devices: "db-server-01"

---

## Example 3: Event Monitoring to Issue Creation

### Step 1: Create an Event
```json
{
  "name": "High CPU Usage Alert",
  "description": "CPU usage exceeded 90% threshold",
  "severity": "Warning",
  "status": "New",
  "timestamp": "2024-01-15T14:30:00Z",
  "source": "Monitoring System",
  "event_type": "Performance Alert",
  "category": "Infrastructure",
  "acknowledged": false
}
```

### Step 2: Link Event to Device
Create: `Event -[ORIGINATED_FROM]-> Device` (e.g., "web-server-03")

### Step 3: Create Issue from Event
Create an Issue and link: `Issue -[TRIGGERED_BY]-> Event`

**Result in ITSM Details Tab:**
- Event shows: "Triggered Issues" with the new issue
- Issue shows: "Triggering Events" with the monitoring alert
- Both show: "Source/Impacted Devices" with device details

---

## Example 4: Release Management

### Step 1: Create a Release
```json
{
  "name": "Q1 2024 Application Update",
  "description": "Quarterly update with bug fixes and new features",
  "version": "2024.Q1.1",
  "status": "Planned",
  "release_manager": "Release Team",
  "created_date": "2024-01-10",
  "scheduled_date": "2024-02-01",
  "release_type": "Major",
  "release_notes": "Includes 15 bug fixes and 5 new features"
}
```

### Step 2: Add Changes to Release
Create multiple: `Release -[CONTAINS]-> Change` relationships

### Step 3: Link to Deployment Targets
Create: `Release -[DEPLOYS_TO]-> Device` for each target device

**Result in ITSM Details Tab:**
The Release shows:
- Contained Changes: List of all changes in this release
- Deployed To Devices: All target deployment devices

---

## Example 5: Complex ITSM Workflow

### Complete Incident-to-Resolution Flow:

1. **Event Detected**
   - Monitoring system generates Event: "Memory Leak Alert"
   - Links to Device: "app-server-02"

2. **Issue Created**
   - Operations creates Issue: "Application Memory Leak"
   - Links Issue to Event (TRIGGERED_BY)
   - Links Issue to Device (IMPACTS)

3. **Problem Analysis**
   - Engineering creates Problem: "Memory Management Bug in v1.5"
   - Links Problem to Issue (CAUSES)
   - Links Problem to Device (AFFECTS)

4. **Change Planned**
   - Change created: "Deploy Memory Leak Patch"
   - Links to Problem (FIXES)
   - Links to Issue (RESOLVES)
   - Links to Device (IMPACTS)

5. **Release Created**
   - Release created: "Hotfix v1.5.1"
   - Links to Change (CONTAINS)
   - Links to Device (DEPLOYS_TO)

6. **Superseding Release**
   - New Release: "v1.6.0"
   - Links to old release: SUPERSEDES v1.5.1

### Visual Relationship Map:
```
Event (Memory Leak Alert)
  └─[ORIGINATED_FROM]→ Device (app-server-02)
  └─[TRIGGERS]→ Issue (Application Memory Leak)
                   └─[CAUSED_BY]→ Problem (Memory Management Bug)
                   └─[RESOLVED_BY]→ Change (Deploy Patch)
                                      └─[PART_OF]→ Release (Hotfix v1.5.1)
                                                      └─[SUPERSEDED_BY]→ Release (v1.6.0)
```

---

## Querying ITSM Data

### Find All Open Issues Caused by a Specific Problem
```cypher
MATCH (p:Problem {name: "Database Query Optimization Issue"})
MATCH (p)<-[:CAUSED_BY]-(i:Issue)
WHERE i.status = "Open"
RETURN i
```

### Find All Changes in a Release
```cypher
MATCH (r:Release {version: "2024.Q1.1"})
MATCH (r)-[:CONTAINS]->(c:Change)
RETURN c.name, c.status, c.change_type
```

### Find Devices Affected by Multiple Issues
```cypher
MATCH (i:Issue)-[:IMPACTS]->(d:Device)
WITH d, count(i) as issue_count
WHERE issue_count > 1
RETURN d.name, issue_count
ORDER BY issue_count DESC
```

### Trace Event to Resolution
```cypher
MATCH path = (e:Event)-[:TRIGGERS]->(i:Issue)-[:RESOLVED_BY]->(c:Change)
WHERE e.name CONTAINS "Memory"
RETURN path
```

---

## Dashboard Metrics

The ITSM Feature Pack enables tracking of key metrics:

1. **Issue Metrics**
   - Open vs Closed Issues
   - Issues by Priority
   - Average Time to Resolution
   - Issues by Category

2. **Problem Metrics**
   - Active Problems
   - Problems by Root Cause
   - Recurring Issues per Problem

3. **Change Metrics**
   - Changes by Status
   - Changes by Risk Level
   - Successful vs Failed Changes
   - Changes by Type

4. **Release Metrics**
   - Releases by Status
   - Changes per Release
   - Deployment Success Rate

5. **Event Metrics**
   - Events by Severity
   - Events by Source
   - Event-to-Issue Conversion Rate
   - Acknowledged vs Unacknowledged Events

---

## Integration Patterns

### Integration with Existing CMDB
- Link ITSM records to existing Device nodes
- Track impact on infrastructure components
- Visualize service dependencies

### Workflow Automation Opportunities
- Auto-create Issues from Events based on severity
- Auto-link Changes to affected Devices
- Track Change approval workflows
- Monitor Release deployment status

### Reporting Capabilities
- Impact Analysis: Which devices are affected by most issues?
- Change Success: What percentage of changes resolve issues?
- Problem Trends: Are problems recurring?
- Release Quality: How many issues per release?
