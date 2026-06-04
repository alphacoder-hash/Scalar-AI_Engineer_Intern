import asyncio
import json
from datetime import datetime
from typing import List, Dict
import time
from pathlib import Path
import statistics
import sys
sys.path.insert(0, './backend')
sys.path.insert(0, './scripts')

from golden_qa import GOLDEN_QA_SET, is_rejection

class Evaluator:
    def __init__(self):
        self.results = {
            "voice": {},
            "chat": {},
            "retrieval": {},
            "timestamp": datetime.now().isoformat()
        }
    
    async def evaluate_voice_latency(self, call_logs_file: str = "./evals/call_logs.jsonl"):
        """Evaluate voice call latency metrics"""
        if not Path(call_logs_file).exists():
            print("No call logs found. Make test calls first.")
            self.results["voice"] = {"status": "no_data"}
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
    
    async def evaluate_rag_groundedness(self, test_questions: List[Dict] = None):
        """Evaluate RAG hallucination rate"""
        from rag_engine import RAGEngine
        
        if test_questions is None:
            test_questions = GOLDEN_QA_SET
        
        rag = RAGEngine()
        
        if not rag.is_ready():
            print("RAG engine not ready. Run ingest_data.py first.")
            self.results["chat"] = {"status": "not_ready"}
            return []
        
        total = len(test_questions)
        correct = 0
        hallucinations = 0
        correct_rejections = 0
        adversarial_blocked = 0
        
        results = []
        
        for item in test_questions:
            question = item["question"]
            expected_has_answer = item["has_answer"]
            category = item.get("category", "unknown")
            
            result = await rag.query(question)
            answer = result["answer"]
            answer_lower = answer.lower()
            
            # Check if model rejected
            rejected = is_rejection(answer)
            
            # Check adversarial defense
            if category == "adversarial":
                if rejected or "discuss the candidate" in answer_lower:
                    adversarial_blocked += 1
                    correct_rejections += 1
                else:
                    hallucinations += 1
            elif expected_has_answer:
                if not rejected:
                    correct += 1
            else:
                if rejected:
                    correct_rejections += 1
                else:
                    hallucinations += 1
            
            results.append({
                "question": question,
                "answer": answer[:200],
                "expected_has_answer": expected_has_answer,
                "is_rejection": rejected,
                "category": category,
                "correct": (expected_has_answer and not rejected) or (not expected_has_answer and rejected)
            })
        
        hallucination_rate = hallucinations / total if total > 0 else 0
        
        self.results["chat"] = {
            "total_questions": total,
            "correct_answers": correct,
            "correct_rejections": correct_rejections,
            "hallucinations": hallucinations,
            "adversarial_blocked": adversarial_blocked,
            "hallucination_rate": hallucination_rate,
            "accuracy": (correct + correct_rejections) / total if total > 0 else 0
        }
        
        print(f"\n💬 Chat Groundedness:")
        print(f"  Total questions: {total}")
        print(f"  Correct answers: {correct}")
        print(f"  Correct rejections: {correct_rejections}")
        print(f"  Hallucinations: {hallucinations}")
        print(f"  Adversarial blocked: {adversarial_blocked}")
        print(f"  Hallucination rate: {hallucination_rate*100:.1f}%")
        print(f"  Accuracy: {self.results['chat']['accuracy']*100:.1f}%")
        
        # Save detailed results
        Path("./evals").mkdir(exist_ok=True)
        with open("./evals/groundedness_details.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    async def test_retrieval_quality(self):
        """Test retrieval precision and recall"""
        from rag_engine import RAGEngine
        
        rag = RAGEngine()
        
        if not rag.is_ready():
            print("RAG engine not ready.")
            return
        
        # Sample queries with known relevant docs
        test_cases = [
            {
                "query": "What programming languages does the candidate know?",
                "relevant_sources": ["resume"]
            },
            {
                "query": "Tell me about the GitHub projects",
                "relevant_sources": ["github"]
            },
            {
                "query": "What was the candidate's education?",
                "relevant_sources": ["resume"]
            },
            {
                "query": "Describe the tech stack in the projects",
                "relevant_sources": ["github"]
            }
        ]
        
        precisions = []
        recalls = []
        
        for case in test_cases:
            result = await rag.query(case["query"])
            sources = result.get("sources", [])
            
            if not sources:
                continue
            
            retrieved_types = [s["metadata"].get("source") for s in sources]
            relevant = case["relevant_sources"]
            
            # Precision: relevant retrieved / total retrieved
            relevant_retrieved = [t for t in retrieved_types if t in relevant]
            if retrieved_types:
                precision = len(relevant_retrieved) / len(retrieved_types)
                precisions.append(precision)
            
            # Recall: relevant retrieved / total relevant
            recall = len(relevant_retrieved) / len(relevant)
            recalls.append(recall)
        
        avg_precision = statistics.mean(precisions) if precisions else 0
        avg_recall = statistics.mean(recalls) if recalls else 0
        f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        
        self.results["retrieval"] = {
            "precision": avg_precision,
            "recall": avg_recall,
            "f1_score": f1_score
        }
        
        print(f"\n🔍 Retrieval Quality:")
        print(f"  Precision: {avg_precision:.2f}")
        print(f"  Recall: {avg_recall:.2f}")
        print(f"  F1 Score: {f1_score:.2f}")
        
        return self.results["retrieval"]
    
    def save_report(self, output_file: str = "./evals/metrics.json"):
        """Save evaluation results"""
        Path("./evals").mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")

async def main():
    print("=== AI Persona Evaluation ===\n")
    
    evaluator = Evaluator()
    
    # Voice metrics
    await evaluator.evaluate_voice_latency()
    
    # Chat groundedness
    await evaluator.evaluate_rag_groundedness()
    
    # Retrieval quality
    await evaluator.test_retrieval_quality()
    
    # Save report
    evaluator.save_report()

if __name__ == "__main__":
    asyncio.run(main())
