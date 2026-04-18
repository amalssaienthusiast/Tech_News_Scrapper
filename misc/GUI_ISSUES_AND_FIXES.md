# Tech News Scraper GUI - Issues & Fixes Summary

## Critical Issues Identified

### 1. Missing `main_content` and `mode_label` Attributes

**Problem:** Lines 765/795/796/799 reference `hasattr(self, 'main_content')` and `hasattr(self, 'mode_label')`, but these attributes are never created in `__init__`.

**Location:** `gui/app.py` lines 765, 795, 796, 799

**Fix:** Add these attributes to `__init__` method:

```python
# In __init__ method, after line 528 (after self._bind_keyboard_shortcuts()), add:

# Mode label for user/developer mode indicator
self.mode_label = tk.Label(self.root, text="👤 User Mode", 
                                font=get_font("sm"), fg=THEME.cyan, bg=THEME.bg)

# Main content frame for user mode
self.main_content = tk.Frame(self.root, bg=THEME.bg, padx=25, pady=20)
```

### 2. `get_font` Function Signature Issues

**Problem:** The `get_font` function signature has default parameters, making them keyword-only in Python 3.8+:
```python
def get_font(size: str = "base", weight: str = "normal", mono: bool = False) -> tuple:
```

But code calls it with positional arguments:
```python
get_font("sm", "bold", mono=True)  # Wrong - mono is passed as positional arg
```

**Locations:** Multiple files call `get_font` with `mono=True` as the 3rd positional argument.

**Fix Options:**

**Option A (Recommended):** Update all calls to use keyword arguments:
```python
# Change all calls from:
get_font("sm", "bold", mono=True)
# To:
get_font(size="sm", weight="bold", mono=True)
```

**Option B:** Update `get_font` function to accept positional arguments:
```python
# In gui/theme.py, change signature to:
def get_font(size: str = "base", weight: str = "normal", *, mono: bool = False) -> tuple:
    # The * makes all keyword-only, allowing positional args
    family = FONTS.mono if mono else FONTS.fallback
    return (family, size, weight)
```

### 3. Incomplete `_build_ui` Method

**Problem:** The `_build_ui` method (line 109) calls `self._build_ui()` but doesn't create `main_content_frame` or `results_frame` properly for the main application.

**Expected:** Should create:
- `self.results_frame` - Main content area for articles
- `self.main_content_frame` - For user mode content
- `self._progress_frame` - For loading states

### 4. Import Issues

**Problem:** Some modules try to import packages that may not exist:
- `advanced_web_scraper.PyBrowser` - Rust browser (may not be compiled)
- `src.resilience` - Optional resilience module

**Fix:** Wrap imports in try/except blocks:

```python
try:
    import advanced_web_scraper
    rust_browser = advanced_web_scraper.PyBrowser("headless")
except ImportError:
    logger.warning("Rust extension not found, falling back to Python")
    rust_browser = None
```

### 5. Type Annotation Issues

**Problem:** LSP errors about `AsyncRunner` and `TechNewsOrchestrator` types.

**Fix:** Update type annotations or use `Optional` imports:

```python
from typing import Optional

# Change type hints from:
async_runner: AsyncRunner
orchestrator: TechNewsOrchestrator
# To:
async_runner: Optional[AsyncRunner]
orchestrator: Optional[TechNewsOrchestrator]
```

## Quick Fixes to Apply

### Fix 1: Add Missing Attributes

**File:** `gui/app.py`

**In `__init__` method (after line 528), add:**
```python
# Add near the end of __init__, after self._bind_keyboard_shortcuts()

# Mode labels
self.mode_label = tk.Label(self.root, text="👤 User Mode", 
                                font=get_font(size="sm"), fg=THEME.cyan)
self.mode_label.place(relx=0.5, rely=0.5)

# Main content frame (for user mode)
self.main_content = tk.Frame(self.root, bg=THEME.bg, padx=25, pady=20)
self.main_content.pack(fill=tk.BOTH, expand=True)

# Store main content frame reference for toggling
self._main_content_frame = self.main_content  # Keep reference for switching
```

### Fix 2: Update `get_font` Calls

**Files to update:** `gui/app.py`, `gui/developer_dashboard.py`, `gui/widgets/log_panel.py`, `gui/security.py`, `gui/popups/dialogs.py`

**Example fix:**
```python
# Find all instances of get_font with mono=True and fix them

# From:
get_font("sm", "bold", mono=True)

# To:
get_font(size="sm", weight="bold", mono=True)
```

**Use global search and replace:**
```bash
# Search for problematic pattern
grep -r "get_font.*, mono=True" gui/

# Replace all occurrences with correct keyword syntax
sed -i 's/get_font(\([^,]*), mono=True\)/get_font(size="\1", weight="\2", mono=True)/g' gui/
```

### Fix 3: Handle Missing Rust Extension

**File:** `gui/app.py`

**Wrap in try/except:**
```python
# Around line 690 in __init__, add:
try:
    from src.bypass import PyBrowser
    rust_browser = PyBrowser("headless")
except ImportError:
    logger.warning("Rust extension not available, using Python browser")
    rust_browser = None

# Also update lines that use rust_browser to handle None case
```

### Fix 4: Create Main Content Frame

**File:** `gui/app.py`

**In `_build_ui` method (around line 200), add:**
```python
# After the separator line, add:

# Main content area
self.results_frame = tk.Frame(self.root, bg=THEME.bg, padx=25, pady=20)
self.results_frame.pack(fill=tk.BOTH, expand=True)
self.results_frame.pack_propagate(False)

# Reference for mode switching
self._main_content_frame = self.results_frame
```

## Files Requiring Updates

### High Priority
1. **gui/app.py** - Add missing attributes, fix _build_ui, handle Rust import
2. **gui/theme.py** - Update get_font signature
3. **gui/__init__.py** - ✅ Already fixed (DeveloperDashboard exported)
4. **gui/developer_dashboard.py** - Fix async_runner type hints
5. **gui/widgets/*.py** - Fix get_font calls to use keyword args

### Medium Priority
1. **All files using get_font** - Update calls to use keyword arguments
2. **Files with optional imports** - Add try/except blocks

## Automated Fix Script

```python
#!/usr/bin/env python3
"""
Fix GUI issues automatically.
"""

import re
import subprocess

def fix_get_font_calls(file_path: str) -> None:
    """Fix get_font calls to use keyword arguments."""
    print(f"Fixing get_font calls in {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to find problematic calls
    # Matches: get_font("sm", "bold", "mono=True) or similar
    pattern = r'get_font\([^,]*),\s*mono=True\s*\)'
    
    def replace_match(match):
        args = match.group(1)  # Extract the arguments
        
        # Convert to keyword arguments
        return f'get_font({", "}, ".join([
            f'size="{arg}", ' 
            f'weight="{arg}"'
        ])
    
    new_content = re.sub(pattern, replace_match, content)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed {len(re.findall(pattern, content))} get_font calls")

if __name__ == "__main__":
    # Fix main app
    fix_get_font_calls("gui/app.py")
    
    # Fix developer dashboard
    fix_get_font_calls("gui/developer_dashboard.py")
    
    # Fix log panel
    fix_get_font_calls("gui/widgets/log_panel.py")
    
    # Fix security
    fix_get_font_calls("gui/security.py")
    
    # Fix dialog
    fix_get_font_calls("gui/popups/dialogs.py")
    
    print("✅ All get_font calls fixed!")
```

## Testing After Fixes

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Check for missing attributes:**
   - Verify mode label appears
   - Verify main content frame is created
   - Check for any runtime errors

3. **Test mode switching:**
   - Try Ctrl+M, F11, F12 shortcuts
   - Verify developer dashboard opens

## Manual Testing Steps

1. Start the app: `python main.py`
2. Check if mode label shows
3. Try switching to developer mode (if available)
4. Check if main content area appears
5. Verify no AttributeError about missing attributes

## Common Error Patterns

### AttributeError: 'NoneType' object has no attribute 'X'

**Causes:**
1. Optional type is None (module not imported)
2. Class not initialized (attribute not set in __init__)
3. Frame not created before use

**Solutions:**
1. Add proper `__init__` initialization for all attributes
2. Check imports and handle ImportError
3. Use hasattr checks with proper fallbacks

### ImportError: "No module named 'X'"

**Causes:**
1. Module not in Python path
2. Typo in import statement
3. Module requires dependencies not installed

**Solutions:**
1. Verify module exists
2. Check requirements.txt for dependencies
3. Add proper sys.path setup
4. Install missing packages

## Summary

- ✅ DeveloperDashboard now exported from gui/__init__.py
- ⚠️ `get_font` function signature causes issues with positional arguments
- ⚠️ `main_content` and `mode_label` attributes missing from TechNewsGUI.__init__
- ⚠️ `_build_ui` method incomplete - doesn't create main content area
- ⚠️ Some optional imports may fail if packages missing

## Next Steps

1. **Run the automated fix script:** `python fix_gui_issues.py`
2. **Add missing attributes manually** if automated fix doesn't work
3. **Test the application** thoroughly
4. **Fix remaining issues** as they appear during runtime

---

**Created:** January 31, 2026
**Purpose:** Document and fix critical GUI issues
