"""Extract sentence exercises and contextual hints from article text."""

import re


def sentence_candidates(passages):
    """Extract sentences and their context from the same source paragraph."""
    candidates = []
    for passage in passages:
        for match in re.finditer(r'.+?(?:[.!?][”\"\'’]*(?=\s+[A-Z“\"0-9]|$)|$)', passage["text"], re.DOTALL):
            text = match.group().strip()
            if len(text.split()) < 2:
                continue
            start = match.start() + len(match.group()) - len(match.group().lstrip())
            end = match.end() - len(match.group()) + len(match.group().rstrip())
            context = passage["text"][:start] + "[배열할 문장]" + passage["text"][end:]
            prompt = f"{passage['number']}문단 해석\n{passage['translation']}\n\n원문 문맥\n{context}"
            candidates.append(dict(text=text, prompt=prompt, source=passage["source"],
                                   paragraph_number=passage["number"]))
    return candidates


