# Understanding "2 Court Nodes" Message

## Question
When running `python update_specific_field.py --field court_bench`, you saw:
```
Updated bench_type for 2 Court nodes
Marked 1 judgments as processed for court_bench
```

**Why does it say 2 Court nodes when you only have 1 document?**

## Answer

It's **NOT 2 separate Court nodes**. The mutation has **2 operations** in the `set` array:

### Operation 1: Update the Court Node
```json
{
  "uid": "uid(court_c856d8650786)",
  "court_id": "court_c856d8650786",
  "name": "Supreme Court of India",
  "dgraph.type": "Court",
  "bench_type": "Division Bench",  ← Adding this field
  "location": "New Delhi"
}
```
This updates the existing Court node with the new `bench_type` field.

### Operation 2: Connect Judgment to Court
```json
{
  "uid": "uid(main_1)",
  "court_heard_in": {
    "uid": "uid(court_c856d8650786)"
  }
}
```
This creates the relationship: **Judgment → court_heard_in → Court**

## Visual Representation

```
Before:
┌─────────────────┐
│    Judgment     │
│  (Asha Devi)    │
└─────────────────┘

┌─────────────────┐
│      Court      │
│ Supreme Court   │
│ Location: Delhi │
└─────────────────┘

After Operation 1 - Add bench_type:
┌─────────────────┐
│      Court      │
│ Supreme Court   │
│ Location: Delhi │
│ Bench: Division │ ← NEW FIELD
└─────────────────┘

After Operation 2 - Connect them:
┌─────────────────┐
│    Judgment     │
│  (Asha Devi)    │
└────────┬────────┘
         │ court_heard_in
         ↓
┌─────────────────┐
│      Court      │
│ Supreme Court   │
│ Location: Delhi │
│ Bench: Division │
└─────────────────┘
```

## What Actually Happened

✅ **1 Court node** was updated with `bench_type`
✅ **1 Judgment node** was connected to that Court
✅ **Total: 2 operations** in the mutation

## Fixed Logging

The script now shows clearer messages:
```
✅ SUCCESS!
Updated bench_type for 1 Court node(s)
Connected 1 Judgment(s) to their Courts
Marked 1 document(s) as processed for court_bench
```

## Example with Multiple Documents

If you had 3 documents all referencing "Supreme Court of India":

**Operation:**
```
Updated bench_type for 1 Court node(s)         ← Same court, updated once
Connected 3 Judgment(s) to their Courts        ← 3 judgments connected
Total: 4 set operations (1 court + 3 judgments)
```

## Summary

The old message was confusing because it counted all operations in the `set` array:
- **Old:** `len(mutation['set'])` = 2 (counted everything)
- **New:** Separate counts:
  - Courts updated: 1
  - Judgments connected: 1

So you actually updated **1 Court** and connected **1 Judgment** to it! ✅
