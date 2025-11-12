# 📊 Dgraph Schema Structure - Complete Overview

**Last Updated**: 12 November 2025

---

## 🏛️ Central Node: Judgment (Title)

All entities connect to the **Judgment** node as the central hub.

```
                                    ┌─────────────────────┐
                       | Judgment | `has_case_type` | CaseType | One-to-One |
| Judgment | `has_neutral_citation` | NeutralCitation | One-to-One |
| Judgment | `cites_act` | Act | One-to-Many ✨ |

**Total Entity Types**: 16 (7 original + 9 new)
**Total Relationships**: 16 edges        │     JUDGMENT        │
                                    │      (Title)        │
                                    └──────────┬──────────┘
                                               │
                ┌──────────────────────────────┼──────────────────────────────┐
                │                              │                              │
                │                              │                              │
    ┌───────────▼──────────┐       ┌──────────▼──────────┐      ┌───────────▼──────────┐
    │   Citation           │       │      Judge          │      │     Advocate         │
    │   [cites]            │       │   [judged_by]       │      │ [petitioner/         │
    │  (One-to-Many)       │       │  (One-to-Many)      │      │  respondant]         │
    └──────────────────────┘       └─────────────────────┘      │  (One-to-Many)       │
                                                                 └──────────────────────┘
                │                              │                              │
    ┌───────────▼──────────┐       ┌──────────▼──────────┐      ┌───────────▼──────────┐
    │      Outcome         │       │   CaseDuration      │      │       Court          │
    │   [has_outcome]      │       │ [has_case_duration] │      │  [court_heard_in]    │
    │   (One-to-One)       │       │   (One-to-One)      │      │   (One-to-One)       │
    └──────────────────────┘       └─────────────────────┘      └──────────────────────┘

                │                              │                              │
    ┌───────────▼──────────┐       ┌──────────▼──────────┐      ┌───────────▼──────────┐
    │   DecisionDate       │       │    FilingDate       │      │  PetitionerParty     │
    │[has_decision_date]   │       │ [has_filing_date]   │      │[has_petitioner_party]│
    │   (One-to-One)       │       │   (One-to-One)      │      │   (One-to-One)       │
    └──────────────────────┘       └─────────────────────┘      └──────────────────────┘

                │                              │                              │
    ┌───────────▼──────────┐       ┌──────────▼──────────┐      ┌───────────▼──────────┐
    │  RespondantParty     │       │    CaseNumber       │      │      Summary         │
    │[has_respondant_party]│       │ [has_case_number]   │      │   [has_summary]      │
    │   (One-to-One)       │       │   (One-to-One)      │      │   (One-to-One)       │
    └──────────────────────┘       └─────────────────────┘      └──────────────────────┘

                │                              │
    ┌───────────▼──────────┐       ┌──────────▼──────────┐
    │     CaseType         │       │  NeutralCitation    │
    │  [has_case_type]     │       │[has_neutral_citation]│
    │   (One-to-One)       │       │   (One-to-One)       │
    └──────────────────────┘       └─────────────────────┘
                                               │
                                   ┌───────────▼──────────┐
                                   │       Act ✨         │
                                   │    [cites_act]       │
                                   │  (One-to-Many) ✨    │
                                   └──────────────────────┘
```

---

## 📋 Entity Types

### 1. **Judgment** (Main Node)
**Fields**:
- `judgment_id` - Unique identifier
- `title` - Case title (indexed: exact, term, fulltext)
- `doc_id` - Document ID (indexed: exact)
- `year` - Year of judgment (indexed: int)
- `processed_timestamp` - Processing timestamp (indexed: hour)

**Relationships**:
- `cites` → Citation (One-to-Many)
- `judged_by` → Judge (One-to-Many)
- `petitioner_represented_by` → Advocate (One-to-Many)
- `respondant_represented_by` → Advocate (One-to-Many)
- `has_outcome` → Outcome (One-to-One)
- `has_case_duration` → CaseDuration (One-to-One)
- `court_heard_in` → Court (One-to-One)
- `has_decision_date` → DecisionDate (One-to-One) ✨ **NEW**
- `has_filing_date` → FilingDate (One-to-One) ✨ **NEW**
- `has_petitioner_party` → PetitionerParty (One-to-One) ✨ **NEW**
- `has_respondant_party` → RespondantParty (One-to-One) ✨ **NEW**
- `has_case_number` → CaseNumber (One-to-One) ✨ **NEW**
- `has_summary` → Summary (One-to-One) ✨ **NEW**
- `has_case_type` → CaseType (One-to-One) ✨ **NEW**
- `has_neutral_citation` → NeutralCitation (One-to-One) ✨ **NEW**
- `cites_act` → Act (One-to-Many) ✨ **NEW**

---

### 2. **Judge**
**Fields**:
- `judge_id` - Unique identifier (indexed: exact, upsert)
- `name` - Judge name (indexed: exact, term, fulltext, upsert)

**Relationship**: Connected FROM Judgment via `judged_by`

---

### 3. **Advocate**
**Fields**:
- `advocate_id` - Unique identifier (indexed: exact, upsert)
- `name` - Advocate name (indexed: exact, term, fulltext, upsert)
- `advocate_type` - Type: "petitioner" or "respondant" (indexed: exact)

**Relationship**: Connected FROM Judgment via `petitioner_represented_by` or `respondant_represented_by`

---

### 4. **Citation**
**Fields**:
- (Same as Judgment - self-referential)

**Relationship**: Connected FROM Judgment via `cites`

---

### 5. **Outcome**
**Fields**:
- `outcome_id` - Unique identifier (indexed: exact, upsert)
- `name` - Outcome name (indexed: exact, term, fulltext, upsert)

**Relationship**: Connected FROM Judgment via `has_outcome`

---

### 6. **CaseDuration**
**Fields**:
- `case_duration_id` - Unique identifier (indexed: exact, upsert)
- `duration` - Duration text (indexed: exact, term)

**Relationship**: Connected FROM Judgment via `has_case_duration`

---

### 7. **Court**
**Fields**:
- `court_id` - Unique identifier (indexed: exact, upsert)
- `name` - Court name (indexed: exact, term, fulltext, upsert)
- `location` - Court location (indexed: term)

**Relationship**: Connected FROM Judgment via `court_heard_in`

---

### 8. ✨ **DecisionDate** (NEW)
**Fields**:
- `decision_date_id` - Unique identifier (indexed: exact, upsert)
- `date` - Decision date (indexed: day, type: datetime)

**Relationship**: Connected FROM Judgment via `has_decision_date`

**Purpose**: Store when the judgment/decision was made

---

### 9. ✨ **FilingDate** (NEW)
**Fields**:
- `filing_date_id` - Unique identifier (indexed: exact, upsert)
- `date` - Filing date (indexed: day, type: datetime)

**Relationship**: Connected FROM Judgment via `has_filing_date`

**Purpose**: Store when the case was originally filed

---

### 10. ✨ **PetitionerParty** (NEW)
**Fields**:
- `petitioner_party_id` - Unique identifier (indexed: exact, upsert)
- `name` - Party name (indexed: exact, term, fulltext, upsert)

**Relationship**: Connected FROM Judgment via `has_petitioner_party`

**Purpose**: Store the petitioner party/plaintiff name

---

### 11. ✨ **RespondantParty** (NEW)
**Fields**:
- `respondant_party_id` - Unique identifier (indexed: exact, upsert)
- `name` - Party name (indexed: exact, term, fulltext, upsert)

**Relationship**: Connected FROM Judgment via `has_respondant_party`

**Purpose**: Store the respondant party/defendant name

---

### 12. ✨ **CaseNumber** (NEW)
**Fields**:
- `case_number_id` - Unique identifier (indexed: exact, upsert)
- `number` - Case number (indexed: exact, term, upsert)

**Relationship**: Connected FROM Judgment via `has_case_number`

**Purpose**: Store the official case number/docket number

---

### 13. ✨ **Summary** (NEW)
**Fields**:
- `summary_id` - Unique identifier (indexed: exact, upsert)
- `text` - Summary text (indexed: fulltext)

**Relationship**: Connected FROM Judgment via `has_summary`

**Purpose**: Store case summary/headnote text

---

### 14. ✨ **CaseType** (NEW)
**Fields**:
- `case_type_id` - Unique identifier (indexed: exact, upsert)
- `type_name` - Type name (indexed: exact, term, upsert)

**Relationship**: Connected FROM Judgment via `has_case_type`

**Purpose**: Store case type (e.g., "Civil", "Criminal", "Constitutional", "Writ Petition")

---

### 15. ✨ **NeutralCitation** (NEW)
**Fields**:
- `neutral_citation_id` - Unique identifier (indexed: exact, upsert)
- `citation_text` - Citation text (indexed: exact, term, upsert)

**Relationship**: Connected FROM Judgment via `has_neutral_citation`

**Purpose**: Store neutral citation format (e.g., "[2024] UKSC 12")

---

### 16. ✨ **Act** (NEW)
**Fields**:
- `act_id` - Unique identifier (indexed: exact, upsert)
- `act_name` - Full name of the Act (indexed: exact, term, fulltext, upsert)

**Relationship**: Connected FROM Judgment via `cites_act`

**Purpose**: Store Acts/Statutes cited in the judgment

**Examples**:
- "Indian Penal Code, 1860"
- "Constitution of India, 1950"
- "Companies Act, 2013"
- "Code of Criminal Procedure, 1973"

---

## 🔍 Index Types Explained

| Index Type | Purpose | Example Field |
|------------|---------|---------------|
| `@index(exact)` | Exact match queries | `judgment_id`, `doc_id` |
| `@index(term)` | Word-level search | `name`, `location` |
| `@index(fulltext)` | Full-text search | `title`, `summary.text` |
| `@index(int)` | Integer range queries | `year` |
| `@index(day)` | Date queries | `date` fields |
| `@upsert` | Prevent duplicates | All `_id` fields |

---

## 📊 Complete Relationship Matrix

| From | Edge | To | Cardinality |
|------|------|-----|-------------|
| Judgment | `cites` | Judgment | One-to-Many |
| Judgment | `judged_by` | Judge | One-to-Many |
| Judgment | `petitioner_represented_by` | Advocate | One-to-Many |
| Judgment | `respondant_represented_by` | Advocate | One-to-Many |
| Judgment | `has_outcome` | Outcome | One-to-One |
| Judgment | `has_case_duration` | CaseDuration | One-to-One |
| Judgment | `court_heard_in` | Court | One-to-One |
| Judgment | `has_decision_date` | DecisionDate | One-to-One ✨ |
| Judgment | `has_filing_date` | FilingDate | One-to-One ✨ |
| Judgment | `has_petitioner_party` | PetitionerParty | One-to-One ✨ |
| Judgment | `has_respondant_party` | RespondantParty | One-to-One ✨ |
| Judgment | `has_case_number` | CaseNumber | One-to-One ✨ |
| Judgment | `has_summary` | Summary | One-to-One ✨ |
| Judgment | `has_case_type` | CaseType | One-to-One ✨ |
| Judgment | `has_neutral_citation` | NeutralCitation | One-to-One ✨ |

**Total Entity Types**: 15 (7 original + 8 new)
**Total Relationships**: 15 edges

---

## 🎯 Query Examples

### Query 1: Get judgment with all details
```graphql
{
  judgment(func: eq(title, "Case Name")) {
    title
    year
    doc_id
    has_decision_date {
      date
    }
    has_filing_date {
      date
    }
    has_case_number {
      number
    }
    has_case_type {
      type_name
    }
    has_neutral_citation {
      citation_text
    }
    has_petitioner_party {
      name
    }
    has_respondant_party {
      name
    }
    has_summary {
      text
    }
    judged_by {
      name
    }
    court_heard_in {
      name
      location
    }
    has_outcome {
      name
    }
  }
}
```

### Query 2: Search by case number
```graphql
{
  cases(func: eq(number, "12345/2024")) @filter(type(CaseNumber)) {
    number
    ~has_case_number {
      title
      has_decision_date {
        date
      }
    }
  }
}
```

### Query 3: Find cases by type
```graphql
{
  civil_cases(func: eq(type_name, "Civil")) @filter(type(CaseType)) {
    type_name
    ~has_case_type {
      title
      year
      has_outcome {
        name
      }
    }
  }
}
```

---

## 🚀 Future Ready

The schema is now **future-proof** with:
- ✅ All current entities (7 types)
- ✅ All new entities (8 types)
- ✅ Proper indexing for efficient queries
- ✅ @upsert to prevent duplicates
- ✅ @reverse for bidirectional queries
- ✅ Fulltext search on summary
- ✅ Date indexing for temporal queries

**Ready for implementation when data is available!**
