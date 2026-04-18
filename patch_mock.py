import os
import glob

# For all widgets, if they have a demo timer, we comment it out.
# Or better, we just comment out `self._timer.start` if the file imports random for simulation.

files = glob.glob("gui_qt/widgets/*.py") + glob.glob("gui_qt/dialogs/*.py")

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()
    
    if "import random" in content or "random." in content:
        # It's doing random simulation. Let's find timer starts and disable them.
        new_content = []
        for line in content.split("\n"):
            if "._timer.start(" in line or "._demo_timer.start(" in line or "._pulse_timer.start(" in line:
                if "self._update_timer.start(" not in line:  # don't touch orchestrator poller
                    line = "        # " + line.lstrip() + "  # DEMO TIMER DISABLED BY OPENCODE"
            new_content.append(line)
        
        with open(file_path, "w") as f:
            f.write("\n".join(new_content))
            
print("Done patching timers")
