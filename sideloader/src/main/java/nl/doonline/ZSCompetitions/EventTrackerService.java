package nl.doonline.ZSCompetitions;

import com.google.gson.Gson;
import com.google.inject.Singleton;
import io.javalin.Javalin;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.*;
import net.runelite.api.events.*;
import net.runelite.client.callback.ClientThread;
import net.runelite.client.chat.ChatColorType;
import net.runelite.client.chat.ChatMessageBuilder;
import net.runelite.client.chat.ChatMessageManager;
import net.runelite.client.chat.QueuedMessage;
import net.runelite.client.eventbus.Subscribe;
import okhttp3.*;
import org.jetbrains.annotations.NotNull;

import javax.inject.Inject;
import java.awt.Rectangle;
import java.awt.Shape;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;
import java.util.stream.Collectors;

@Slf4j
@Singleton
public class EventTrackerService {

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final Client client;
    private final ClientThread clientThread;
    private final EventTrackerConfig config;
    private final Gson gson;
    private final OkHttpClient okHttpClient;
    private final ChatMessageManager chatMessageManager;

    private final List<Map<String, Object>> eventCache = new CopyOnWriteArrayList<>();
    private final Map<String, Map<String, String>> schemaRegistry = new ConcurrentHashMap<>();

    private Javalin pollingServer;
    private ScheduledExecutorService scheduler;

    private volatile boolean connected = false;
    private volatile boolean temporarilyDisabled = false;
    private ScheduledFuture<?> connectionCheckTask;
    private ScheduledFuture<?> popupTask;
    private WorldView wv;

    @Inject
    public EventTrackerService(Client client, ClientThread clientThread, EventTrackerConfig config, Gson gson, OkHttpClient okHttpClient, ChatMessageManager chatMessageManager) {
        this.client = client;
        this.clientThread = clientThread;
        this.config = config;
        this.gson = gson;
        this.okHttpClient = okHttpClient;
        this.chatMessageManager = chatMessageManager;
        registerSchemas();
    }

    public void start() {
        log.info("Event Tracker Service started!");
        this.temporarilyDisabled = false;
        this.scheduler = Executors.newSingleThreadScheduledExecutor();
        startPollingServer();
        sendSessionEvent("SESSION_STARTED", false);

        if (config.enableConnectionHandling()) {
            startConnectionCheck();
        } else {
            connected = true;
        }
    }

    public void stop() {
        log.info("Event Tracker Service stopped!");
        if (connected) {
            sendSessionEvent("SESSION_CLOSED", true);
        }
        if (pollingServer != null) {
            pollingServer.stop();
        }
        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdownNow();
        }
    }

    private void startPollingServer() {
        try {
            pollingServer = Javalin.create(config -> {
                config.jsonMapper(new io.javalin.json.JavalinGson(gson));
            }).start(config.pollPort());

            // HTML endpoint for human-readable browsing
            pollingServer.get("/", ctx -> {
                StringBuilder sb = new StringBuilder();
                sb.append("<h1>0ZS Competition Event Proxy Server</h1>");
                sb.append("<p>Remains hidden for common users. debugging should be done here, i dont have to store any data in this way. and makes it easier for our main host domain to manage the player driven community events and clan competitions.</p>");
                sb.append("<p>We do not store session data unless we have to inquire on some specifics if it comes to which player actually won the contest. we keep session timelines only in memory.</p>");
                sb.append("<h2>Endpoints:</h2>");
                sb.append("<ul>");
                sb.append("<li><a href='/api'>instructions</a></li>");
                sb.append("<li><a href='/api/client/session'>session_replay</a></li>");
                sb.append("<li><a href='/api/state/npc'>npc_view_visible</a></li>");
                sb.append("<li><a href='/api/state/object'>object_view_visible</a></li>");
                sb.append("</ul>");
                sb.append("<h2>Available Event Schemas:</h2>");
                sb.append("<ul>");
                schemaRegistry.keySet().stream().sorted().forEach(eventType -> {
                    sb.append("<li><a href='/api/schema/").append(eventType).append("'>")
                            .append(eventType).append("</a></li>");
                });
                sb.append("</ul>");
                ctx.html(sb.toString());
            });

            // JSON endpoints for programmatic access
            pollingServer.get("/api", ctx -> {
                Map<String, Object> index = new ConcurrentHashMap<>();
                index.put("description", "0ZS Competitions Replay System");
                Map<String, String> endpoints = getStringStringMap();
                index.put("endpoints", endpoints);
                index.put("availableEventSchemas", schemaRegistry.keySet().stream().sorted().collect(Collectors.toList()));
                ctx.json(index);
            });

            pollingServer.get("/api/client/session", ctx -> ctx.json(eventCache));

            pollingServer.get("/api/state/npc", ctx -> {
                CompletableFuture<List<Map<String, Object>>> future = new CompletableFuture<>();
                clientThread.invoke(() -> {
                    List<Map<String, Object>> result = new ArrayList<>();
                    wv = client.getTopLevelWorldView();
                    for (NPC npc : wv.npcs()) {
                        Map<String, Object> npcData = new ConcurrentHashMap<>();
                        npcData.put("name", npc.getName());
                        npcData.put("id", npc.getId());
                        npcData.put("boundingBox", getBoundingBox(npc));
                        result.add(npcData);
                    }
                    future.complete(result);
                });
                try {
                    ctx.json(future.get());
                } catch (InterruptedException | ExecutionException e) {
                    ctx.status(500).result("Error processing request on client thread: " + e.getMessage());
                }
            });

            pollingServer.get("/api/state/object", ctx -> {
                CompletableFuture<List<Map<String, Object>>> future = new CompletableFuture<>();
                clientThread.invoke(() -> {
                    List<Map<String, Object>> result = new ArrayList<>();
                    wv = client.getWorldView(-1);
                    Scene scene = wv.getScene();
                    Tile[][][] tiles = scene.getTiles();
                    int plane = wv.getPlane();
                    for (int x = 0; x < Constants.SCENE_SIZE; x++) {
                        for (int y = 0; y < Constants.SCENE_SIZE; y++) {
                            Tile tile = tiles[plane][x][y];
                            if (tile == null) continue;
                            for (GameObject gameObject : tile.getGameObjects()) {
                                if (gameObject == null) continue;
                                Map<String, Object> objectData = new ConcurrentHashMap<>();
                                objectData.put("id", gameObject.getId());
                                objectData.put("boundingBox", getBoundingBox(gameObject));
                                result.add(objectData);
                            }
                        }
                    }
                    future.complete(result);
                });
                try {
                    ctx.json(future.get());
                } catch (InterruptedException | ExecutionException e) {
                    ctx.status(500).result("Error processing request on client thread: " + e.getMessage());
                }
            });

            pollingServer.get("/api/schema/{eventType}", ctx -> {
                String eventType = ctx.pathParam("eventType");
                if (schemaRegistry.containsKey(eventType)) {
                    ctx.json(schemaRegistry.get(eventType));
                } else {
                    ctx.status(404).result("Schema not found for event type: " + eventType);
                }
            });

            log.info("Polling server started on port {}", config.pollPort());
        } catch (Exception e) {
            log.error("Failed to start polling server", e);
        }
    }

    private static @NotNull Map<String, String> getStringStringMap() {
        Map<String, String> endpoints = new ConcurrentHashMap<>();
        endpoints.put("/api", "This JSON index.");
        endpoints.put("/api/client/session", "GET a JSON array of all cached game events.");
        endpoints.put("/api/state/npc", "GET a JSON array of currently visible NPCs.");
        endpoints.put("/api/state/object", "GET a JSON array of currently visible game objects.");
        endpoints.put("/api/schema/{eventType}", "GET the data schema for a specific event type.");
        return endpoints;
    }

    private void registerSchemas() {
        schemaRegistry.put("GAME_STATE_CHANGED", Map.of("gameState", "String"));
        schemaRegistry.put("STAT_CHANGED", Map.of("skill", "String", "xp", "long", "level", "int", "boostedLevel", "int"));
        schemaRegistry.put("ACTOR_DEATH", Map.of("actorName", "String", "boundingBox", "object"));
        schemaRegistry.put("HITSPLAT_APPLIED", Map.of("actorName", "String", "hitsplatType", "int", "amount", "int", "boundingBox", "object"));
        schemaRegistry.put("NPC_SPAWNED", Map.of("npcId", "int", "npcName", "String", "boundingBox", "object"));
        schemaRegistry.put("NPC_DESPAWNED", Map.of("npcId", "int", "npcName", "String"));
        schemaRegistry.put("ITEM_CONTAINER_CHANGED", Map.of("containerId", "int", "itemCount", "int"));
        schemaRegistry.put("CHAT_MESSAGE", Map.of("type", "String", "name", "String", "message", "String"));
        schemaRegistry.put("SESSION_STARTED", Collections.emptyMap());
        schemaRegistry.put("SESSION_CLOSED", Collections.emptyMap());
        schemaRegistry.put("ACTOR_POSITION_UPDATE", Map.of("actorName", "String", "actorId", "int", "boundingBox", "object"));
    }

    private Map<String, Integer> getBoundingBox(Actor actor) {
        return getBoundingBoxForShape(actor != null ? actor.getConvexHull() : null);
    }

    private Map<String, Integer> getBoundingBox(GameObject gameObject) {
        return getBoundingBoxForShape(gameObject != null ? gameObject.getConvexHull() : null);
    }

    private Map<String, Integer> getBoundingBoxForShape(Shape hull) {
        if (hull == null) {
            return Collections.emptyMap();
        }
        Rectangle bounds = hull.getBounds();
        return Map.of("x", bounds.x, "y", bounds.y, "width", bounds.width, "height", bounds.height);
    }

    private void startConnectionCheck() {
        if (temporarilyDisabled || (connectionCheckTask != null && !connectionCheckTask.isDone())) {
            return;
        }
        connected = false;
        log.info("Connection to host lost. Starting connection checker...");

        connectionCheckTask = scheduler.scheduleAtFixedRate(this::checkConnection, 0, config.retryDelaySeconds(), TimeUnit.SECONDS);

        if (config.enableConnectionHandling() && (popupTask == null || popupTask.isDone())) {
            popupTask = scheduler.schedule(this::showConnectionFailedPopup, config.popupDelayMinutes(), TimeUnit.MINUTES);
        }
    }

    private void checkConnection() {
        Request request = new Request.Builder().url(config.postEndpoint()).head().build();
        try {
            Response response = okHttpClient.newCall(request).execute();
            if (response.isSuccessful()) {
                log.info("Successfully reconnected to host.");
                connected = true;
                if (connectionCheckTask != null) {
                    connectionCheckTask.cancel(false);
                }
                if (popupTask != null) {
                    popupTask.cancel(false);
                }
                flushEventCache();
            }
            response.close();
        } catch (IOException e) {
            log.debug("Connection check failed: {}", e.getMessage());
        }
    }

    private void flushEventCache() {
        log.info("Flushing {} events from cache...", eventCache.size());
        for (Map<String, Object> event : eventCache) {
            postEvent(event, false);
        }
    }

    private void showConnectionFailedPopup() {
        if (connected || temporarilyDisabled) {
            return;
        }
        log.warn("Disabling event tracker for this session due to connection failure.");
        this.temporarilyDisabled = true;
        if (connectionCheckTask != null) {
            connectionCheckTask.cancel(true);
        }

        final String message = new ChatMessageBuilder()
                .append(ChatColorType.HIGHLIGHT)
                .append("Event Tracker: Failed to connect to host. The tracker has been disabled for this session to improve performance. You can re-enable it in the plugin settings.")
                .build();

        chatMessageManager.queue(QueuedMessage.builder()
                .type(ChatMessageType.CONSOLE)
                .runeLiteFormattedMessage(message)
                .build());
    }

    private void sendEvent(String eventType, Map<String, Object> eventData) {
        if (temporarilyDisabled) return;

        Map<String, Object> event = new ConcurrentHashMap<>();
        event.put("timestamp", Instant.now().toString());

        String playerName = "N/A";
        Player localPlayer = client.getLocalPlayer();
        if (localPlayer != null && localPlayer.getName() != null) {
            playerName = localPlayer.getName();
        }
        event.put("playerName", playerName);

        event.put("eventType", eventType);
        event.put("eventData", eventData);

        eventCache.add(event);
        if (connected) {
            postEvent(event, false);
        }
    }

    private void sendSessionEvent(String eventType, boolean synchronous) {
        Map<String, Object> event = new ConcurrentHashMap<>();
        event.put("timestamp", Instant.now().toString());
        event.put("playerName", "N/A");
        event.put("eventType", eventType);
        event.put("eventData", Collections.emptyMap());

        eventCache.add(event);
        postEvent(event, synchronous);
    }

    private void postEvent(Map<String, Object> event, boolean synchronous) {
        if (temporarilyDisabled) return;

        String json = gson.toJson(event);
        RequestBody body = RequestBody.create(json, JSON);
        Request request = new Request.Builder().url(config.postEndpoint()).post(body).build();

        if (synchronous) {
            try {
                okHttpClient.newCall(request).execute().close();
                log.info("Sent synchronous event: {}", event.get("eventType"));
            } catch (IOException e) {
                log.error("Error sending synchronous event", e);
            }
        } else {
            okHttpClient.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(@NotNull Call call, IOException e) {
                    if (connected && config.enableConnectionHandling()) {
                        startConnectionCheck();
                    }
                }

                @Override
                public void onResponse(@NotNull Call call, @NotNull Response response) throws IOException {
                    if (!response.isSuccessful()) {
                        log.warn("Unexpected code {} when posting event", response.code());
                    }
                    response.close();
                }
            });
        }
    }

    @Subscribe
    public void onGameTick(GameTick gameTick) {
        if (config.pushActorPositionUpdates()) {
            int wvIdMin = -1; // i have no idea what id we need to use so im going to do a few together.
            int wvIdMax = 1;
            for (int i=wvIdMin; i<=wvIdMax; i++) {
                wv = client.getWorldView(i);
                for (NPC npc : wv.npcs()) {
                    Map<String, Object> data = new ConcurrentHashMap<>();
                    data.put("actorName", npc.getName());
                    data.put("actorId", npc.getId());
                    data.put("boundingBox", getBoundingBox(npc));
                    data.put("worldViewId", "_" + i + "_wvId");
                    sendEvent("ACTOR_POSITION_UPDATE", data);
                }
            }
        }
    }

    @Subscribe
    public void onGameStateChanged(GameStateChanged gameStateChanged) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        data.put("gameState", gameStateChanged.getGameState().toString());
        sendEvent("GAME_STATE_CHANGED", data);
    }

    @Subscribe
    public void onStatChanged(StatChanged statChanged) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        data.put("skill", statChanged.getSkill().getName());
        data.put("xp", statChanged.getXp());
        data.put("level", statChanged.getLevel());
        data.put("boostedLevel", statChanged.getBoostedLevel());
        sendEvent("STAT_CHANGED", data);
    }

    @Subscribe
    public void onActorDeath(ActorDeath actorDeath) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        Actor actor = actorDeath.getActor();
        data.put("actorName", actor.getName());
        data.put("boundingBox", getBoundingBox(actor));
        sendEvent("ACTOR_DEATH", data);
    }

    @Subscribe
    public void onHitsplatApplied(HitsplatApplied hitsplatApplied) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        Actor actor = hitsplatApplied.getActor();
        data.put("actorName", actor.getName());
        data.put("hitsplatType", hitsplatApplied.getHitsplat().getHitsplatType());
        data.put("amount", hitsplatApplied.getHitsplat().getAmount());
        data.put("boundingBox", getBoundingBox(actor));
        sendEvent("HITSPLAT_APPLIED", data);
    }

    @Subscribe
    public void onNpcSpawned(NpcSpawned npcSpawned) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        NPC npc = npcSpawned.getNpc();
        data.put("npcId", npc.getId());
        data.put("npcName", npc.getName());
        data.put("boundingBox", getBoundingBox(npc));
        sendEvent("NPC_SPAWNED", data);
    }

    @Subscribe
    public void onNpcDespawned(NpcDespawned npcDespawned) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        data.put("npcId", npcDespawned.getNpc().getId());
        data.put("npcName", npcDespawned.getNpc().getName());
        sendEvent("NPC_DESPAWNED", data);
    }

    @Subscribe
    public void onItemContainerChanged(ItemContainerChanged itemContainerChanged) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        data.put("containerId", itemContainerChanged.getContainerId());
        data.put("itemCount", itemContainerChanged.getItemContainer().count());
        sendEvent("ITEM_CONTAINER_CHANGED", data);
    }

    @Subscribe
    public void onChatMessage(ChatMessage chatMessage) {
        Map<String, Object> data = new ConcurrentHashMap<>();
        data.put("type", chatMessage.getType().toString());
        data.put("name", chatMessage.getName());
        data.put("message", chatMessage.getMessage());
        sendEvent("CHAT_MESSAGE", data);
    }
}
