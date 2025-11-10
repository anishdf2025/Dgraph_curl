#!/usr/bin/env python3
"""
Complete Dgraph ETL Pipeline
1. Connects to Elasticsearch
2. Applies Dgraph schema
3. Generates mutation from Elasticsearch data
4. Uploads data to Dgraph
"""

from elasticsearch import Elasticsearch
import json
import hashlib
import requests

# === Configuration ===
ES_HOST = "http://localhost:9200"
ES_INDEX_NAME = "graphdb"
DGRAPH_HOST = "http://localhost:8180"
OUTPUT_FILE = "dgraph_mutations_all.json"

# === Global tracking to prevent duplicates ===
global_citations = {}
global_judges = {}
global_advocates = {}
global_outcomes = {}
global_case_durations = {}

def get_hash(text):
    """Generate a unique hash for any text"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]

# === Step 1: Apply Dgraph Schema ===
def apply_dgraph_schema():
    """Apply the schema to Dgraph"""
    print("=" * 70)
    print("📋 STEP 1: Applying Dgraph Schema")
    print("=" * 70)
    
    schema = '''
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

# Common field (used by Judge, Advocate, Outcome)
name: string @index(exact, term, fulltext) @upsert .
'''
    
    try:
        response = requests.post(f"{DGRAPH_HOST}/alter", data=schema)
        result = response.json()
        
        if response.status_code == 200 and result.get('data', {}).get('code') == 'Success':
            print("✅ Schema applied successfully!")
            print("   - Judgment, Judge, Advocate, Outcome, CaseDuration types created")
            print("   - All predicates with proper indexing and @upsert")
            return True
        else:
            print(f"⚠️  Schema response: {result}")
            return False
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        return False

# === Step 2: Connect to Elasticsearch ===
def connect_to_elasticsearch():
    """Connect to Elasticsearch and verify index exists"""
    print("\n" + "=" * 70)
    print("📡 STEP 2: Connecting to Elasticsearch")
    print("=" * 70)
    
    try:
        es = Elasticsearch([ES_HOST])
        
        if not es.ping():
            print("❌ Failed to connect to Elasticsearch")
            return None
        
        print(f"✅ Connected to Elasticsearch successfully!")
        
        if not es.indices.exists(index=ES_INDEX_NAME):
            print(f"❌ Index '{ES_INDEX_NAME}' does not exist!")
            return None
        
        print(f"✅ Index '{ES_INDEX_NAME}' found!")
        return es
    except Exception as e:
        print(f"❌ Error connecting to Elasticsearch: {e}")
        return None

# === Step 3: Fetch data from Elasticsearch ===
def fetch_elasticsearch_data(es):
    """Fetch all documents from Elasticsearch"""
    print("\n" + "=" * 70)
    print("📊 STEP 3: Fetching Data from Elasticsearch")
    print("=" * 70)
    
    try:
        # Get total count
        count_response = es.count(index=ES_INDEX_NAME)
        total_docs = count_response['count']
        print(f"Total documents found: {total_docs}")
        
        # Fetch all documents using scroll API
        response = es.search(
            index=ES_INDEX_NAME,
            body={
                "query": {
                    "match_all": {}
                },
                "size": 100
            },
            scroll='2m'
        )
        
        scroll_id = response['_scroll_id']
        documents = response['hits']['hits']
        
        # Continue scrolling if there are more documents
        while len(response['hits']['hits']) > 0:
            response = es.scroll(scroll_id=scroll_id, scroll='2m')
            documents.extend(response['hits']['hits'])
            if len(response['hits']['hits']) == 0:
                break
        
        # Clear scroll
        es.clear_scroll(scroll_id=scroll_id)
        
        print(f"✅ Fetched {len(documents)} documents from Elasticsearch")
        return documents
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        return []

# === Step 4: Build Dgraph mutation ===
def build_dgraph_mutation(documents):
    """Build single mutation with all data"""
    print("\n" + "=" * 70)
    print("🔨 STEP 4: Building Dgraph Mutation")
    print("=" * 70)
    
    all_query_parts = []
    all_set_nodes = []
    
    for idx, doc in enumerate(documents, 1):
        source = doc['_source']
        
        # Extract fields
        title = source.get('title', '').strip()
        doc_id = source.get('doc_id', f"doc_{idx}").strip()
        year = source.get('year', None)
        citations = source.get('citations', [])
        outcome = source.get('outcome', '').strip()
        case_duration = source.get('case_duration', '').strip()
        judges = source.get('judges', [])
        petitioner_advocates = source.get('petitioner_advocates', [])
        respondant_advocates = source.get('respondant_advocates', [])
        processed_timestamp = source.get('processed_timestamp', None)
        
        # Ensure lists
        if isinstance(citations, str):
            try:
                citations = json.loads(citations)
            except:
                citations = [citations] if citations else []
        elif not isinstance(citations, list):
            citations = []
        
        if not isinstance(judges, list):
            judges = [judges] if judges else []
        if not isinstance(petitioner_advocates, list):
            petitioner_advocates = [petitioner_advocates] if petitioner_advocates else []
        if not isinstance(respondant_advocates, list):
            respondant_advocates = [respondant_advocates] if respondant_advocates else []
        
        # Clean up
        citations = [c.strip() for c in citations if c and c.strip()]
        judges = [j.strip() for j in judges if j and j.strip()]
        petitioner_advocates = [a.strip() for a in petitioner_advocates if a and a.strip()]
        respondant_advocates = [a.strip() for a in respondant_advocates if a and a.strip()]
        
        escaped_title = title.replace('"', '\\"')
        print(f"  ✓ Processing document {idx}: {escaped_title[:50]}...")
        
        # Create judgment ID
        judgment_id = f"J_{idx}"
        all_query_parts.append(f"main_{idx} as var(func: eq(judgment_id, \"{judgment_id}\"))")
        
        # Track citations
        citation_vars = []
        for citation in citations:
            if citation not in global_citations:
                citation_hash = get_hash(citation)
                global_citations[citation] = citation_hash
                escaped_citation = citation.replace('"', '\\"')
                var_name = f"cite_{citation_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(title, \"{escaped_citation}\"))")
            citation_hash = global_citations[citation]
            citation_vars.append(f"cite_{citation_hash}")
        
        # Track judges
        judge_vars = []
        for judge in judges:
            if judge not in global_judges:
                judge_hash = get_hash(judge)
                global_judges[judge] = judge_hash
                escaped_judge = judge.replace('"', '\\"')
                var_name = f"judge_{judge_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_judge}\")) @filter(type(Judge))")
            judge_hash = global_judges[judge]
            judge_vars.append(f"judge_{judge_hash}")
        
        # Track petitioner advocates
        petitioner_advocate_vars = []
        for advocate in petitioner_advocates:
            if advocate not in global_advocates:
                advocate_hash = get_hash(advocate)
                global_advocates[advocate] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) @filter(type(Advocate) AND eq(advocate_type, \"petitioner\"))")
            advocate_hash = global_advocates[advocate]
            petitioner_advocate_vars.append(f"adv_{advocate_hash}")
        
        # Track respondant advocates
        respondant_advocate_vars = []
        for advocate in respondant_advocates:
            advocate_key = f"{advocate}_respondant"
            if advocate_key not in global_advocates:
                advocate_hash = get_hash(advocate_key)
                global_advocates[advocate_key] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) @filter(type(Advocate) AND eq(advocate_type, \"respondant\"))")
            advocate_hash = global_advocates[advocate_key]
            respondant_advocate_vars.append(f"adv_{advocate_hash}")
        
        # Track outcome
        outcome_var = None
        if outcome:
            if outcome not in global_outcomes:
                outcome_hash = get_hash(outcome)
                global_outcomes[outcome] = outcome_hash
                escaped_outcome = outcome.replace('"', '\\"')
                outcome_var = f"outcome_{outcome_hash}"
                all_query_parts.append(f"{outcome_var} as var(func: eq(name, \"{escaped_outcome}\")) @filter(type(Outcome))")
            else:
                outcome_hash = global_outcomes[outcome]
                outcome_var = f"outcome_{outcome_hash}"
        
        # Track case duration
        duration_var = None
        if case_duration:
            if case_duration not in global_case_durations:
                duration_hash = get_hash(case_duration)
                global_case_durations[case_duration] = duration_hash
                escaped_duration = case_duration.replace('"', '\\"')
                duration_var = f"duration_{duration_hash}"
                all_query_parts.append(f"{duration_var} as var(func: eq(duration, \"{escaped_duration}\")) @filter(type(CaseDuration))")
            else:
                duration_hash = global_case_durations[case_duration]
                duration_var = f"duration_{duration_hash}"
        
        # Build judgment node
        judgment_node = {
            "uid": f"uid(main_{idx})",
            "judgment_id": judgment_id,
            "title": title,
            "doc_id": doc_id,
            "dgraph.type": "Judgment"
        }
        
        if year is not None:
            judgment_node["year"] = year
        
        if processed_timestamp:
            judgment_node["processed_timestamp"] = processed_timestamp
        
        # Add relationships
        if citation_vars:
            judgment_node["cites"] = [{"uid": f"uid({var})"} for var in citation_vars]
        if judge_vars:
            judgment_node["judged_by"] = [{"uid": f"uid({var})"} for var in judge_vars]
        if petitioner_advocate_vars:
            judgment_node["petitioner_represented_by"] = [{"uid": f"uid({var})"} for var in petitioner_advocate_vars]
        if respondant_advocate_vars:
            judgment_node["respondant_represented_by"] = [{"uid": f"uid({var})"} for var in respondant_advocate_vars]
        if outcome_var:
            judgment_node["has_outcome"] = {"uid": f"uid({outcome_var})"}
        if duration_var:
            judgment_node["has_case_duration"] = {"uid": f"uid({duration_var})"}
        
        all_set_nodes.append(judgment_node)
    
    # Add all citation nodes
    for citation, citation_hash in global_citations.items():
        all_set_nodes.append({
            "uid": f"uid(cite_{citation_hash})",
            "title": citation,
            "dgraph.type": "Judgment"
        })
    
    # Add all judge nodes
    for judge, judge_hash in global_judges.items():
        all_set_nodes.append({
            "uid": f"uid(judge_{judge_hash})",
            "judge_id": f"judge_{judge_hash}",
            "name": judge,
            "dgraph.type": "Judge"
        })
    
    # Add all advocate nodes
    for advocate_key, advocate_hash in global_advocates.items():
        advocate_name = advocate_key.replace("_respondant", "")
        advocate_type = "respondant" if "_respondant" in advocate_key else "petitioner"
        all_set_nodes.append({
            "uid": f"uid(adv_{advocate_hash})",
            "advocate_id": f"adv_{advocate_hash}",
            "name": advocate_name,
            "advocate_type": advocate_type,
            "dgraph.type": "Advocate"
        })
    
    # Add all outcome nodes
    for outcome, outcome_hash in global_outcomes.items():
        all_set_nodes.append({
            "uid": f"uid(outcome_{outcome_hash})",
            "outcome_id": f"outcome_{outcome_hash}",
            "name": outcome,
            "dgraph.type": "Outcome"
        })
    
    # Add all case duration nodes
    for duration, duration_hash in global_case_durations.items():
        all_set_nodes.append({
            "uid": f"uid(duration_{duration_hash})",
            "case_duration_id": f"duration_{duration_hash}",
            "duration": duration,
            "dgraph.type": "CaseDuration"
        })
    
    # Create final mutation
    final_mutation = {
        "query": "{\n  " + "\n  ".join(all_query_parts) + "\n}",
        "set": all_set_nodes
    }
    
    print(f"\n✅ Mutation built successfully!")
    print(f"   📚 Citations: {len(global_citations)}")
    print(f"   👨‍⚖️  Judges: {len(global_judges)}")
    print(f"   👔 Advocates: {len(global_advocates)}")
    print(f"   🎯 Outcomes: {len(global_outcomes)}")
    print(f"   ⏱️  Case Durations: {len(global_case_durations)}")
    print(f"   🔢 Total nodes: {len(all_set_nodes)}")
    
    return final_mutation

# === Step 5: Save and Upload to Dgraph ===
def upload_to_dgraph(mutation):
    """Save mutation to file and upload to Dgraph"""
    print("\n" + "=" * 70)
    print("🚀 STEP 5: Uploading Data to Dgraph")
    print("=" * 70)
    
    # Save to file
    print(f"📝 Saving mutation to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mutation, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved to {OUTPUT_FILE}")
    
    # Upload to Dgraph
    print(f"\n📤 Uploading to Dgraph at {DGRAPH_HOST}/mutate")
    try:
        response = requests.post(
            f"{DGRAPH_HOST}/mutate?commitNow=true",
            headers={"Content-Type": "application/json"},
            json=mutation
        )
        
        result = response.json()
        
        if response.status_code == 200 and result.get('data', {}).get('code') == 'Success':
            print("✅ Data uploaded successfully!")
            uids = result.get('data', {}).get('uids', {})
            print(f"   🆔 Total UIDs created/updated: {len(uids)}")
            return True
        else:
            print(f"⚠️  Upload response: {result}")
            return False
    except Exception as e:
        print(f"❌ Error uploading to Dgraph: {e}")
        return False

# === Main Pipeline ===
def main():
    """Run the complete ETL pipeline"""
    print("\n" + "=" * 70)
    print("🚀 DGRAPH ETL PIPELINE - Elasticsearch to Dgraph")
    print("=" * 70)
    
    # Step 1: Apply Schema
    if not apply_dgraph_schema():
        print("\n❌ Pipeline failed at schema application")
        return
    
    # Step 2: Connect to Elasticsearch
    es = connect_to_elasticsearch()
    if not es:
        print("\n❌ Pipeline failed at Elasticsearch connection")
        return
    
    # Step 3: Fetch Data
    documents = fetch_elasticsearch_data(es)
    if not documents:
        print("\n❌ Pipeline failed at data fetching")
        return
    
    # Step 4: Build Mutation
    mutation = build_dgraph_mutation(documents)
    if not mutation:
        print("\n❌ Pipeline failed at mutation building")
        return
    
    # Step 5: Upload to Dgraph
    if not upload_to_dgraph(mutation):
        print("\n❌ Pipeline failed at data upload")
        return
    
    # Success!
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"📊 Processed {len(documents)} judgments")
    print(f"📁 Mutation saved to: {OUTPUT_FILE}")
    print(f"🎯 Data uploaded to Dgraph at: {DGRAPH_HOST}")
    print("=" * 70)

if __name__ == "__main__":
    main()
