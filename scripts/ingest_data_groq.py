import os
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from github import Github
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

class DataIngestion:
    def __init__(self):
        print("Loading embeddings model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("Embeddings ready")
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.documents = []

    def ingest_resume(self, file_path: str):
        if not os.path.exists(file_path):
            print(f"Resume not found at {file_path}, skipping.")
            # Add hardcoded candidate summary as fallback
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
            metadata={"source": "resume", "type": "resume", "candidate": os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")}
        ))
        print(f"Resume ingested: {len(text)} characters")

    def _add_candidate_summary(self):
        """Fallback candidate info when resume PDF not available on server"""
        candidate_name = os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")
        summary = f"""
Candidate: {candidate_name}
GitHub: https://github.com/alphacoder-hash

Projects and Skills:
- Built IncidentCommander: A production-grade OpenEnv environment for evaluating AI agents as SRE.
  Stack: Python, FastAPI, Docker, Gradio, Hugging Face Spaces, OpenAI API
  Features: 8-service microservices simulation, tiered incident scenarios, keyword-based grading

- HotelBookingPro: Hotel booking system with JWT authentication and dynamic pricing using Segment Trees
  Stack: TypeScript, JWT, Node.js

- ideaspark-studio: TypeScript project
- localo: TypeScript project  
- Email-Spam-Classifier: ML project using Python/Jupyter Notebook
- ai-resume-analyzer1: JavaScript AI resume analysis tool
- Personal-Portfolio: TypeScript portfolio website

Technical Skills:
- Languages: Python, TypeScript, JavaScript
- Frameworks: FastAPI, React, Node.js
- AI/ML: OpenAI API, Hugging Face, LangChain, RAG systems
- DevOps: Docker, Railway, Hugging Face Spaces
- Databases: ChromaDB, vector databases

Applying for: AI Engineer role at Scaler
"""
        self.documents.append(Document(
            page_content=summary,
            metadata={"source": "resume", "type": "summary", "candidate": candidate_name}
        ))
        print("Added candidate summary as resume fallback")

    def ingest_github_repos(self, username: str, repo_names: List[str] = None):
        print(f"\nIngesting GitHub repos for {username}")
        token = os.getenv("GITHUB_TOKEN")
        g = Github(token) if token else Github()

        try:
            user = g.get_user(username)
        except Exception as e:
            print(f"Error fetching GitHub user: {e}")
            return

        if repo_names:
            repos = []
            for name in repo_names:
                try:
                    repos.append(user.get_repo(name))
                except Exception as e:
                    print(f"  Could not fetch {name}: {e}")
        else:
            repos = list(user.get_repos())[:10]

        for repo in repos:
            print(f"  Processing: {repo.name}")
            # README
            try:
                readme = repo.get_readme()
                content = readme.decoded_content.decode('utf-8')
                self.documents.append(Document(
                    page_content=content,
                    metadata={"source": "github", "type": "readme", "repo": repo.name, "url": repo.html_url, "language": repo.language or ""}
                ))
                print(f"    README added")
            except:
                pass

            # Key config files
            for fname in ['package.json', 'requirements.txt', 'pyproject.toml', 'Dockerfile']:
                try:
                    fc = repo.get_contents(fname)
                    content = fc.decoded_content.decode('utf-8')
                    self.documents.append(Document(
                        page_content=f"File: {fname}\n\n{content}",
                        metadata={"source": "github", "type": "config", "repo": repo.name, "file": fname}
                    ))
                    print(f"    {fname} added")
                except:
                    pass

            # Commits
            try:
                commits = list(repo.get_commits()[:20])
                commit_text = "\n".join([f"- {c.commit.message[:100]}" for c in commits])
                self.documents.append(Document(
                    page_content=f"Recent commits for {repo.name}:\n{commit_text}",
                    metadata={"source": "github", "type": "commits", "repo": repo.name}
                ))
                print(f"    Commits added")
            except:
                pass

        print(f"Total documents: {len(self.documents)}")

    def create_vectorstore(self):
        if not self.documents:
            print("No documents to process!")
            return None

        print(f"\nCreating vector store from {len(self.documents)} documents...")
        split_docs = self.splitter.split_documents(self.documents)
        print(f"Split into {len(split_docs)} chunks")

        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
        print("Embedding documents (may take 1-2 min)...")

        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=persist_dir
        )
        print(f"Vector store created at {persist_dir}")
        return vectorstore


def main():
    print("=" * 50)
    print("Data Ingestion for Sam - AI Persona")
    print("=" * 50)

    ingestion = DataIngestion()

    # Resume
    resume_path = os.getenv("RESUME_PATH", "./data/Vaibhav_Pandey_Intern_Resume.pdf")
    ingestion.ingest_resume(resume_path)

    # GitHub
    github_username = os.getenv("GITHUB_USERNAME", "alphacoder-hash")
    github_repos = [r.strip() for r in os.getenv("GITHUB_REPOS", "").split(",") if r.strip()]
    ingestion.ingest_github_repos(github_username, github_repos if github_repos else None)

    # Create vector store
    if ingestion.documents:
        ingestion.create_vectorstore()
        print("\nData ingestion complete!")
    else:
        print("\nNo documents ingested!")


if __name__ == "__main__":
    main()
