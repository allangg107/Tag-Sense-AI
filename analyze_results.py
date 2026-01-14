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
    with open('test_config.json', 'r') as f:
        config = json.load(f)
    
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
                results.append(json.loads(line))
    
    # Aggregate scores
    # Key: prompt_id
    # Value: list of scores
    combo_scores = defaultdict(list)
    
    # Track specific tag errors
    false_positives = Counter() # Generated but not expected
    false_negatives = Counter() # Expected but not generated

    for res in results:
        file_path = res.get('file_path', '')
        filename = os.path.basename(file_path)
        
        if filename not in benchmarks:
            continue
            
        expected_tags = benchmarks[filename]
        generated_tags = res.get('tags', [])
        
        # Analyze discrepancies
        exp_set = set(t.lower() for t in expected_tags)
        gen_set = set(t.lower() for t in generated_tags)
        
        fp = gen_set - exp_set
        fn = exp_set - gen_set
        
        false_positives.update(fp)
        false_negatives.update(fn)

        # Clean generated tags (sometimes they are strings looking like lists if parsing failed, 
        # but the provided snippet shows they are lists. 
        # However, one entry showed: "tags": ["json", "[\"work", "project", "email\"]", "**analysis:**"]
        # This indicates some models output raw text that wasn't parsed perfectly.
        # The 'tags' field in jsonl seems to be what the system *extracted*.
        # If the system failed to extract a clean list, the score will naturally be low, which is correct.
        # We will treat the list as is.
        
        # Handle the weird case where a tag might be a string representation of a list
        # e.g. "[\"work", "resume\"]"
        # The current extraction logic in the app might be imperfect. 
        # We will try to clean it up slightly for fairness, or just take it as is.
        # Given the user wants to know which *generated* the most relevant tags, 
        # if the model output garbage that couldn't be parsed, it's a bad result.
        # So we will use the tags as provided by the file.
        
        score = calculate_jaccard(expected_tags, generated_tags)
        
        # The prompt_id in results is like "phi4_allan_custom"
        # We can use this directly as the identifier for the combo.
        combo_id = res.get('prompt_id')
        model_name = res.get('model_name')
        
        # If prompt_id is missing, construct it
        if not combo_id and model_name:
             combo_id = f"{model_name}_unknown"
             
        if combo_id:
            combo_scores[combo_id].append(score)

    # Calculate average scores
    avg_scores = []
    for combo, scores in combo_scores.items():
        avg = sum(scores) / len(scores)
        avg_scores.append((combo, avg))
    
    # Sort
    avg_scores.sort(key=lambda x: x[1], reverse=True)
    
    print("Top 5 Model + Prompt Combinations:")
    for i, (combo, score) in enumerate(avg_scores[:5], 1):
        print(f"{i}. {combo} (Score: {score:.4f})")
    print("\nTop 5 Missing Tags (False Negatives - Expected but not found):")
    for tag, count in false_negatives.most_common(5):
        print(f" - '{tag}': missed {count} times")

    print("\nTop 5 Extra Tags (False Positives - Generated but not expected):")
    for tag, count in false_positives.most_common(5):
        print(f" - '{tag}': added {count} times")
if __name__ == "__main__":
    analyze()
