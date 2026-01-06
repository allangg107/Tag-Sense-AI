import json
import os
from collections import defaultdict

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
    
    # Load results
    results = []
    with open('test_results.jsonl', 'r') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    
    # Aggregate scores
    # Key: prompt_id
    # Value: list of scores
    combo_scores = defaultdict(list)
    
    for res in results:
        file_path = res.get('file_path', '')
        filename = os.path.basename(file_path)
        
        if filename not in benchmarks:
            continue
            
        expected_tags = benchmarks[filename]
        generated_tags = res.get('tags', [])
        
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

if __name__ == "__main__":
    analyze()
