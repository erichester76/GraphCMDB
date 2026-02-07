# Sidebar Highlight Fix - Second Attempt

## The Problem
After the first fix attempt, the sidebar highlight was still not updating when clicking different node types, though it showed correctly on page load.

## Why the First Fix Didn't Work

### The Alpine.js Conflict
The sidebar links had BOTH:
1. **Alpine.js `:class` binding** (reactive)
2. **JavaScript classList manipulation** (our fix)

```django
<a class="flex items-center..."
   :class="darkMode ? ('{% if request.resolver_match.kwargs.label == label %}bg-indigo-600 text-white{% else %}text-gray-300 hover:bg-gray-700{% endif %}') : (...)">
```

### The Conflict
Alpine.js's `:class` binding is **reactive** - it continuously watches for changes and re-applies classes. Here's what was happening:

1. ✅ Page loads with correct initial highlight (Django template)
2. ✅ User clicks "Network" in sidebar
3. ✅ HTMX swaps content
4. ✅ `htmx:afterSwap` event fires
5. ✅ Our JavaScript runs `updateSidebarHighlight()`
6. ✅ JavaScript updates classList on links
7. ❌ **Alpine.js re-evaluates `:class` binding**
8. ❌ **Alpine applies old Django template logic**
9. ❌ Our JavaScript changes are overwritten!

### Why It Appeared to Work Initially
When testing manually with browser DevTools, you could:
- Inspect the element
- See the classes change in real-time
- But Alpine would revert them milliseconds later

### The Trigger for Alpine Re-evaluation
Alpine.js re-evaluates `:class` bindings when:
- Reactive properties change (like `darkMode`)
- Parent component updates
- DOM mutations occur
- HTMX content changes

Since our `:class` references `darkMode` (an Alpine reactive property), even small changes could trigger re-evaluation.

## The Real Fix

### 1. Remove Alpine.js `:class` Binding
Changed from:
```django
class="flex items-center px-3 py-2 text-sm font-medium rounded-md group-hover:pr-20"
:class="darkMode ? ('{% if request.resolver_match.kwargs.label == label %}bg-indigo-600 text-white{% else %}text-gray-300 hover:bg-gray-700{% endif %}') : ('{% if request.resolver_match.kwargs.label == label %}bg-indigo-50 text-indigo-700{% else %}text-gray-700 hover:bg-gray-50{% endif %}')"
```

To:
```django
class="flex items-center px-3 py-2 text-sm font-medium rounded-md group-hover:pr-20 {% if request.resolver_match.kwargs.label == label %}bg-indigo-50 text-indigo-700 dark:bg-indigo-600 dark:text-white{% else %}text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700{% endif %}"
```

**Key changes**:
- ❌ Removed Alpine `:class` binding entirely
- ✅ Moved Django template logic into static `class` attribute
- ✅ Used Tailwind's `dark:` variant for dark mode styles

### 2. Use Tailwind's dark: Variant
Instead of checking dark mode in JavaScript and conditionally applying classes:

**Before (complex)**:
```javascript
const darkMode = document.documentElement.classList.contains('dark');

if (isActive) {
    if (darkMode) {
        link.classList.add('bg-indigo-600', 'text-white');
    } else {
        link.classList.add('bg-indigo-50', 'text-indigo-700');
    }
}
```

**After (simple)**:
```javascript
if (isActive) {
    // Apply both light and dark classes - Tailwind handles which shows
    link.classList.add('bg-indigo-50', 'text-indigo-700', 'dark:bg-indigo-600', 'dark:text-white');
}
```

### How Tailwind's dark: Variant Works
When you add classes like `dark:bg-indigo-600`:
- Tailwind generates CSS: `.dark .dark\:bg-indigo-600 { background-color: ... }`
- If `<html class="dark">`, the dark variant styles apply
- If `<html>` has no dark class, light styles apply
- This is pure CSS - no JavaScript conflicts!

### 3. Updated JavaScript
The new `updateSidebarHighlight()` function:

```javascript
function updateSidebarHighlight() {
    const path = window.location.pathname;
    const match = path.match(/\/nodes\/([^\/]+)/);
    if (!match) return;
    
    const currentLabel = match[1];
    
    document.querySelectorAll('aside a[href*="/nodes/"]').forEach(link => {
        const linkPath = link.getAttribute('href');
        const linkMatch = linkPath.match(/\/nodes\/([^\/]+)/);
        
        if (linkMatch) {
            const linkLabel = linkMatch[1];
            const isActive = linkLabel === currentLabel;
            
            // Remove all state classes (including dark: variants)
            link.classList.remove(
                'bg-indigo-600', 'text-white',
                'text-gray-300', 'hover:bg-gray-700',
                'bg-indigo-50', 'text-indigo-700',
                'text-gray-700', 'hover:bg-gray-50',
                'dark:bg-indigo-600', 'dark:text-white',
                'dark:text-gray-300', 'dark:hover:bg-gray-700'
            );
            
            // Add both light and dark mode classes
            if (isActive) {
                link.classList.add(
                    'bg-indigo-50', 'text-indigo-700',      // Light mode
                    'dark:bg-indigo-600', 'dark:text-white'  // Dark mode
                );
            } else {
                link.classList.add(
                    'text-gray-700', 'hover:bg-gray-50',           // Light mode
                    'dark:text-gray-300', 'dark:hover:bg-gray-700' // Dark mode
                );
            }
        }
    });
}
```

## Debug Logging Added
Temporarily added console.log statements to diagnose:

```javascript
console.log('HTMX afterSwap event', evt.detail);
console.log('updateSidebarHighlight - current path:', path);
console.log('Current label:', currentLabel);
console.log('Found', links.length, 'sidebar links');
console.log(`Link ${linkLabel}: isActive=${isActive}`);
console.log('Sidebar highlight update complete');
```

These logs help verify:
1. ✅ Events are firing
2. ✅ Correct URL is parsed
3. ✅ Links are found
4. ✅ Active state is correct
5. ✅ Classes are applied

## The Flow Now

### User Clicks "Network"
```
1. HTMX intercepts click
   ↓
2. HTMX requests /nodes/Network
   ↓
3. Server responds with content + header (OOB)
   ↓
4. HTMX swaps #main-content
   ↓
5. HTMX swaps #page-title and #header-actions (OOB)
   ↓
6. HTMX pushes URL → /nodes/Network
   ↓
7. htmx:afterSwap event fires
   ↓
8. updateSidebarHighlight() runs
   ↓
9. Parses URL → "Network"
   ↓
10. Finds all sidebar links
   ↓
11. For each link:
    - Checks if link.label === currentLabel
    - Removes old classes
    - Adds new classes (with dark: variants)
   ↓
12. ✅ Network highlighted
    ✅ Interface unhighlighted
    ✅ No Alpine.js interference!
```

### Dark Mode Toggle
```
1. User clicks dark mode button
   ↓
2. Alpine.js updates darkMode property
   ↓
3. Alpine.js adds/removes 'dark' class on <html>
   ↓
4. Tailwind CSS automatically applies/removes dark: variant styles
   ↓
5. ✅ Highlights show correct colors
   ✅ No JavaScript needed!
```

## Why This Fix Works

### No Reactive Binding Conflicts
- **Before**: Alpine `:class` binding fought with JavaScript
- **After**: No Alpine binding on these elements

### Separation of Concerns
- **Initial state**: Django template generates correct classes
- **Navigation**: JavaScript updates classes
- **Dark mode**: Tailwind CSS handles via dark: variants
- **No overlap**: Each system has its own responsibility

### Pure CSS Dark Mode
- Tailwind's `dark:` variant uses CSS selectors
- No JavaScript checks needed
- Changes instant and conflict-free
- Works even if JavaScript disabled (for initial state)

## Testing Checklist

With debug logging, verify:
- [ ] Console shows "HTMX afterSwap event" when clicking links
- [ ] Console shows correct current path and label
- [ ] Console shows "Found N sidebar links"
- [ ] Console shows correct isActive state for each link
- [ ] Visual: Correct link is highlighted
- [ ] Visual: Other links are unhighlighted
- [ ] Visual: Dark mode toggle changes highlight colors
- [ ] Visual: Browser back button updates highlight

## Cleanup

Once confirmed working, remove debug console.log statements:
```javascript
// Remove these lines:
console.log('HTMX afterSwap event', evt.detail);
console.log('Updating sidebar highlight after main-content swap');
console.log('updateSidebarHighlight - current path:', path);
console.log('No match found in path');
console.log('Current label:', currentLabel);
console.log('Found', links.length, 'sidebar links');
console.log(`Link ${linkLabel}: isActive=${isActive}`);
console.log('Sidebar highlight update complete');
console.log('Popstate event - updating sidebar');
console.log('DOMContentLoaded - initializing sidebar highlight');
```

## Summary

The real problem wasn't the JavaScript logic - it was **Alpine.js fighting JavaScript** for control of the classes. By removing the Alpine `:class` binding and using Tailwind's `dark:` variant, we eliminated the conflict and let each system do what it does best:

- **Django**: Generate initial correct state
- **JavaScript**: Update state on navigation
- **Tailwind CSS**: Handle dark mode styling
- **Alpine.js**: Manage other UI state (sidebar open/close, modals, etc.)

The fix is actually simpler than the first attempt because we're not manually managing dark mode - Tailwind does it for us! 🎉
