# Permission Denied Messages - Visual Guide

## Overview
When users attempt to access resources they don't have permission for, the system now displays clear, contextual error messages at the top of the page.

## Message Display Features

### 1. Error Message Appearance

**Light Mode:**
- Red background (bg-red-50)
- Red border (border-red-200)
- Red icon and text
- Prominent but not jarring

**Dark Mode:**
- Dark red background (bg-red-900/20)
- Dark red border (border-red-800)
- Light red icon and text
- Consistent with dark theme

### 2. Message Types Supported

#### Error Messages (Red)
- Permission denied
- Access restrictions
- Failed operations

**Example:**
```
🔴 Access Denied: You do not have permission to view Device nodes.
```

#### Warning Messages (Yellow)
- Cautionary notices
- Partial success scenarios

#### Success Messages (Green)
- Successful operations
- Confirmations

#### Info Messages (Blue)
- General information
- Helpful tips

### 3. Interactive Features

**Dismiss Button:**
- X button in top-right corner
- Smooth fade-out animation when clicked
- Removes message from view

**Auto-animations:**
- Fade-in when page loads (300ms)
- Scale-up effect (95% to 100%)
- Smooth transitions

### 4. Contextual Error Messages

The system now provides specific information about what was denied:

**Node Access:**
- "Access Denied: You do not have permission to view Device nodes."
- "Access Denied: You do not have permission to create Network nodes."
- "Access Denied: You do not have permission to modify Interface nodes."
- "Access Denied: You do not have permission to delete Server nodes."

**Staff-Only Access:**
- "Access Denied: Only staff members can view the user list."
- "Access Denied: Only staff members can view groups."

### 5. Smart Redirect Logic

**Before:** Always redirected to dashboard
**After:** 
- If coming from within the app → redirects back to referring page
- If coming from external → redirects to dashboard
- Preserves user context when possible

## Technical Implementation

### Message Structure
```html
<div class="message-alert">
    <icon> Message text <dismiss-button>
</div>
```

### Message Positioning
- Appears at top of main content area
- Below header, above page content
- Full width with proper spacing
- Doesn't break layout

### Accessibility
- Proper ARIA roles
- Keyboard dismissible (implicit via Alpine.js)
- High contrast colors
- Clear visual hierarchy

## User Experience Improvements

### Before
1. User clicks on restricted resource
2. Silently redirects to dashboard
3. User is confused why they're on dashboard
4. No indication of what went wrong

### After
1. User clicks on restricted resource
2. Redirects to dashboard (or back)
3. **Clear error message displayed**: "Access Denied: You do not have permission to view Device nodes."
4. User understands exactly what happened
5. Can dismiss message when ready

## Testing Scenarios

To verify the implementation:

1. **Test as regular user without permissions:**
   - Try to access node list → See "Access Denied: You do not have permission to view [Type] nodes."
   - Try to create node → See "Access Denied: You do not have permission to create [Type] nodes."
   - Try to edit node → See "Access Denied: You do not have permission to modify [Type] nodes."
   - Try to delete node → See "Access Denied: You do not have permission to delete [Type] nodes."

2. **Test staff-only pages:**
   - Non-staff user tries to view users → See "Access Denied: Only staff members can view the user list."
   - Non-staff user tries to view groups → See "Access Denied: Only staff members can view groups."

3. **Test message display:**
   - Verify message appears at top of page
   - Check both light and dark mode
   - Verify dismiss button works
   - Check animations are smooth

4. **Test redirect logic:**
   - From sidebar link → Should redirect to dashboard with message
   - From within node detail → Should go back to previous page with message

## Browser Compatibility

- **Chrome/Edge:** Full support
- **Firefox:** Full support
- **Safari:** Full support (Alpine.js v3+)
- **Mobile browsers:** Responsive and touch-friendly

## Future Enhancements

Potential improvements:
- Toast notifications for less critical messages
- Auto-dismiss after X seconds
- Sound/vibration feedback on mobile
- Message history/log
- Customize redirect per message type
