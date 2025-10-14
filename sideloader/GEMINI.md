# Gemini Session Summary: clan-event-webhook Plugin Development

This document summarizes the key insights, skills, and decisions made during the development and refactoring of the `clan-event-webhook` RuneLite plugin.

## Project Overview
The project evolved from a simple "greeter" plugin into a robust event tracking and API service for RuneLite. Its primary function is to capture various in-game events, cache them, push them to an external server, and expose a local API for polling live and historical game data.

## Key Architectural Decisions & Implementations

### 1. Service-Oriented Architecture
- **Problem:** Initial plugin was monolithic, with event tracking as its main function. User requested event tracking to be a "part" of a larger plugin.
- **Solution:** Refactored into a `ZSCompetitionsPlugin` (main entry point) and an `EventTrackerService` (dedicated event handling logic).
- **Guice Integration:** `EventTrackerService` is a `@Singleton` injected into `ZSCompetitionsPlugin`. The main plugin manages the service's lifecycle (`start()`, `stop()`) and registers/unregisters it with RuneLite's `EventBus`.

### 2. Namespace Refactoring
- **Change:** `com.example` to `nl.doonline.ZSCompetitions`.
- **Impact:** Required moving files, updating `package` declarations, `build.gradle` group, and `runelite-plugin.properties`.

### 3. Robust Connection Handling
- **Problem:** External POST endpoint might be unavailable. Need retries and user feedback.
- **Solution:** Implemented a `ScheduledExecutorService` for periodic connection checks.
- **State Management:** `connected`, `temporarilyDisabled` flags.
- **User Notification:** Chat message via `ChatMessageManager` on prolonged disconnection, with configurable delay.
- **Configuration:** Added `enableConnectionHandling`, `retryDelaySeconds`, `popupDelayMinutes` to `EventTrackerConfig`.

### 4. Embedded Web Server (Javalin)
- **Purpose:** Serve cached events and API schemas.
- **Endpoints:**
    - `GET /`: HTML index for human browsing.
    - `GET /api`: JSON index for programmatic access.
    - `GET /api/poll`: Returns `List<Map<String, Object>>` of cached events.
    - `GET /api/nearby-npcs`: Returns `List<Map<String, Object>>` of visible NPCs with bounding boxes.
    - `GET /api/nearby-objects`: Returns `List<Map<String, Object>>` of visible GameObjects with bounding boxes.
    - `GET /api/schema/{eventType}`: Returns JSON schema for a specific event type.
- **JSON Mapper:** Configured Javalin to use the existing `Gson` instance (`config.jsonMapper(new JavalinGson(gson))`) to avoid adding Jackson.

### 5. Event Tracking & Data Structure
- **Standardized JSON:** All events follow a consistent `{"timestamp": ..., "playerName": ..., "eventType": ..., "eventData": {...}}` structure.
- **Comprehensive Events:** Subscribed to `GameStateChanged`, `StatChanged`, `ActorDeath`, `HitsplatApplied`, `NpcSpawned`, `NpcDespawned`, `ItemContainerChanged`, `ChatMessage`, `GameTick`.
- **Session Events:** `SESSION_STARTED` and `SESSION_CLOSED` events sent on plugin start/stop. `SESSION_CLOSED` is synchronous.
- **Bounding Box Coordinates:**
    - Added `boundingBox` (`x`, `y`, `width`, `height`) to relevant events (`NPC_SPAWNED`, `ACTOR_DEATH`, `HITSPLAT_APPLIED`).
    - Helper methods `getBoundingBox(Actor)` and `getBoundingBox(GameObject)` created, delegating to `getBoundingBoxForShape(Shape)`.
- **Configurable Position Updates:** `ACTOR_POSITION_UPDATE` events sent on `GameTick` if `pushActorPositionUpdates` config is enabled.

## Troubleshooting & Lessons Learned

### 1. Gradle JDK Incompatibility
- **Issue:** `Unsupported class file major version 69` due to Gradle daemon running on Java 25 (early access).
- **Resolution:** Explicitly set `org.gradle.java.home=C:/path/to/jdk-11` in `gradle.properties` and stopped existing daemons (`gradlew --stop`).
- **Insight:** Always ensure the JDK running Gradle is compatible with the project's target and Gradle's version. `gradle.properties` is key for project-specific JDK configuration.

### 2. Lombok Version Incompatibility
- **Issue:** `java.lang.NoSuchFieldException` from Lombok when compiling with JDK 11.
- **Resolution:** Downgraded Lombok from `1.18.30` to `1.18.22`, a known stable version for JDK 11.
- **Insight:** Newer versions of annotation processors (like Lombok) might introduce incompatibilities with older JDKs, even if the project targets that JDK. Check compatibility matrices.

### 3. Javalin JSON Mapper Configuration
- **Issue:** 500 error on polling endpoint due to missing JSON object mapper.
- **Resolution:** Configured Javalin to use the existing `Gson` instance (`config.jsonMapper(new JavalinGson(gson))`).
- **Insight:** Javalin doesn't bundle a JSON mapper by default; it needs to be explicitly configured or a default (like Jackson) added.

### 4. RuneLite Client Thread Access
- **Issue:** `java.lang.AssertionError: must be called on client thread` when accessing game state from Javalin's server threads.
- **Resolution:** Used `CompletableFuture` with `clientThread.invoke(() -> { ... future.complete(result); })` and `future.get()` to safely execute game state access on the client thread and retrieve the result.
- **Insight:** Direct access to RuneLite's `Client` API from non-client threads is forbidden. Use `ClientThread` for safe inter-thread communication. `CompletableFuture` is a robust pattern for returning values.

### 5. Java String Escaping for HTML
- **Issue:** `unclosed string literal` error when building HTML strings with embedded quotes.
- **Resolution:** Switched to using single quotes for HTML attributes (`href='...'`) to simplify Java string literals and avoid complex backslash escaping.
- **Insight:** Be mindful of string literal escaping, especially when generating HTML or other languages within Java. Simplify where possible.

### 6. Git Repository Context
- **Issue:** `fatal: not a git repository` when running `git` commands from the wrong directory.
- **Resolution:** Ensured `git` commands were executed from the correct project root (`D:\Workspace\@OSRSNext\clan-event-webhook`).
- **Insight:** Always verify the current working directory for VCS operations.

## Instruction for Future Updates

This `GEMINI.md` file should be updated after each significant development session or commit. Summarize new features, architectural changes, encountered issues, and their resolutions. This ensures a continuous learning and documentation process.
