import json
import os
import sys
from collections import defaultdict, Counter

def calculate_jaccard(list1, list2):
    set1 = set(t.lower() for t in list1)
    set2 = set(t.lower() for t in list2)
    
    if not set1 and not set2:
        return 1.0
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def analyze():
    # Load config
    try:
        with open('test_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: test_config.json not found. Please run this script from the project root.")
        return
    
    benchmarks = config.get('benchmarks', {})
    
    # Determine results file
    results_file = 'test_results.jsonl'
    if len(sys.argv) > 1:
        results_file = sys.argv[1]

    if not os.path.exists(results_file):
        print(f"Error: Results file '{results_file}' not found.")
        return

    print(f"Analyzing: {results_file}")

    # Load results
    results = []
    with open(results_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # --- Categorized Aggregation ---
    # Key: normalized category (e.g., 'text_domain')
    # Value: defaultdict(list) where key is prompt_id and value is list of scores
    category_scores = defaultdict(lambda: defaultdict(list))
    
    # Key: normalized category
    # Value: Counter()
    category_false_positives = defaultdict(Counter)
    category_false_negatives = defaultdict(Counter)

    config_tags = config.get('tags', {})
    # Sort categories by length, longest first, to ensure "text_domain" is matched before "text"
    sorted_categories = sorted(config_tags.keys(), key=len, reverse=True)

    for res in results:
        file_path = res.get('file_path', '')
        filename = os.path.basename(file_path)
        
        if filename not in benchmarks:
            continue
            
        prompt_id = res.get('prompt_id')
        if not prompt_id:
            continue

        # --- Identify Category from prompt_id ---
        # e.g., "gemma3_12b_text_domain_domain_focus" -> "text_domain"
        category = None
        for cat in sorted_categories:
            if cat in prompt_id:
                category = cat
                break
        
        if not category:
            # print(f"Warning: Could not determine category for prompt_id: {prompt_id}")
            continue
        
        # Normalize category key to handle potential casing duplicates and grouping
        normalized_category = category.lower().strip()
        
        # --- Filter Expected Tags by Category ---
        all_expected_tags = benchmarks[filename]
        # Use existing category key (from config) to fetch tags set
        category_tag_set = set(config_tags.get(category, []))
        
        # We only care about the benchmark tags that belong to the current category
        filtered_expected_tags = [tag for tag in all_expected_tags if tag in category_tag_set]

        generated_tags = res.get('tags', [])
        
        # --- Analyze Discrepancies for the Category ---
        exp_set = set(t.lower() for t in filtered_expected_tags)
        gen_set = set(t.lower() for t in generated_tags)
        
        fp = gen_set - exp_set
        fn = exp_set - gen_set
        
        category_false_positives[normalized_category].update(fp)
        category_false_negatives[normalized_category].update(fn)
        
        # --- Calculate Score ---
        score = calculate_jaccard(filtered_expected_tags, generated_tags)
        category_scores[normalized_category][prompt_id].append(score)

    # --- Display Categorized Results ---
    # Sort keys for consistent output order
    for category in sorted(category_scores.keys()):
        combo_scores = category_scores[category]
        
        print("\n" + "="*60)
        print(f"ANALYSIS FOR CATEGORY: {category.upper()}")
        print("="*60)

        # Calculate average scores
        avg_scores = []
        for combo, scores in combo_scores.items():
            avg = sum(scores) / len(scores)
            avg_scores.append((combo, avg))
        
        # Sort
        avg_scores.sort(key=lambda x: x[1], reverse=True)
        
        print("Top Model + Prompt Combinations:")
        for i, (combo, score) in enumerate(avg_scores, 1):
            print(f"{i}. {combo} (Score: {score:.4f})")
        
        print("\nTop 5 Missing Tags (False Negatives):")
        for tag, count in category_false_negatives[category].most_common(5):
            print(f" - '{tag}': missed {count} times")

        print("\nTop 5 Extra Tags (False Positives):")
        for tag, count in category_false_positives[category].most_common(5):
            print(f" - '{tag}': added {count} times")
    print("\n")

if __name__ == "__main__":
    analyze()
