---
name: paint-objects
description: Use when drawing or updating chart objects in MQL5 for this workspace. Follow the local rules for choosing the right object type, anchoring it to the correct candle, updating existing objects safely, and forcing chart redraw when needed.
---

# Paint Objects

Use this skill when creating or editing MQL5 code that paints chart objects with `ObjectCreate`, `ObjectMove`, or `ObjectSetInteger`.

## Object Choice

Choose the object type that matches the visual requirement.

- Use `OBJ_RECTANGLE` for zones, gaps, ranges, and areas with top and bottom.
- Do not simulate a zone with two trend lines when the intent is a filled area.
- Use lines only when the user explicitly wants a line-based drawing.

## Anchoring

Anchor the object to the correct candle and prices.

- If the drawing is based on a multi-candle pattern, confirm which candle defines the start time.
- For the FVG case in this workspace, the rectangle must start at candle 1, the oldest candle in the 3-candle pattern.
- For zones, use the upper price as the top and the lower price as the bottom.

Example pattern for FVG:

```mq5
datetime start_time = StructToTime(time);
datetime end_time = start_time + (duration_minutes * 60);

ObjectCreate(chart_id, rect_name, OBJ_RECTANGLE, 0, start_time, high, end_time, low);
```

## Repainting And Updates

Do not assume `ObjectCreate` will succeed repeatedly with the same name.

- If the object does not exist, create it.
- If the object already exists, update it with `ObjectMove`.
- Keep object names stable and deterministic.

Pattern:

```mq5
if(ObjectFind(chart_id, object_name) < 0)
{
   ObjectCreate(chart_id, object_name, OBJ_RECTANGLE, 0, start_time, high, end_time, low);
}
else
{
   ObjectMove(chart_id, object_name, 0, start_time, high);
   ObjectMove(chart_id, object_name, 1, end_time, low);
}
```

## Visibility

After painting or updating objects, force a chart refresh when needed.

- Call `ChartRedraw(chart_id)` after a batch of object updates.
- Do not assume the chart will visibly refresh immediately on its own.

## Validation

When painted objects do not appear, check these points before changing strategy logic:

1. The object name is not colliding with an existing object unexpectedly.
2. Existing objects are updated with `ObjectMove` instead of recreated blindly.
3. `ChartRedraw(...)` is called after painting.
