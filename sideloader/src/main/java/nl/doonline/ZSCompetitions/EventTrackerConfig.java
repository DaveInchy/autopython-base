package nl.doonline.ZSCompetitions;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;
import net.runelite.client.config.Units;

@ConfigGroup("zscompetitions")
public interface EventTrackerConfig extends Config {
    @ConfigItem(
            keyName = "postEndpoint",
            name = "Event POST Endpoint",
            description = "The full URL to POST event data to.",
            position = 1
    )
    default String postEndpoint() {
        return "http://localhost:1664/post";
    }

    @ConfigItem(
            keyName = "pollPort",
            name = "Poll Endpoint Port",
            description = "The local port to run the polling server on.",
            position = 2
    )
    default int pollPort() {
        return 1464;
    }

    @ConfigItem(
            keyName = "enableConnectionHandling",
            name = "Enable Connection Handling",
            description = "Enable retry and pop-up notifications on connection failure.",
            position = 3
    )
    default boolean enableConnectionHandling() {
        return true;
    }

    @ConfigItem(
            keyName = "retryDelaySeconds",
            name = "Connection Retry Delay",
            description = "Seconds between each attempt to reconnect to the host.",
            position = 4
    )
    @Units(Units.SECONDS)
    default int retryDelaySeconds() {
        return 10;
    }

    @ConfigItem(
            keyName = "popupDelayMinutes",
            name = "Popup Delay",
            description = "Minutes to wait before showing a connection failure pop-up.",
            position = 5
    )
    @Units(Units.MINUTES)
    default int popupDelayMinutes() {
        return 1;
    }

    @ConfigItem(
            keyName = "pushActorPositionUpdates",
            name = "Push Actor Position Updates",
            description = "If enabled, sends an event for every actor's position on every game tick. WARNING: Creates a lot of data.",
            position = 6
    )
    default boolean pushActorPositionUpdates() {
        return false;
    }
}
