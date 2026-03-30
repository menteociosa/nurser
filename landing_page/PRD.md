# CareShift -- Product Requirements Document (PRD)

## Product Overview

CareShift is a Progressive Web App (PWA) designed for small caregiver
teams to record patient observations and transfer information between
shifts quickly and reliably.

The primary goal is ultra-fast data entry during caregiving work while
still capturing structured data that can generate alerts and summaries.

The system replaces: - paper notebooks - messaging threads - informal
spreadsheets

with a structured mobile-friendly handover tool.

------------------------------------------------------------------------

## Key Design Principles

### Ultra-Fast Logging

Common events must be recorded in one or two taps.

Example flow: Bathroom → Urinated

Result: - event saved - timestamp defaults to current time - caregiver
automatically recorded

Timestamp must remain editable.

### Minimal Typing

Interface prioritizes: - quick tap buttons - dropdown selections - voice
recording

Free text is optional.

### Immediate Context

Caregivers beginning a shift must understand patient status within 10
seconds.

Main screen shows: - latest events - alerts - pending tasks

### Mobile First

Primary devices: - smartphones - tablets

Large touch targets and clear UI required.

------------------------------------------------------------------------

## User Roles

### Team Lead (Administrator)

Responsibilities: - create and manage teams - configure observation
fields - invite caregivers - view dashboards - manage alerts - manage
patient profile

### Caregiver (Team Member)

Responsibilities: - log events - record shift logs - record voice
notes - view patient timeline - complete tasks

Caregivers may belong to multiple teams simultaneously.

------------------------------------------------------------------------

## Core Concepts

### Team

Represents caregivers responsible for one patient.

Includes: - patient profile - caregiver list - observation fields -
shift logs - alerts - tasks

### Patient Care Profile

Contains persistent patient information:

Example fields: - allergies - medications list - mobility status -
dietary restrictions - medical conditions - emergency contacts

### Shift Log

Records events during one caregiver shift.

Contains: - caregiver - start time - end time - observations - tasks -
notes - voice notes

------------------------------------------------------------------------

## Event Logging

### Quick Event Logging

Primary interaction model.

Examples of quick actions: - Bathroom - Meal - Medication - Mobility -
Sleep - Water intake

Each tap records: - caregiver - timestamp - event type

Optional modal: Add note or adjust timestamp.

### Event Types

Examples:

Bathroom: - Urinated - Bowel movement

Meal: - Full meal - Partial meal - Refused

Mobility: - Walked - Walked assisted - Bed rest

Medication: - medication selector - dosage - confirmation

------------------------------------------------------------------------

## Configurable Observation Fields

Team leads may add additional structured fields.

Supported types: - Boolean - Dropdown - Numeric - Multi-select - Text -
Timestamp event

------------------------------------------------------------------------

## Voice Notes

Caregivers may record voice notes.

Process: 1. record audio 2. upload to server 3. speech-to-text
transcription 4. store audio and transcript

------------------------------------------------------------------------

## Timeline View

Chronological patient event timeline.

Example:

08:12 -- Bathroom (urinated)\
09:30 -- Breakfast (full meal)\
10:00 -- Medication (Metformin)\
11:15 -- Mobility (walked assisted)

Elements: - icon - timestamp - caregiver - event type

------------------------------------------------------------------------

## Next Shift Tasks

Caregivers may leave tasks for the next shift.

Examples: - administer medication - encourage walking - monitor
temperature

Statuses: - pending - completed - skipped

Completion records timestamp and caregiver.

------------------------------------------------------------------------

## Shift Summary

When a shift ends the system generates a summary automatically.

Example:

Shift Summary -- Maria (08:00--16:00)

Patient slept poorly.\
Ate breakfast and lunch.\
Urinated twice.\
Walked once with assistance.\
Medication administered: Metformin.

Caregiver may edit before finalizing.

------------------------------------------------------------------------

## Alerts and Pattern Detection

Examples:

Bathroom alerts: - no bathroom event in 24h

Mobility alerts: - no mobility event in 24h

Sleep alerts: - poor sleep multiple shifts

Medication alerts: - scheduled medication missing

Alerts appear in: - dashboard - patient screen - push notifications

------------------------------------------------------------------------

## Dashboard (Team Lead)

Metrics examples:

Last 24 hours: - bathroom visits - meals eaten - mobility events -
medications administered

Simple charts show event frequency.

------------------------------------------------------------------------

## Notifications

Supported via PWA push notifications.

Triggers: - new shift log - task assigned - alerts - team invitation

------------------------------------------------------------------------

## Localization

Initial language: Mexican Spanish.

Architecture must support: - English - Swedish - German

All UI strings externalized.

------------------------------------------------------------------------

## Security

Minimum requirements: - HTTPS - authenticated access - role-based
permissions - encrypted storage - team-level data isolation

Future compliance: - GDPR - HIPAA-style protections

------------------------------------------------------------------------

## PWA Requirements

Application must: - be installable on mobile - support push
notifications - support mobile-first interface

Future optional feature: offline event caching.

------------------------------------------------------------------------

## MVP Scope

Included: - teams - caregivers - patient profile - quick event logging -
timeline - configurable observation fields - voice notes with
transcription - tasks - shift summaries - alerts - dashboards - push
notifications

Excluded: - hospital system integrations - billing systems - insurance
compliance
