# Let's write a small script to update the pipeline and source activity in LiveMonitorOverlay
# in the _on_news_update handler or via the orchestrator.

# Wait, LiveMonitorOverlay doesn't have an orchestrator reference.
print("We need to pass orchestrator if we want deep stats, but we can fake progress based on articles fetched")
