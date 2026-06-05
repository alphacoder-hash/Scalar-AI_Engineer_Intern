import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from github import Github, GithubException
from sentence_transformers import SentenceTransformer
import chromadb

CODE_EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.yml', '.yaml', '.toml', '.sh'}
SKIP_FILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '.gitignore'}
MAX_FILE_SIZE = 30_000  # chars


# ── Minimal Document + splitter (no langchain) ────────────────────────────────

class Document:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


def _split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            newline = text.rfind('\n', start, end)
            if newline > start + chunk_size // 2:
                end = newline + 1
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


# ── Ingestion ─────────────────────────────────────────────────────────────────

class DataIngestion:
    def __init__(self):
        print("Loading embeddings model...")
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("Embeddings ready")
        self.documents: List[Document] = []

    # ── Resume ────────────────────────────────────────────────────────────────

    def ingest_resume(self, file_path: str):
        if not os.path.exists(file_path):
            print(f"Resume not found at {file_path}, using fallback summary.")
            self._add_candidate_summary()
            return

        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == '.docx':
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            print(f"Unsupported format: {ext}")
            return

        self.documents.append(Document(
            page_content=text,
            metadata={"source": "resume", "type": "resume",
                      "candidate": os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")}
        ))
        print(f"Resume ingested: {len(text)} chars")

    def _add_candidate_summary(self):
        candidate_name = os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")
        summary = f"""Candidate: {candidate_name}
GitHub: https://github.com/alphacoder-hash

Education: Computer Science undergraduate, Class of 2027

Experience:
- Centific Premier Hackathon 2.0 (Apr-May 2026): AI Agent Development Contributor, Hyderabad
  Built AI-powered Business Analyst Agent in Agentic SDLC platform.
  Ingested PDF, DOCX, PPTX, email, meeting inputs to auto-extract requirements.
  Generated Features, Epics, User Stories with HITL validation pipelines and confidence scoring.

Technical Skills:
- Languages: Python, JavaScript (ES6+), TypeScript, Java, C++
- AI/ML: Prompt Engineering, NLP, LLM-powered Apps, AI Evaluation, HITL Validation,
  Scikit-learn, Semantic Similarity Matching
- Frameworks: React.js, Node.js, Express.js, Django
- Data & APIs: REST APIs, JSON Processing, Data Pipelines, Vector Databases
- Tools: Git, GitHub, Vercel, Docker
- Core CS: DSA, OOP, DBMS, OS, Computer Networks

Achievements:
- CodeChef 4-Star, Max rating 1870
- LeetCode Max rating 1713
- Smart India Hackathon (SIH) 2025: Institute-level qualifier among 200+ teams
- Grand Finalist: PU Code Hackathon 2.0 and 3.0
- Participant: Vadodara Hackathon 6.0

Contact:
- Email: Vpandey1707@gmail.com
- LinkedIn: linkedin.com/in/vaibhav-pandey-4532b8290
- GitHub: github.com/alphacoder-hash

Applying for: AI Engineer role at Scaler"""
        self.documents.append(Document(
            page_content=summary,
            metadata={"source": "resume", "type": "summary", "candidate": candidate_name}
        ))
        print("Added candidate summary as resume fallback")

    # ── GitHub ────────────────────────────────────────────────────────────────

    def ingest_github_repos(self, username: str, repo_names: List[str] = None):
        print(f"\nIngesting GitHub repos for {username}")
        token = os.getenv("GITHUB_TOKEN")
        if token:
            from github import Auth
            g = Github(auth=Auth.Token(token))
        else:
            g = Github()

        try:
            user = g.get_user(username)
        except GithubException as e:
            print(f"Error fetching GitHub user: {e}")
            return

        repos = []
        if repo_names:
            for name in repo_names:
                try:
                    repos.append(user.get_repo(name))
                except GithubException as e:
                    print(f"  Could not fetch {name}: {e}")
        else:
            repos = list(user.get_repos())[:10]

        for repo in repos:
            print(f"  Processing: {repo.name}")
            self._ingest_repo(repo)

        print(f"Total documents: {len(self.documents)}")

    def _ingest_repo(self, repo):
        base_meta = {"source": "github", "repo": repo.name,
                     "url": repo.html_url, "language": repo.language or ""}

        # README
        try:
            readme = repo.get_readme()
            content = readme.decoded_content.decode('utf-8')
            self.documents.append(Document(
                page_content=content,
                metadata={**base_meta, "type": "readme", "file": "README.md"}
            ))
            print(f"    README ({len(content)} chars)")
        except Exception:
            pass

        # Key config files
        for fname in ['package.json', 'requirements.txt', 'pyproject.toml',
                      'Dockerfile', 'docker-compose.yml', 'Makefile']:
            try:
                fc = repo.get_contents(fname)
                content = fc.decoded_content.decode('utf-8')
                self.documents.append(Document(
                    page_content=f"File: {fname}\n\n{content}",
                    metadata={**base_meta, "type": "config", "file": fname}
                ))
                print(f"    {fname}")
            except Exception:
                pass

        # Source code files
        self._ingest_source_files(repo, base_meta)

        # Commit history (last 50)
        try:
            commits = list(repo.get_commits()[:50])
            lines = []
            for c in commits:
                msg = c.commit.message.strip().replace('\n', ' ')
                date = c.commit.author.date.strftime('%Y-%m-%d')
                lines.append(f"[{date}] {msg}")
            self.documents.append(Document(
                page_content=f"Commit history for {repo.name}:\n" + "\n".join(lines),
                metadata={**base_meta, "type": "commits", "file": "git_log"}
            ))
            print(f"    {len(commits)} commits")
        except Exception as e:
            print(f"    Commits error: {e}")

        # Repo summary
        try:
            desc = repo.description or "No description"
            lang = repo.language or "multiple languages"
            topics = ", ".join(repo.get_topics()) or "none"
            summary = (
                f"Repository: {repo.name}\nURL: {repo.html_url}\n"
                f"Description: {desc}\nPrimary language: {lang}\n"
                f"Topics: {topics}\nStars: {repo.stargazers_count} | Forks: {repo.forks_count}\n"
                f"Created: {repo.created_at.strftime('%Y-%m-%d')} | "
                f"Last updated: {repo.updated_at.strftime('%Y-%m-%d')}"
            )
            self.documents.append(Document(
                page_content=summary,
                metadata={**base_meta, "type": "repo_summary", "file": "meta"}
            ))
        except Exception:
            pass

    def _ingest_source_files(self, repo, base_meta, path="", depth=0):
        if depth > 3:
            return
        try:
            contents = repo.get_contents(path or "")
            if not isinstance(contents, list):
                contents = [contents]
            for item in contents:
                if item.type == "dir":
                    if item.name in ('node_modules', '.git', 'dist', 'build',
                                     '__pycache__', 'venv', '.venv', 'coverage',
                                     '.next', 'static'):
                        continue
                    self._ingest_source_files(repo, base_meta, item.path, depth + 1)
                elif item.type == "file":
                    if item.name in SKIP_FILES:
                        continue
                    if Path(item.name).suffix.lower() not in CODE_EXTENSIONS:
                        continue
                    if item.size > MAX_FILE_SIZE:
                        continue
                    try:
                        content = item.decoded_content.decode('utf-8', errors='replace')
                        if len(content.strip()) < 50:
                            continue
                        self.documents.append(Document(
                            page_content=f"File: {item.path}\n\n{content}",
                            metadata={**base_meta, "type": "source_code", "file": item.path}
                        ))
                    except Exception:
                        pass
        except Exception:
            pass

    # ── Vector store ──────────────────────────────────────────────────────────

    def create_vectorstore(self):
        if not self.documents:
            print("No documents to process!")
            return None

        # Split into chunks
        chunks: List[Document] = []
        for doc in self.documents:
            for chunk_text in _split_text(doc.page_content):
                chunks.append(Document(page_content=chunk_text, metadata=doc.metadata))

        print(f"\n{len(self.documents)} docs → {len(chunks)} chunks")

        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
        if Path(persist_dir).exists():
            shutil.rmtree(persist_dir)
            print(f"Wiped old vector store at {persist_dir}")

        print("Embedding (may take 2-3 min)...")
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.create_collection(
            name="persona_docs",
            metadata={"hnsw:space": "cosine"}
        )

        batch_size = 64
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.page_content for c in batch]
            embeddings = self.encoder.encode(texts, show_progress_bar=False).tolist()
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=[c.metadata for c in batch],
                ids=[f"chunk_{i + j}" for j in range(len(batch))]
            )
            print(f"  Embedded {min(i + batch_size, len(chunks))}/{len(chunks)}")

        print(f"Vector store saved at {persist_dir} ({len(chunks)} chunks)")
        return collection


def main():
    print("=" * 50)
    print("Data Ingestion for Sam - AI Persona")
    print("=" * 50)

    ingestion = DataIngestion()

    resume_path = os.getenv("RESUME_PATH", "./data/Vaibhav_Pandey_Intern_Resume.pdf")
    ingestion.ingest_resume(resume_path)

    github_username = os.getenv("GITHUB_USERNAME", "alphacoder-hash")
    github_repos = [r.strip() for r in os.getenv("GITHUB_REPOS", "").split(",") if r.strip()]
    ingestion.ingest_github_repos(github_username, github_repos if github_repos else None)

    if ingestion.documents:
        ingestion.create_vectorstore()
        print("\nData ingestion complete!")
    else:
        print("\nNo documents ingested!")


if __name__ == "__main__":
    main()
