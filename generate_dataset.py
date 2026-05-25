import json
import random

data = []

# ── 1. VALID MCQ FILE EXAMPLES ──────────────────────
valid_mcq_files = [
    "1. What is Python?\nA) A snake\nB) A programming language\nC) A database\nD) An OS\nAnswer: B",
    "Q1. What does HTML stand for?\na) Hyper Text Markup Language\nb) High Tech Modern Language\nc) Hyper Transfer Mode Link\nd) None\nCorrect: a",
    "1. Which data structure uses FIFO?\nA) Stack\nB) Queue\nC) Tree\nD) Graph\nAns: B",
    "Question 1: What is RAM?\n(A) Read Access Memory\n(B) Random Access Memory\n(C) Run At Maximum\n(D) Real Address Mode\nAnswer: (B)",
    "MCQ 1: Which language is used for web styling?\nA. Python\nB. Java\nC. CSS\nD. C++\nAnswer: C",
    "1. What is a primary key?\nA) Foreign key\nB) Unique identifier\nC) Index\nD) Constraint\nAns: B\n\n2. What is SQL?\nA) A language\nB) A database\nC) A server\nD) None\nAns: A",
]

# ── 2. INVALID FILE EXAMPLES ─────────────────────────
invalid_files = [
    "The water cycle involves evaporation, condensation, and precipitation...",
    "Dear Sir, I am writing to apply for the position of software engineer...",
    "Chapter 1: Introduction to Machine Learning\nMachine learning is a subset of AI...",
    "Invoice #1234\nItem: Laptop\nQuantity: 1\nPrice: $999",
    "Once upon a time in a land far away, there lived a dragon...",
    "Name: John\nAge: 25\nCity: Chennai\nPhone: 9876543210",
    "Monthly Sales Report\nJanuary: $5000\nFebruary: $7000\nMarch: $6000",
    "Recipe: Chocolate Cake\n1. Mix flour and sugar\n2. Add eggs\n3. Bake at 180C",
]

# ── 3. APP COMMANDS ───────────────────────────────────
app_commands = [
    ("show all questions", '{"action": "show", "filter": "all"}'),
    ("show python questions", '{"action": "show", "filter": "python"}'),
    ("show java questions", '{"action": "show", "filter": "java"}'),
    ("show sql questions", '{"action": "show", "filter": "sql"}'),
    ("display all mcqs", '{"action": "show", "filter": "all"}'),
    ("filter questions by topic python", '{"action": "show", "filter": "python"}'),
    ("delete question 3", '{"action": "delete", "target": "3"}'),
    ("remove question 5", '{"action": "delete", "target": "5"}'),
    ("delete all questions", '{"action": "delete", "target": "all"}'),
    ("edit question 2", '{"action": "edit", "target": "2"}'),
    ("update question 4", '{"action": "edit", "target": "4"}'),
    ("modify question 1", '{"action": "edit", "target": "1"}'),
    ("add a new question", '{"action": "add"}'),
    ("insert a question", '{"action": "add"}'),
    ("export questions", '{"action": "export"}'),
    ("download my questions", '{"action": "export"}'),
    ("save questions to file", '{"action": "export"}'),
]

# ── 4. GENERAL KNOWLEDGE REJECTIONS ──────────────────
rejections = [
    "who is elon musk?",
    "what is the weather today?",
    "tell me a joke",
    "write a poem",
    "what is the capital of india?",
    "explain gravity",
    "who won the world cup?",
    "what is cooking?",
    "write an email for me",
    "what is the stock price?",
    "tell me about history",
    "what is love?",
    "recommend a movie",
    "translate this to french",
    "what is the meaning of life?",
    "write a story",
    "what is music?",
    "who is the president?",
    "what is fashion?",
    "what is python?",
    "explain machine learning",
    "generate a mcq question",
    "create a java question",
    "what is recursion?",
    "explain data structures",
]

rejection_response = "I only handle MCQ file validation and app commands. I cannot answer general questions."

# ── BUILD DATASET ─────────────────────────────────────

# Valid MCQ files — 35 each
for sample in valid_mcq_files:
    for _ in range(35):
        data.append({
            "prompt": f"Check if this file contains MCQ questions:\n\n{sample}",
            "completion": "✅ Valid MCQ file. Questions detected."
        })

# Invalid files — 25 each
for sample in invalid_files:
    for _ in range(25):
        data.append({
            "prompt": f"Check if this file contains MCQ questions:\n\n{sample}",
            "completion": "❌ Not an MCQ file. Please upload a file containing MCQ questions."
        })

# App commands — 30 each
for prompt, completion in app_commands:
    for _ in range(30):
        data.append({"prompt": prompt, "completion": completion})

# Rejections — 25 each
for q in rejections:
    for _ in range(25):
        data.append({"prompt": q, "completion": rejection_response})

random.shuffle(data)

with open("mcq_validator_dataset.jsonl", "w") as f:
    for item in data:
        f.write(json.dumps(item) + "\n")

print(f"✅ Dataset created: {len(data)} examples")