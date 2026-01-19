"""Evaluation tests for the preference signals extraction agent using Azure AI Evaluation SDK."""

import json
import tempfile
import pytest
from dotenv import load_dotenv

# Load environment variables before importing agent
load_dotenv("app.env")

from azure.ai.evaluation import evaluate
from agent_framework import ChatMessage

from src.agents.signals_extraction_agent import agent
from src.agents.models.models import Preferences, Preference


# Custom evaluator class - SDK will auto-aggregate numeric return values
class PreferenceF1Evaluator:
    """Evaluator that calculates precision, recall, and F1 for preference extraction."""
    
    def __call__(self, *, response: str, ground_truth: str, **kwargs) -> dict:
        """Compare extracted preferences against ground truth."""
        try:
            actual = json.loads(response) if response else []
            expected = json.loads(ground_truth) if ground_truth else []
            
            actual_set = {(p["type"], p["value"].lower()) for p in actual}
            expected_set = {(p["type"], p["value"].lower()) for p in expected}
            
            if len(actual_set) == 0 and len(expected_set) == 0:
                return {"f1": 1.0, "precision": 1.0, "recall": 1.0, "exact_match": 1}
            
            if len(actual_set) == 0:
                return {"f1": 0.0, "precision": 0.0, "recall": 0.0, "exact_match": 0}
            
            if len(expected_set) == 0:
                return {"f1": 0.0, "precision": 0.0, "recall": 1.0, "exact_match": 0}
            
            true_positives = len(actual_set & expected_set)
            precision = true_positives / len(actual_set)
            recall = true_positives / len(expected_set)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            exact_match = 1 if actual_set == expected_set else 0
            
            return {"f1": f1, "precision": precision, "recall": recall, "exact_match": exact_match}
        except Exception:
            return {"f1": 0.0, "precision": 0.0, "recall": 0.0, "exact_match": 0}


# Mock conversations with expected preference extractions
TEST_CASES = [
    {
        "name": "explicit_color_preference",
        "conversation": [
            ChatMessage(role="user", content="I really love red dresses, do you have any?"),
            ChatMessage(role="assistant", content="Yes! We have several red dresses available. Let me show you some options."),
        ],
        "expected_preferences": [
            Preference(item_type="colour_group", value="red")
        ]
    },
    {
        "name": "multiple_color_preferences",
        "conversation": [
            ChatMessage(role="user", content="I'm looking for something in blue or maybe navy"),
            ChatMessage(role="assistant", content="Great choices! Here are some blue and navy items."),
            ChatMessage(role="user", content="Actually, I also like beige tones"),
        ],
        "expected_preferences": [
            Preference(item_type="colour_group", value="blue"),
            Preference(item_type="colour_group", value="navy"),
            Preference(item_type="colour_group", value="beige"),
        ]
    },
    {
        "name": "article_preference_from_tool_response",
        "conversation": [
            ChatMessage(role="user", content="Show me some summer tops"),
            ChatMessage(role="assistant", content="Here are some options: article_id: 0123456789 - Floral Summer Top, article_id: 0987654321 - Cotton Beach Blouse"),
            ChatMessage(role="user", content="I love that floral summer top! Add it to my wishlist"),
        ],
        "expected_preferences": [
            Preference(item_type="article", value="0123456789")
        ]
    },
    {
        "name": "mixed_preferences",
        "conversation": [
            ChatMessage(role="user", content="I prefer orange and warm colors in general"),
            ChatMessage(role="assistant", content="I found these items: article_id: 1111111111 - Orange Cardigan, article_id: 2222222222 - Coral Sweater"),
            ChatMessage(role="user", content="That orange cardigan is perfect!"),
        ],
        "expected_preferences": [
            Preference(item_type="colour_group", value="orange"),
            Preference(item_type="article", value="1111111111"),
        ]
    },
    {
        "name": "no_preferences",
        "conversation": [
            ChatMessage(role="user", content="What's your return policy?"),
            ChatMessage(role="assistant", content="Our return policy allows returns within 30 days of purchase."),
        ],
        "expected_preferences": []
    },
]


class TestPreferenceSignalsEval:
    """Evaluation tests for preference signals extraction."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc["name"] for tc in TEST_CASES])
    async def test_preference_extraction(self, test_case):
        """Test preference extraction against expected results."""
        conversation = test_case["conversation"]
        expected = test_case["expected_preferences"]
        
        # Run the agent
        result = await agent.run(conversation)
        actual_preferences = result.value
        
        # Format for evaluator
        expected_str = json.dumps([{"type": p.item_type, "value": p.value} for p in expected])
        actual_str = json.dumps([{"type": p.item_type, "value": p.value} for p in actual_preferences.prefs]) if actual_preferences and actual_preferences.prefs else "[]"
        
        # Use the same evaluator class as the SDK evaluation
        evaluator = PreferenceF1Evaluator()
        metrics = evaluator(response=actual_str, ground_truth=expected_str)
        
        print(f"\nTest: {test_case['name']}")
        print(f"Expected: {expected_str}")
        print(f"Actual:   {actual_str}")
        print(f"Metrics: {metrics}")
        
        # Record metrics for evaluation (no strict assertion for baseline)
        # The metrics are logged for analysis


async def run_full_evaluation():
    """Run evaluation on all test cases using Azure AI Evaluation SDK."""
    eval_data = []
    
    print("\n" + "=" * 60)
    print("RUNNING PREFERENCE EXTRACTION AGENT...")
    print("=" * 60)
    
    for test_case in TEST_CASES:
        conversation = test_case["conversation"]
        expected = test_case["expected_preferences"]
        
        # Run the agent
        result = await agent.run(conversation)
        actual_preferences = result.value
        
        # Format for Azure AI Evaluation
        conversation_text = "\n".join([f"{m.role}: {m.contents}" for m in conversation])
        expected_str = json.dumps([{"type": p.item_type, "value": p.value} for p in expected])
        actual_str = json.dumps([{"type": p.item_type, "value": p.value} for p in actual_preferences.prefs]) if actual_preferences and actual_preferences.prefs else "[]"
        
        eval_data.append({
            "query": conversation_text,
            "response": actual_str,
            "ground_truth": expected_str,
        })
        
        print(f"\n{test_case['name']}:")
        print(f"  Expected: {expected_str}")
        print(f"  Actual:   {actual_str}")
    
    # Write eval data to a JSONL file for Azure AI Evaluation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for item in eval_data:
            f.write(json.dumps(item) + '\n')
        eval_data_path = f.name
    
    # Run Azure AI Evaluation - SDK auto-aggregates numeric metrics!
    print("\n" + "=" * 60)
    print("AZURE AI EVALUATION SDK RESULTS")
    print("=" * 60)
    
    eval_result = evaluate(
        data=eval_data_path,
        evaluators={
            "preference": PreferenceF1Evaluator(),
        },
    )
    
    # The SDK returns a dict with 'rows' and 'metrics'
    # Row-level results are in eval_result['rows'], aggregate from there
    if 'rows' in eval_result and eval_result['rows']:
        rows = eval_result['rows']
        
        # Compute aggregates from row data
        print(f"\nAggregated Metrics:")
        metric_cols = [k for k in rows[0].keys() if 'preference' in k.lower()]
        for col in metric_cols:
            values = [r[col] for r in rows if col in r and isinstance(r[col], (int, float))]
            if values:
                avg = sum(values) / len(values)
                metric_name = col.split('.')[-1]
                print(f"  {metric_name}: {avg:.4f}")
    
    print(f"\nTotal rows evaluated: {len(eval_data)}")
    print("=" * 60)
    
    return eval_result


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_full_evaluation())
