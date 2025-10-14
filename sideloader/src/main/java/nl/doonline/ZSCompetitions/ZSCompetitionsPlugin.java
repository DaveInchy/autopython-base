package nl.doonline.ZSCompetitions;

import com.google.inject.Provides;
import lombok.extern.slf4j.Slf4j;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.EventBus;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;

import javax.inject.Inject;

@Slf4j
@PluginDescriptor(
        name = "0ZS Competitions",
        description = "A plugin for clan competitions and events.",
        tags = {"clan", "event", "competition", "0zs"}
)
public class ZSCompetitionsPlugin extends Plugin {

    @Inject
    private EventBus eventBus;

    @Inject
    private EventTrackerService eventTrackerService;

    @Override
    protected void startUp() throws Exception {
        log.info("0ZS Competitions plugin started!");
        eventBus.register(eventTrackerService);
        eventTrackerService.start();
    }

    @Override
    protected void shutDown() throws Exception {
        eventTrackerService.stop();
        eventBus.unregister(eventTrackerService);
        log.info("0ZS Competitions plugin stopped!");
    }

    @Provides
    EventTrackerConfig provideConfig(ConfigManager configManager) {
        return configManager.getConfig(EventTrackerConfig.class);
    }
}
