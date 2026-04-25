---
name: paint-objects
description: Use when drawing, updating, or managing the lifecycle of graphical chart objects in MQL5. Follow local rules for separation of concerns (keep calculation logic separate from rendering), optimal object updating, property management, and forcing visual redraws.
---

# Paint Objects (MQL5 Rendering)

Use this skill when generating or modifying MQL5 code that involves `ObjectCreate`, `ObjectMove`, `ObjectSetInteger`, `ObjectDelete`, or any other visual chart manipulation. 

## 1. Separation of Concerns
Never mix complex pattern detection logic (e.g., finding gaps, calculating indicators) with rendering logic.
- Detection functions should return structures with data (prices, times, validity).
- Rendering functions should take those structures and purely handle the MQL5 Object API.

## 2. Object Choice
Choose the MQL5 object type (`ENUM_OBJECT`) that strictly matches the visual requirement.
- **Zones/Areas:** Use `OBJ_RECTANGLE`. Do not simulate areas using multiple trend lines.
- **Levels/Targets:** Use `OBJ_HLINE` (infinite) or `OBJ_TREND` with `OBJPROP_RAY_RIGHT = false` (finite segment).
- **Markers/Icons:** Use `OBJ_ARROW` with appropriate Wingdings codes.

## 3. Creation and Updating (The MQL5 Way)
MQL5 handles object updates efficiently. If `ObjectCreate` is called with the name of an object that *already exists*, it automatically updates its anchor points (coordinates). 

Use the `ObjectFind` pattern only when you need to set cosmetic properties (colors, fills, widths) strictly upon initial creation, saving processing time on subsequent updates:

```mql5
// 1. Define unique, deterministic names
string obj_name = "Zone_" + IntegerToString(zone_id);

// 2. Check existence to apply initial formatting
if(ObjectFind(chart_id, obj_name) < 0) {
    // Object does not exist, create it and set static properties
    if(ObjectCreate(chart_id, obj_name, OBJ_RECTANGLE, sub_window, time1, price1, time2, price2)) {
        ObjectSetInteger(chart_id, obj_name, OBJPROP_COLOR, clrBlue);
        ObjectSetInteger(chart_id, obj_name, OBJPROP_FILL, true);
        ObjectSetInteger(chart_id, obj_name, OBJPROP_BACK, true);
    }
} else {
    // Object exists, just update its coordinates
    ObjectMove(chart_id, obj_name, 0, time1, price1);
    ObjectMove(chart_id, obj_name, 1, time2, price2);
    // Alternatively, ObjectCreate(...) with the same name achieves the same coordinate update.
}
```

## 4. Time Coordinates (datetime)
Object anchor points require `datetime`. If your logic uses bar indexes (shift), convert the index to time before rendering:
`datetime time_val = iTime(_Symbol, _Period, bar_index);`

## 5. Visibility and Redrawing
Commands to create or modify objects are asynchronous and placed in a chart queue. 
- **Always call `ChartRedraw(chart_id)`** at the end of your rendering block to force the visual update.
- By default, programmatically created objects are hidden in the object list. If the user needs to interact with them, set `OBJPROP_HIDDEN` to `false` and `OBJPROP_SELECTABLE` to `true`.

## 6. Cleanup
Provide mechanisms to clean up painted objects when the MQL5 program is removed (`OnDeinit`). Use `ObjectsDeleteAll` with a specific prefix to avoid deleting user-drawn objects.


---
