# Sidebar Highlight Fix

## Issue
User reported: "the sidebar highlight of the type selected is not changing anymore on click to a new type"

After fixing the header update issue with HTMX OOB swaps, the sidebar navigation worked but the visual highlight didn't follow the selected item.

## Root Cause

### Server-Side Template Logic
The sidebar uses Django template logic to set active state CSS classes:

```django
<a ... :class="darkMode ? (
    '{% if request.resolver_match.kwargs.label == label %}bg-indigo-600 text-white{% else %}text-gray-300 hover:bg-gray-700{% endif %}'
) : (
    '{% if request.resolver_match.kwargs.label == label %}bg-indigo-50 text-indigo-700{% else %}text-gray-700 hover:bg-gray-50{% endif %}'
)">
```

This Django template code is evaluated once on the server when the page is initially rendered. It checks `request.resolver_match.kwargs.label` to determine which item should be highlighted.

### Why It Stopped Working
1. Initially loads: `/nodes/Interface`
   - Django renders sidebar with Interface highlighted ✅

2. User clicks "Network" in sidebar
   - HTMX intercepts with `hx-get="/nodes/Network"`
   - HTMX updates `#main-content` with new data
   - HTMX pushes URL with `hx-push-url="true"` → `/nodes/Network`
   - Header updates via OOB swap ✅
   - **BUT** sidebar HTML is NOT re-rendered
   - Django template logic already evaluated (Interface is still highlighted) ❌

3. Result: URL is `/nodes/Network`, header shows "Network Nodes", but sidebar still highlights "Interface"

## Solution

### Client-Side JavaScript
Added JavaScript to dynamically update sidebar highlights when navigation occurs:

```javascript
function updateSidebarHighlight() {
    // 1. Get current URL path
    const path = window.location.pathname;  // e.g., "/nodes/Network"
    
    // 2. Extract label from path
    const match = path.match(/\/nodes\/([^\/]+)/);
    const currentLabel = match[1];  // e.g., "Network"
    
    // 3. Check dark mode state
    const darkMode = document.documentElement.classList.contains('dark');
    
    // 4. Update all sidebar links
    document.querySelectorAll('aside a[href*="/nodes/"]').forEach(link => {
        const linkPath = link.getAttribute('href');
        const linkLabel = linkPath.match(/\/nodes\/([^\/]+)/)[1];
        const isActive = linkLabel === currentLabel;
        
        // Remove old classes
        link.classList.remove(
            'bg-indigo-600', 'text-white',           // Dark active
            'text-gray-300', 'hover:bg-gray-700',     // Dark inactive
            'bg-indigo-50', 'text-indigo-700',        // Light active
            'text-gray-700', 'hover:bg-gray-50'       // Light inactive
        );
        
        // Add new classes based on state
        if (isActive) {
            if (darkMode) {
                link.classList.add('bg-indigo-600', 'text-white');
            } else {
                link.classList.add('bg-indigo-50', 'text-indigo-700');
            }
        } else {
            if (darkMode) {
                link.classList.add('text-gray-300', 'hover:bg-gray-700');
            } else {
                link.classList.add('text-gray-700', 'hover:bg-gray-50');
            }
        }
    });
}
```

### Event Listeners

**1. HTMX Navigation**
```javascript
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target && evt.detail.target.id === 'main-content') {
        updateSidebarHighlight();
    }
});
```
Fires after HTMX updates content. Only updates highlight when main content is swapped (not for other HTMX operations).

**2. Browser Navigation (Back/Forward)**
```javascript
window.addEventListener('popstate', function() {
    updateSidebarHighlight();
});
```
Ensures highlight updates when user uses browser back/forward buttons.

**3. Initial Page Load**
```javascript
document.addEventListener('DOMContentLoaded', function() {
    updateSidebarHighlight();
});
```
Sets correct initial state on page load.

## Flow Diagram

### Before Fix
```
User clicks "Network" in sidebar
    ↓
HTMX intercepts click
    ↓
HTMX requests /nodes/Network
    ↓
HTMX swaps #main-content
    ↓
HTMX pushes URL → /nodes/Network
    ↓
Header updates (OOB swap) ✅
    ↓
Sidebar HTML unchanged ❌
    ↓
Interface still highlighted ❌
```

### After Fix
```
User clicks "Network" in sidebar
    ↓
HTMX intercepts click
    ↓
HTMX requests /nodes/Network
    ↓
HTMX swaps #main-content
    ↓
HTMX pushes URL → /nodes/Network
    ↓
Header updates (OOB swap) ✅
    ↓
htmx:afterSwap event fires
    ↓
updateSidebarHighlight() runs
    ↓
Parses URL → "Network"
    ↓
Updates all sidebar link classes
    ↓
Network is highlighted ✅
Interface unhighlighted ✅
```

## CSS Classes Reference

### Light Mode
**Active Link**:
- Background: `bg-indigo-50` (light indigo)
- Text: `text-indigo-700` (dark indigo)

**Inactive Link**:
- Text: `text-gray-700` (dark gray)
- Hover: `hover:bg-gray-50` (light gray background)

### Dark Mode
**Active Link**:
- Background: `bg-indigo-600` (bright indigo)
- Text: `text-white` (white)

**Inactive Link**:
- Text: `text-gray-300` (light gray)
- Hover: `hover:bg-gray-700` (darker gray background)

## Implementation Details

### URL Pattern Matching
```javascript
const match = path.match(/\/nodes\/([^\/]+)/);
```
Matches URLs like:
- `/nodes/Interface` → captures `"Interface"`
- `/nodes/Network` → captures `"Network"`
- `/nodes/IP_Address` → captures `"IP_Address"`

### Dark Mode Detection
```javascript
const darkMode = document.documentElement.classList.contains('dark');
```
Checks if the `<html>` element has the `dark` class, which is managed by Alpine.js in the template.

### Link Selection
```javascript
document.querySelectorAll('aside a[href*="/nodes/"]')
```
Selects all links inside the `<aside>` element that have `/nodes/` in their href. This ensures we only update navigation links, not other links on the page.

## Edge Cases Handled

1. **Page Load**: DOMContentLoaded ensures correct initial state
2. **HTMX Navigation**: htmx:afterSwap updates after content swap
3. **Browser Navigation**: popstate handles back/forward buttons
4. **Dark Mode**: Checks mode state and applies appropriate classes
5. **Non-matching URLs**: Returns early if URL doesn't match pattern
6. **Multiple HTMX Swaps**: Only updates on #main-content swaps

## Testing Scenarios

### Scenario 1: Navigate Between Types
1. Start on Interface
   - Sidebar: Interface highlighted ✅
2. Click Network
   - URL changes to /nodes/Network ✅
   - Header: "Network Nodes" ✅
   - Sidebar: Network highlighted ✅
   - Interface unhighlighted ✅
3. Click IP_Address
   - URL changes to /nodes/IP_Address ✅
   - Header: "IP_Address Nodes" ✅
   - Sidebar: IP_Address highlighted ✅
   - Network unhighlighted ✅

### Scenario 2: Browser Navigation
1. Navigate: Interface → Network → IP_Address
2. Click browser back button
   - URL: /nodes/Network ✅
   - Sidebar: Network highlighted ✅
3. Click browser back button again
   - URL: /nodes/Interface ✅
   - Sidebar: Interface highlighted ✅
4. Click browser forward button
   - URL: /nodes/Network ✅
   - Sidebar: Network highlighted ✅

### Scenario 3: Dark Mode Toggle
1. On Interface page in light mode
   - Highlight: Light indigo background ✅
2. Toggle to dark mode
   - Highlight: Bright indigo background ✅
   - Other links: Light gray text ✅
3. Navigate to Network
   - Highlight updates ✅
   - Still in dark mode styles ✅

### Scenario 4: Direct URL Access
1. Type `/nodes/Network` in address bar
2. Page loads
   - DOMContentLoaded fires
   - updateSidebarHighlight() runs
   - Network is highlighted ✅

## Benefits

1. **Immediate Visual Feedback**: Users see which page they're on
2. **Consistent with URL**: Highlight always matches URL
3. **Works with Browser Controls**: Back/forward buttons update highlight
4. **No Server Changes**: Pure client-side solution
5. **Framework Compatible**: Works with HTMX, Alpine.js, and Tailwind CSS
6. **Minimal Performance Impact**: Only runs on navigation events
7. **Mode Aware**: Automatically handles light/dark mode

## Alternative Solutions Considered

### Option 1: Re-render Sidebar via HTMX OOB
- Add sidebar to OOB swap response
- **Rejected**: Would lose Alpine.js state (open/closed categories)
- More server overhead
- More HTML to transfer

### Option 2: Alpine.js Reactive Property
- Add Alpine property for active label
- Sync with URL on navigation
- **Rejected**: More complex, mixes concerns
- Would need to modify existing Alpine component

### Option 3: CSS-only Solution
- Use `:target` or `:visited` pseudo-classes
- **Rejected**: Can't detect URL changes via HTMX
- Limited browser support for advanced selectors

### Option 4: JavaScript (Chosen) ✅
- Simple event-driven approach
- No framework modifications needed
- Works with existing structure
- Easy to understand and maintain

## Files Modified
- `cmdb/templates/base.html` - Added 68 lines of JavaScript

## Summary
A simple client-side JavaScript solution that:
- Listens for HTMX navigation events
- Parses the current URL
- Updates sidebar CSS classes dynamically
- Maintains visual consistency between URL, header, and sidebar
- Works with all navigation methods (clicks, back/forward, direct URLs)

**Result**: Sidebar highlight now correctly follows the selected node type! 🎉
