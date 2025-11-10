#!/usr/bin/env python3
"""
Generate individual Dgraph JSON mutation files to prevent duplicates
Each judgment gets its own upsert mutation file
Uses hash-based tracking to prevent duplicate citation nodes
"""

import pandas as pd
import ast
import json
import os
import hashlib

# === Input / Output ===
input_path = "/home/anish/Desktop/Anish/Dgraph_curl/tests.xlsx"
output_dir = "upsert_mutations_no_citation_duplicates"
os.makedirs(output_dir, exist_ok=True)

# === Use blank nodes for Dgraph (avoids UID parsing errors) ===
# Blank nodes with _: prefix let Dgraph auto-generate UIDs

# === Global citation tracking to prevent duplicates ===
global_citations = {}  # {citation_title: citation_hash}

def get_citation_hash(title):
    """Generate a unique hash for a citation title"""
    return hashlib.md5(title.encode('utf-8')).hexdigest()[:12]

# === Load Excel ===
df = pd.read_excel(input_path)
print(f"📊 Processing {len(df)} rows...")
print("=" * 70)

mutation_files = []

for idx, row in df.iterrows():
    title = str(row["Title"]).strip()
    raw_citations = str(row["Citation"]).strip()
    doc_id = str(row["doc_id"]).strip() if pd.notna(row["doc_id"]) else f"doc_{idx+1}"
    year = int(row["Year"]) if pd.notna(row["Year"]) else None

    escaped_title = title.replace('"', '\\"')
    print(f"✓ Row {idx+1}: {escaped_title[:50]}...")

    # Parse citations
    citations = []
    if raw_citations.startswith("{") or raw_citations.startswith('"cited_cases"'):
        try:
            if raw_citations.startswith('"cited_cases"'):
                raw_citations = "{" + raw_citations + "}"
            citation_data = json.loads(raw_citations.replace("'", '"'))
            citations = citation_data.get("cited_cases", [])
        except Exception as e:
            print(f"⚠ JSON parse failed: {e}")
    elif raw_citations.startswith("["):
        try:
            citations = ast.literal_eval(raw_citations)
        except Exception as e:
            print(f"⚠ List parse failed: {e}")

    citations = [c.strip() for c in citations if c.strip()]

    # Create upsert mutation
    judgment_id = f"J_{idx+1}"
    
    # Create JSON mutation for this judgment
    query_parts = [f"main as var(func: eq(judgment_id, \"{judgment_id}\"))"]
    
    # Track citations with hash to prevent duplicates
    citation_vars = []
    for citation in citations:
        # Generate or retrieve citation hash
        if citation not in global_citations:
            citation_hash = get_citation_hash(citation)
            global_citations[citation] = citation_hash
        else:
            citation_hash = global_citations[citation]
        
        var_name = f"cite_{citation_hash}"
        citation_vars.append(var_name)
        escaped_citation = citation.replace('"', '\\"')
        query_parts.append(f"{var_name} as var(func: eq(title, \"{escaped_citation}\"))")
    
    mutation = {
        "query": "{\n  " + "\n  ".join(query_parts) + "\n}",
        "set": [
            {
                "uid": "uid(main)",
                "judgment_id": judgment_id,
                "title": title,
                "doc_id": doc_id,
                "dgraph.type": "Judgment"
            }
        ]
    }
    
    if year is not None:
        mutation["set"][0]["year"] = year
    
    # Add citations using hash-based variable names
    for var_name, citation in zip(citation_vars, citations):
        # Add citation node - using only title as unique identifier
        citation_node = {
            "uid": f"uid({var_name})",
            "title": citation,
            "dgraph.type": "Judgment"
        }
        mutation["set"].append(citation_node)
        
        # Add citation relationship
        if "cites" not in mutation["set"][0]:
            mutation["set"][0]["cites"] = []
        mutation["set"][0]["cites"].append({"uid": f"uid({var_name})"})

    # Write individual mutation file
    mutation_file = f"{output_dir}/mutation_{idx+1:04d}.json"
    with open(mutation_file, "w", encoding="utf-8") as f:
        json.dump(mutation, f, indent=2, ensure_ascii=False)
    
    mutation_files.append(mutation_file)

# === Create upload script ===
upload_script = f"{output_dir}/upload_all.sh"
with open(upload_script, "w") as f:
    f.write("#!/bin/bash\n")
    f.write("echo 'Uploading mutations to Dgraph...'\n")
    for mutation_file in mutation_files:
        f.write(f'echo "Uploading {os.path.basename(mutation_file)}..."\n')
        f.write(f'curl -X POST "localhost:8180/mutate?commitNow=true" \\\n')
        f.write(f'     -H "Content-Type: application/json" \\\n')
        f.write(f'     --data-binary @{mutation_file}\n')
        f.write('echo ""\n')
    f.write('echo "All mutations uploaded!"\n')

# Make script executable
os.chmod(upload_script, 0o755)

print("\n" + "=" * 70)
print("✅ JSON mutation files generated successfully (using upserts)!")
print(f"📁 Output directory: {output_dir}/")
print(f"📊 Total rows: {len(df)}")
print(f"🔗 Total mutation files: {len(mutation_files)}")
print(f"📚 Unique citations tracked: {len(global_citations)}")
print("🔄 Duplicate prevention: Citations with same title will reuse same node")
print("=" * 70)
print("🚀 Upload to Dgraph using:")
print(f"   chmod +x {upload_script}")
print(f"   ./{upload_script}")
print("=" * 70)
print("🔄 Or upload individual files:")
print("   curl -X POST \"localhost:8180/mutate?commitNow=true\" \\")
print("        -H \"Content-Type: application/json\" \\")
print(f"        --data-binary @{output_dir}/mutation_0001.json")
print("=" * 70)
