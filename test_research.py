from agents.researcher import ResearchAgent

agent = ResearchAgent()
summary, docs = agent.research(["Green tea benefits", "Coffee"])

print("--- SUMMARY ---")
print(summary)
print("--- DOCS ---")
print([doc['source'] for doc in docs])
