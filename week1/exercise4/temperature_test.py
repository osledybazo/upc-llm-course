"""Ex 4 experiment: same call as call.py, run 3x at temperature 0.0 and 1.5."""
import os
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI(base_url=os.environ["OPENAI_ENDPOINT"], api_key=os.environ["OPENAI_API_KEY"])
model = os.environ["MODEL"]
PROMPT = os.environ.get("PROMPT", "Say hello in one sentence.")
for t in (0.0, 1.5):
    print(f"\n== temperature={t}  model={model}  prompt={PROMPT!r}")
    for i in range(3):
        r = client.chat.completions.create(model=model, temperature=t, messages=[
            {"role": "system", "content": "You are a terse assistant."},
            {"role": "user", "content": PROMPT}])
        print(f"  run {i+1}: {r.choices[0].message.content.strip()!r}  ({r.usage.completion_tokens} tok)")
