#!/usr/bin/env python3
"""
Dgraph Schema Definition
This file contains the complete schema for the graph database
"""

DGRAPH_SCHEMA = '''
type Judgment {
  judgment_id
  title
  doc_id
  year
  processed_timestamp
  cites
  judged_by
  petitioner_represented_by
  respondant_represented_by
  has_outcome
  has_case_duration
  court_heard_in
  has_decision_date
  has_filing_date
  has_petitioner_party
  has_respondant_party
  has_case_number
  has_summary
  has_case_type
  has_neutral_citation
  cites_act
}

type Judge {
  judge_id
  name
}

type Advocate {
  advocate_id
  name
  advocate_type
}

type Outcome {
  outcome_id
  name
}

type CaseDuration {
  case_duration_id
  duration
}

type Court {
  court_id
  name
  location
  bench_type
}

type DecisionDate {
  decision_date_id
  date
}

type FilingDate {
  filing_date_id
  date
}

type PetitionerParty {
  petitioner_party_id
  name
}

type RespondantParty {
  respondant_party_id
  name
}

type CaseNumber {
  case_number_id
  number
}

type Summary {
  summary_id
  text
}

type CaseType {
  case_type_id
  type_name
}

type NeutralCitation {
  neutral_citation_id
  citation_text
}

type Act {
  act_id
  act_name
}

# Judgment fields
judgment_id: string @index(exact) @upsert .
title: string @index(exact, term, fulltext) @upsert .
doc_id: string @index(exact) @upsert .
year: int @index(int) .
processed_timestamp: datetime @index(hour) .
cites: [uid] @reverse .
judged_by: [uid] @reverse .
petitioner_represented_by: [uid] @reverse .
respondant_represented_by: [uid] @reverse .
has_outcome: uid @reverse .
has_case_duration: uid @reverse .
court_heard_in: uid @reverse .
has_decision_date: uid @reverse .
has_filing_date: uid @reverse .
has_petitioner_party: uid @reverse .
has_respondant_party: uid @reverse .
has_case_number: uid @reverse .
has_summary: uid @reverse .
has_case_type: uid @reverse .
has_neutral_citation: uid @reverse .
cites_act: [uid] @reverse .

# Judge fields
judge_id: string @index(exact) @upsert .

# Advocate fields
advocate_id: string @index(exact) @upsert .
advocate_type: string @index(exact) .

# Outcome fields
outcome_id: string @index(exact) @upsert .

# CaseDuration fields
case_duration_id: string @index(exact) @upsert .
duration: string @index(exact, term) .

# Court fields
court_id: string @index(exact) @upsert .
location: string @index(term) .
bench_type: string @index(exact, term) @upsert .

# DecisionDate fields
decision_date_id: string @index(exact) @upsert .
date: datetime @index(day) .

# FilingDate fields
filing_date_id: string @index(exact) @upsert .

# PetitionerParty fields
petitioner_party_id: string @index(exact) @upsert .

# RespondantParty fields
respondant_party_id: string @index(exact) @upsert .

# CaseNumber fields
case_number_id: string @index(exact) @upsert .
number: string @index(exact, term) @upsert .

# Summary fields
summary_id: string @index(exact) @upsert .
text: string @index(fulltext) .

# CaseType fields
case_type_id: string @index(exact) @upsert .
type_name: string @index(exact, term) @upsert .

# NeutralCitation fields
neutral_citation_id: string @index(exact) @upsert .
citation_text: string @index(exact, term) @upsert .

# Act fields
act_id: string @index(exact) @upsert .
act_name: string @index(exact, term, fulltext) @upsert .

# Common field (used by Judge, Advocate, Outcome, Court, PetitionerParty, RespondantParty)
name: string @index(exact, term, fulltext) @upsert .
'''
