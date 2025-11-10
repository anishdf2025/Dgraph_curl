#!/usr/bin/env python3
"""
Get field names from Elasticsearch index 'graphdb'
"""

from elasticsearch import Elasticsearch
import json

# === Configuration ===
ES_HOST = "http://localhost:9200"
INDEX_NAME = "graphdb"

# === Connect to Elasticsearch ===
try:
    es = Elasticsearch([ES_HOST])
    
    if es.ping():
        print("✅ Connected to Elasticsearch successfully!")
    else:
        print("❌ Failed to connect to Elasticsearch")
        exit(1)
except Exception as e:
    print(f"❌ Error connecting to Elasticsearch: {e}")
    exit(1)

print("=" * 70)

# === Check if index exists ===
if not es.indices.exists(index=INDEX_NAME):
    print(f"⚠️  Index '{INDEX_NAME}' does not exist!")
    print("\nAvailable indices:")
    for index in es.indices.get_alias(index="*"):
        print(f"  - {index}")
    exit(1)

print(f"📊 Index: '{INDEX_NAME}'")
print("=" * 70)

# === Get field names from mapping ===
print("\n🔍 Field Names from Mapping:\n")

try:
    mapping = es.indices.get_mapping(index=INDEX_NAME)
    
    # Extract field names
    fields = []
    
    if INDEX_NAME in mapping:
        properties = mapping[INDEX_NAME].get('mappings', {}).get('properties', {})
        
        for field_name, field_info in properties.items():
            field_type = field_info.get('type', 'N/A')
            fields.append(f"{field_name} ({field_type})")
            print(f"  ✓ {field_name:30s} -> Type: {field_type}")
        
        if not fields:
            print("  ⚠️  No fields found in mapping")
    
except Exception as e:
    print(f"❌ Error getting mapping: {e}")

print("\n" + "=" * 70)

# === Get field names from a sample document ===
print("\n🔍 Field Names from Sample Document:\n")

try:
    response = es.search(
        index=INDEX_NAME,
        body={
            "query": {
                "match_all": {}
            },
            "size": 1
        }
    )
    
    if response['hits']['total']['value'] > 0:
        sample_doc = response['hits']['hits'][0]['_source']
        
        print("Field names in sample document:")
        for field_name in sample_doc.keys():
            field_value = sample_doc[field_name]
            value_type = type(field_value).__name__
            print(f"  ✓ {field_name:30s} -> Value Type: {value_type}")
        
        print("\n" + "=" * 70)
        print("\n📄 Sample Document:")
        print(json.dumps(sample_doc, indent=2))
    else:
        print("  ⚠️  No documents found in the index")
    
except Exception as e:
    print(f"❌ Error getting sample document: {e}")

print("\n" + "=" * 70)
print("✅ Done!")
