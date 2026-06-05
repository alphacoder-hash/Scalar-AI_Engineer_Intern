import asyncio
import json
from datetime import datetime
from typing import List, Dict
import time
from pathlib import Path
import statistics

class Evaluator:
    def __init__(self):
        self.results = {
            "voice": {},
            "chat": {},
            "timestamp": datetime.now().isoformat()
        }
    
    async def evaluate_voice_latency(self, call_logs_file: str = "./evals/call_logs.jsonl"):
        """Evaluate voice call latency metrics"""
        if not Path(call_logs_file).exists():
            print("No call logs found")
            return
        
        latencies = []
        durations = []
        success_count = 0
        total_calls = 0
        
        with open(call_logs_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                total_calls += 1
                
                if data.get("latency"):
                    latencies.append(data["latency"])
                
                if data.get("duration"):
                    durations.append(data["duration"])
                
                if data.get("success"):
                    success_count += 1
        
        self.results["voice"] = {
            "total_calls": total_calls,
            "avg_latency": statistics.mean(latencies) if latencies else 0,
            "p95_latency": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0,
            "success_rate": success_count / total_calls if total_calls else 0,
            "avg_duration": statistics.mean(durations) if durations else 0
        }
        
        print(f"\n📞 Voice Metrics:")
        print(f"  Total calls: {total_calls}")
        print(f"  Avg first response: {self.results['voice']['avg_latency']:.2f}s")
        print(f"  P95 latency: {self.results['voice']['p95_latency']:.2f}s")
        print(f"  Success rate: {self.results['voice']['success_rate']*100:.1f}%")
    
    async def evaluate_rag_groundedness(self, test_questions: List[Dict]):
        """Evaluate RAG hallucination rate"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from rag_engine_groq import RAGEngine
        
        rag = RAGEngine()
        
        total = len(test_questions)
        correct = 0
        hallucinations = 0
        correct_rejections = 0
        
        results = []
        
        for item in test_questions:
            question = item["question"]
            expected_has_answer = item["has_answer"]
            
            result = await rag.query(question)
            answer = result["answer"].lower()
            
            # Check if model says "don't know"
            reject_phrases = ["don't have", "don't know", "not sure", "can't find"]
            is_rejection = any(phrase in answer for phrase in reject_phrases)
            
            if expected_has_answer:
                if not is_rejection:
                    correct += 1
                else:
                    # Should have answered but rejected
                    pass
            else:
                if is_rejection:
                    correct_rejections += 1
                else:
                    hallucinations += 1
            
            results.append({
                "question": question,
                "answer": answer,
                "expected_has_answer": expected_has_answer,
                "is_rejection": is_rejection,
                "correct": (expected_has_answer and not is_rejection) or (not expected_has_answer and is_rejection)
            })
        
        hallucination_rate = hallucinations / total
        
        self.results["chat"] = {
            "total_questions": total,
            "correct_answers": correct,
            "correct_rejections": correct_rejections,
            "hallucinations": hallucinations,
            "hallucination_rate": hallucination_rate,
            "accuracy": (correct + correct_rejections) / total
        }
        
        print(f"\n💬 Chat Groundedness:")
        print(f"  Total questions: {total}")
        print(f"  Hallucination rate: {hallucination_rate*100:.1f}%")
        print(f"  Accuracy: {self.results['chat']['accuracy']*100:.1f}%")
        
        return results
    
    async def test_retrieval_quality(self):
        """Test retrieval precision and recall"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from rag_engine_groq import RAGEngine
        
        rag = RAGEngine()
        
        # Sample queries with known relevant docs
        test_cases = [
            {
                "query": "What programming languages does the candidate know?",
                "relevant_sources": ["resume"]
            },
            {
                "query": "Tell me about the e-commerce project",
                "relevant_sources": ["github"]
            }
        ]
        
        precisions = []
        recalls = []
        
        for case in test_cases:
            result = await rag.query(case["query"])
            sources = result.get("sources", [])
            
            retrieved_types = [s["metadata"].get("source") for s in sources]
            relevant = case["relevant_sources"]
            
            # Precision: relevant retrieved / total retrieved
            if retrieved_types:
                precision = len([t for t in retrieved_types if t in relevant]) / len(retrieved_types)
                precisions.append(precision)
            
            # Recall: relevant retrieved / total relevant
            recall = len([t for t in retrieved_types if t in relevant]) / len(relevant)
            recalls.append(recall)
        
        avg_precision = statistics.mean(precisions) if precisions else 0
        avg_recall = statistics.mean(recalls) if recalls else 0
        
        print(f"\n🔍 Retrieval Quality:")
        print(f"  Precision: {avg_precision:.2f}")
        print(f"  Recall: {avg_recall:.2f}")
        
        return {
            "precision": avg_precision,
            "recall": avg_recall
        }
    
    def save_report(self, output_file: str = "./evals/metrics.json"):
        """Save evaluation results"""
        Path("./evals").mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")

# Test questions for groundedness evaluation
TEST_QUESTIONS = [
    {"question": "What is your educational background?", "has_answer": True},
    {"question": "What programming languages do you know?", "has_answer": True},
    {"question": "Tell me about your GitHub projects", "has_answer": True},
    {"question": "What is your favorite ice cream flavor?", "has_answer": False},
    {"question": "What car do you drive?", "has_answer": False},
    {"question": "How many years of experience do you have?", "has_answer": True},
    {"question": "What is your mother's maiden name?", "has_answer": False},
]

async def main():
    print("=== AI Persona Evaluation ===\n")
    
    evaluator = Evaluator()
    
    # Voice metrics
    await evaluator.evaluate_voice_latency()
    
    # Chat groundedness
    await evaluator.evaluate_rag_groundedness(TEST_QUESTIONS)
    
    # Retrieval quality
    await evaluator.test_retrieval_quality()
    
    # Save report
    evaluator.save_report()

if __name__ == "__main__":
    asyncio.run(main())
