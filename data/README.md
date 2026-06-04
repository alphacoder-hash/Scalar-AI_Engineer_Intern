# Sample Resume Template

Place your actual resume as `data/resume.pdf` or `data/resume.docx`.

## What to Include

Your resume should contain:

### Education
- Degree, University, Year
- GPA (optional)
- Relevant coursework

### Experience
- Company names, roles, dates
- Key responsibilities and achievements
- Technologies used

### Skills
- Programming languages (Python, JavaScript, etc.)
- Frameworks (React, FastAPI, etc.)
- Tools (Git, Docker, AWS, etc.)
- Databases (PostgreSQL, MongoDB, etc.)

### Projects
- Project names and descriptions
- Technologies used
- Your role and contributions
- Links to GitHub repos (important!)

## Example Structure

```
John Doe
Software Engineer
john@example.com | github.com/johndoe

EDUCATION
Bachelor of Science in Computer Science
University of Example, 2020-2024
GPA: 3.8/4.0

EXPERIENCE
Software Engineer, Tech Company
June 2023 - Present
- Built scalable APIs using FastAPI and PostgreSQL
- Implemented RAG system with OpenAI embeddings
- Tech: Python, React, AWS, Docker

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: React, FastAPI, LangChain, PyTorch
Tools: Git, Docker, AWS, PostgreSQL, Redis

PROJECTS
AI Chat Assistant
- Built RAG-powered chatbot with 95% accuracy
- Integrated with Pinecone vector database
- GitHub: github.com/johndoe/ai-chat

E-commerce Platform
- Full-stack application with 10K+ users
- React frontend, FastAPI backend
- GitHub: github.com/johndoe/ecommerce
```

## Tips

1. **Be specific**: Include actual numbers, technologies, and achievements
2. **Link GitHub**: Make sure your repos are public and well-documented
3. **Quantify**: Use metrics (users, performance improvements, etc.)
4. **Recent**: Focus on last 3-5 years
5. **Relevant**: Highlight AI/ML, backend, or full-stack work for this role

## Testing

After placing your resume:
```bash
python scripts/ingest_data.py
```

Then test questions:
- "What is your educational background?"
- "What programming languages do you know?"
- "Tell me about your work experience"
- "What projects have you built?"
