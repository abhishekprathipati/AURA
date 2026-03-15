from transformers import pipeline
p = pipeline("text-classification", model="SamLowe/roberta-base-go_emotions", return_all_scores=True)
res = p("I have so many assignments and I feel like I can't handle anything")[0]
best = max(res, key=lambda x: x["score"])
print("Best:", best)
print("Keys:", res[0].keys())
