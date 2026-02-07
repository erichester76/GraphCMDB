# ITSM Feature Pack

## Overview

The ITSM (IT Service Management) Feature Pack provides comprehensive ITIL-aligned functionality for managing IT services within GraphCMDB. This feature pack implements five core ITSM disciplines with rich data models, relationships, and UI components.

## Components

### 1. Issue Management
Track and manage incidents affecting IT services.

**Properties:**
- name (required)
- description
- priority (required)
- status (required)
- assignee
- reporter
- created_date
- resolved_date
- category
- impact
- urgency

**Relationships:**
- CAUSED_BY → Problem
- TRIGGERED_BY → Event
- RESOLVED_BY → Change
- IMPACTS → Device

### 2. Problem Management
Manage root cause analysis and prevent recurring incidents.

**Properties:**
- name (required)
- description
- priority (required)
- status (required)
- assignee
- created_date
- resolved_date
- root_cause
- workaround
- category
- impact

**Relationships:**
- CAUSES → Issue
- RESOLVED_BY → Change
- AFFECTS → Device
- RELATED_TO → Problem

### 3. Change Management
Control and coordinate changes to IT infrastructure.

**Properties:**
- name (required)
- description
- priority (required)
- status (required)
- change_type (required)
- assignee
- requester
- created_date
- scheduled_date
- completed_date
- risk_level
- approval_status
- rollback_plan
- impact_assessment

**Relationships:**
- RESOLVES → Issue
- FIXES → Problem
- PART_OF → Release
- IMPACTS → Device

### 4. Release Management
Plan and coordinate software releases and deployments.

**Properties:**
- name (required)
- description
- version (required)
- status (required)
- release_manager
- created_date
- scheduled_date
- deployed_date
- release_type
- release_notes
- rollback_plan

**Relationships:**
- CONTAINS → Change
- DEPLOYS_TO → Device
- SUPERSEDES → Release

### 5. Event Management
Monitor and track system events and alerts.

**Properties:**
- name (required)
- description
- severity (required)
- status (required)
- timestamp (required)
- source
- event_type
- category
- acknowledged
- acknowledged_by
- acknowledged_date

**Relationships:**
- TRIGGERS → Issue
- RELATED_TO → Event
- ORIGINATED_FROM → Device

## UI Features

Each ITSM type includes a custom "ITSM Details" tab that displays:

### Issue Details Tab
- Related Problems (caused by)
- Resolved By Changes
- Triggering Events
- Impacted Devices

### Problem Details Tab
- Caused Issues
- Resolved By Changes
- Related Problems
- Affected Devices

### Change Details Tab
- Resolves Issues
- Fixes Problems
- Part of Releases
- Impacted Devices

### Release Details Tab
- Contained Changes
- Deployed To Devices
- Supersedes Releases
- Superseded By Releases

### Event Details Tab
- Triggered Issues
- Related Events
- Source Devices

## Technical Details

### Dependencies
- Django
- Neomodel
- Neo4j with APOC plugin (for JSON property handling)

### File Structure
```
feature_packs/itsm_pack/
├── config.py           # Feature pack configuration and tab definitions
├── types.json          # Node type definitions with properties and relationships
├── views.py            # Custom view functions for tab content
└── templates/          # HTML templates for tab views
    ├── issue_details_tab.html
    ├── problem_details_tab.html
    ├── change_details_tab.html
    ├── release_details_tab.html
    └── event_details_tab.html
```

### Integration
The feature pack automatically integrates with GraphCMDB through:
1. Type registration via types.json
2. Tab registration via config.py
3. Template directory auto-discovery
4. Dynamic view loading

## Usage

### Creating ITSM Records

Navigate to the dashboard and select any ITSM type (Issue, Problem, Change, Release, or Event) to create new records with the required properties.

### Viewing ITSM Details

When viewing an ITSM record, click the "ITSM Details" tab to see all related entities and relationships in organized tables.

### Creating Relationships

Use the "Add Relationship" feature on the detail page to connect ITSM records to each other and to infrastructure components (Devices).

## Best Practices

1. **Issue → Problem Linking**: Link recurring issues to problems for root cause tracking
2. **Change → Issue Resolution**: Connect changes to the issues they resolve
3. **Event → Issue Triggering**: Link monitoring events to the issues they create
4. **Release → Change Grouping**: Group related changes into releases
5. **Device Impact Tracking**: Always link ITSM records to affected devices

## Extension Points

The ITSM feature pack can be extended by:
1. Adding custom properties to types.json
2. Creating additional relationship types
3. Adding new views for specialized reports
4. Integrating with external ticketing systems
5. Adding workflow automation

## Version

Version: 1.0.0
Status: Production Ready
