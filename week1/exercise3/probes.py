"""Ex 3: send exploratory prompts to the local Ollama model, each in a fresh chat; save transcript."""
import json, sys, time, urllib.request
MODEL = sys.argv[1] if len(sys.argv) > 1 else "ministral-3:14b"
PROBES = [
 ("Zero-shot task", "Summarise the plot of Romeo and Juliet in exactly two sentences."),
 ("Few-shot made-up rule", "blorp(cat) = tac9\nblorp(house) = esuoh5\nblorp(sun) = nus3\nblorp(table) = ?"),
 ("Strict format (JSON only)", "List three European capitals with their country and approximate population. Answer ONLY with a JSON array, no prose, no markdown."),
 ("Language switch (Spanish)", "¿Cuál es la diferencia entre 'ser' y 'estar'? Responde en dos frases."),
 ("Language switch (Catalan)", "Explica'm en una frase què és un transformer en intel·ligència artificial."),
 ("Small code", "Write a Python function is_palindrome(s) that ignores case and punctuation. Code only."),
 ("Counting letters", "How many letters 'r' are in the word 'strawberry'? Answer with just the number."),
 ("Arithmetic", "What is 4831 * 297? Answer with just the number."),
 ("False premise", "Why did Albert Einstein win the 1931 Nobel Prize in Chemistry?"),
 ("Fake citation", "Give me the exact title, authors and DOI of the 2019 paper by Marc Alier on tokenization in Catalan LLMs."),
 ("Recent knowledge", "Who won the most recent FIFA World Cup, and in what year? One sentence."),
]
out = [f"# Exercise 3 — probes on {MODEL}\n"]
for title, prompt in PROBES:
    body = json.dumps({"model": MODEL, "stream": False, "messages": [{"role": "user", "content": prompt}]}).encode()
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})))
    dt = time.time() - t
    tps = r["eval_count"] / (r["eval_duration"] / 1e9)
    out.append(f"\n## {title}\n\n**Prompt:**\n```\n{prompt}\n```\n**Answer** ({dt:.1f}s, {tps:.1f} tok/s):\n```\n{r['message']['content'].strip()}\n```\n")
    print(out[-1], flush=True)
open(f"transcript_{MODEL.replace(':','_')}.md", "w").write("".join(out))
