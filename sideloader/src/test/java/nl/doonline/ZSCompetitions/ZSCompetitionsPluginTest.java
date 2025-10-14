package nl.doonline.ZSCompetitions;

import net.runelite.client.RuneLite;
import net.runelite.client.externalplugins.ExternalPluginManager;

public class ZSCompetitionsPluginTest {
    public static void main(String[] args) throws Exception {
        ExternalPluginManager.loadBuiltin(ZSCompetitionsPlugin.class);
        RuneLite.main(args);
    }
}