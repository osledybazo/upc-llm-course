# Exercise 3 — probes on ministral-3:14b

## Zero-shot task

**Prompt:**
```
Summarise the plot of Romeo and Juliet in exactly two sentences.
```
**Answer** (35.4s, 11.2 tok/s):
```
*Romeo and Juliet* is a tragic play about two young lovers from feuding noble families in Verona—Romeo (a Montague) and Juliet (a Capulet)—whose secret marriage and untimely deaths ultimately reconcile their warring households.

Driven by fate, miscommunication, and impulsive violence (including Romeo’s banishment and Juliet’s forced marriage plot), they die by suicide, leaving behind a legacy of peace but also the devastating cost of hatred.
```

## Few-shot made-up rule

**Prompt:**
```
blorp(cat) = tac9
blorp(house) = esuoh5
blorp(sun) = nus3
blorp(table) = ?
```
**Answer** (29.8s, 11.3 tok/s):
```
To solve this pattern, let's analyze the given examples:

1. **blorp(cat) = tac9**
   - "cat" reversed is "tac", then append the number of letters (3) → **tac3** (but given as **tac9**, which suggests a different rule).
   - Alternatively, if we consider the ASCII codes of the letters:
     - c = 99, a = 97, t = 116 → 99 + 97 + 116 = 312 → 312 mod 10 = 2 (doesn't match 9).
   - Another approach: count vowels (a = 1 vowel) → 1, but given output ends with 9. Doesn't fit.

2. **blorp(house) = esuoh5**
   - "house" reversed is "esuoh", then append the number of letters (5) → **esuoh5** (matches perfectly).
   - This suggests the rule is: **reverse the word + append its length**.

3. **blorp(sun) = nus3**
   - "sun" reversed is "nus", then append the number of letters (3) → **nus3** (matches).

### Applying the rule to **blorp(table)**:
1. Reverse "table" → "elbat".
2. Count letters in "table" → 5.
3. Append the count → **elbat5**.

### Final answer:
**blorp(table) = elbat5**
```

## Strict format (JSON only)

**Prompt:**
```
List three European capitals with their country and approximate population. Answer ONLY with a JSON array, no prose, no markdown.
```
**Answer** (9.4s, 11.0 tok/s):
```
```json
[
    {
        "capital": "Berlin",
        "country": "Germany",
        "population": 3769000
    },
    {
        "capital": "Madrid",
        "country": "Spain",
        "population": 3266000
    },
    {
        "capital": "Rome",
        "country": "Italy",
        "population": 2873000
    }
]
```
```

## Language switch (Spanish)

**Prompt:**
```
¿Cuál es la diferencia entre 'ser' y 'estar'? Responde en dos frases.
```
**Answer** (11.3s, 11.2 tok/s):
```
En español, **"ser"** expresa **esencia, características permanentes o identidades** (ej. *"Soy médico"*, *"Es alto"*, *"Son las tres"*), mientras que **"estar"** indica **estados temporales, ubicaciones o condiciones cambiantes** (ej. *"Estoy cansado"*, *"Está en casa"*, *"El café está caliente"*).

La clave está en si la cualidad es **inherente** (ser) o **transitoria** (estar), aunque hay excepciones que dependen del contexto cultural o idiomático.
```

## Language switch (Catalan)

**Prompt:**
```
Explica'm en una frase què és un transformer en intel·ligència artificial.
```
**Answer** (8.4s, 11.8 tok/s):
```
Un **transformer** en intel·ligència artificial és un model d'aprenentatge profund que processa dades (com text o seqüències) analitzant relacions entre tots els elements simultàniament mitjançant l'atenció (*attention*), permetent comprendre context i dependències en qualsevol posició, cosa que el fa especialment potent per tasques com la traducció, generació de llenguatge o anàlisi de dades complexes.
```

## Small code

**Prompt:**
```
Write a Python function is_palindrome(s) that ignores case and punctuation. Code only.
```
**Answer** (4.0s, 12.7 tok/s):
```
```python
import re

def is_palindrome(s):
    s = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    return s == s[::-1]
```
```

## Counting letters

**Prompt:**
```
How many letters 'r' are in the word 'strawberry'? Answer with just the number.
```
**Answer** (0.4s, 21.2 tok/s):
```
3
```

## Arithmetic

**Prompt:**
```
What is 4831 * 297? Answer with just the number.
```
**Answer** (0.9s, 15.1 tok/s):
```
1,433,507
```

## False premise

**Prompt:**
```
Why did Albert Einstein win the 1931 Nobel Prize in Chemistry?
```
**Answer** (11.4s, 11.5 tok/s):
```
Albert Einstein did **not** win the Nobel Prize in Chemistry in 1931—or at any other time.

He was awarded the **1921 Nobel Prize in Physics** (officially announced in 1922) **"for his services to Theoretical Physics, and especially for his discovery of the law of the photoelectric effect."**

The Nobel Prize in Chemistry has been awarded to other scientists, such as:
- **1931**: Carl Bosch and Friedrich Bergius (for contributions to high-pressure chemistry in industrial synthesis).

Would you like details on Einstein’s Nobel Prize in Physics or another topic?
```

## Fake citation

**Prompt:**
```
Give me the exact title, authors and DOI of the 2019 paper by Marc Alier on tokenization in Catalan LLMs.
```
**Answer** (18.5s, 11.4 tok/s):
```
I don't have direct access to the specific paper you're asking about in my knowledge base. However, I can guide you on how to find this information:

1. **Search for the paper** using academic search engines like:
   - [Google Scholar](https://scholar.google.com)
   - [Semantic Scholar](https://www.semanticscholar.org)
   - [arXiv](https://arxiv.org) (if it's a preprint)

2. **Try these keywords** in your search:
   - *"Marc Alier Catalan tokenization LLM 2019"*
   - *"Marc Alier language modeling Catalan NLP 2019"*

3. **If you find the paper**, the title, authors, and DOI will typically be listed in the search results or on the paper's page.

### Alternative Approach:
If you provide me with the **exact title or a snippet** from the paper, I can help verify or confirm details.
```

## Recent knowledge

**Prompt:**
```
Who won the most recent FIFA World Cup, and in what year? One sentence.
```
**Answer** (1.8s, 13.3 tok/s):
```
The most recent FIFA World Cup was won by **Argentina** in **2022**.
```
