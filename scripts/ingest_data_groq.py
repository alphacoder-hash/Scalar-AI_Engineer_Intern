import os
import sys
from pathlib import Path
from typing import List
from github import Github
from pypdf import PdfReader
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document as LangchainDocument
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class DataIngestion:
    def __init__(self):
        print("Initializing embeddings (this may take a moment on first run)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("✓ Embeddings ready")
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.documents = []
    
    def ingest_resume(self, file_path: str):
        """Ingest resume (PDF or DOCX)"""
        print(f"\nIngesting resume from {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ Resume not found at {file_path}")
            return
        
        if file_path.endswith('.pdf'):
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() for page in reader.pages])
        elif file_path.endswith('.docx'):
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        else:
            print("❌ Unsupported resume format. Use PDF or DOCX.")
            return
        
        doc = LangchainDocument(
            page_content=text,
            metadata={
                "source": "resume",
                "type": "resume",
                "file": file_path,
                "candidate": os.getenv("CANDIDATE_NAME", "Candidate")
            }
        )
        
        self.documents.append(doc)
        print(f"✓ Resume ingested: {len(text)} characters")
    
    def ingest_github_repos(self, username: str, repo_names: List[str] = None):
        """Ingest GitHub repositories"""
        print(f"\nIngesting GitHub repos for {username}")
        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("⚠ Warning: GITHUB_TOKEN not set. Rate limits will apply.")
        
        g = Github(token) if token else Github()
        
        try:
            user = g.get_user(username)
        except Exception as e:
            print(f"❌ Error fetching GitHub user: {str(e)}")
            return
        
        if repo_names:
            repos = []
            for name in repo_names:
                try:
                    repos.append(user.get_repo(name))
                except Exception as e:
                    print(f"  ⚠ Couldn't fetch {name}: {str(e)}")
        else:
            repos = list(user.get_repos())[:10]
        
        for repo in repos:
            print(f"  Processing: {repo.name}")
            
            # README
            try:
                readme = repo.get_readme()
                content = readme.decoded_content.decode('utf-8')
                doc = LangchainDocument(
                    page_content=content,
                    metadata={
                        "source": "github",
                        "type": "readme",
                        "repo": repo.name,
                        "url": repo.html_url,
                        "language": repo.language
                    }
                )
                self.documents.append(doc)
                print(f"    ✓ README")
            except Exception as e:
                print(f"    ⚠ No README: {str(e)}")
            
            # Key files
            key_files = [
                'package.json', 'requirements.txt', 'pyproject.toml', 
                'setup.py', 'docker-compose.yml', 'Dockerfile'
            ]
            
            for file_name in key_files:
                try:
                    file_content = repo.get_contents(file_name)
                    content = file_content.decoded_content.decode('utf-8')
                    doc = LangchainDocument(
                        page_content=f"File: {file_name}\n\n{content}",
                        metadata={
                            "source": "github",
                            "type": "config",
                            "repo": repo.name,
                            "file": file_name,
                            "url": repo.html_url
                        }
                    )
                    self.documents.append(doc)
                    print(f"    ✓ {file_name}")
                except:
                    pass
            
            # Recent commits
            try:
                commits = list(repo.get_commits()[:20])
                commit_summary = "\n".join([
                    f"- {c.commit.message[:100]}" 
                    for c in commits
                ])
                
                doc = LangchainDocument(
                    page_content=f"Recent commits for {repo.name}:\n{commit_summary}",
                    metadata={
                        "source": "github",
                        "type": "commits",
                        "repo": repo.name,
                        "url": repo.html_url
                    }
                )
                self.documents.append(doc)
                print(f"    ✓ Commits")
            except:
                pass
            
            print(f"  ✓ {repo.name}: Total {len(self.documents)} docs")
    
    def create_vectorstore(self):
        """Create and persist vector store"""
        print(f"\n📦 Creating vector store from {len(self.documents)} documents")
        
        if not self.documents:
            print("❌ No documents to process. Check resume and GitHub configuration.")
            return None
        
        # Split documents
        split_docs = self.text_splitter.split_documents(self.documents)
        print(f"✓ Split into {len(split_docs)} chunks")
        
        # Create vector store
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        
        print("🔄 Embedding documents (this may take 1-2 minutes)...")
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=persist_dir
        )
        
        print(f"✓ Vector store created at {persist_dir}")
        return vectorstore

def main():
    print("="*60)
    print("   Data Ingestion for Sam - AI Persona")
    print("="*60)
    
    ingestion = DataIngestion()
    
    # Ingest resume
    resume_path = os.getenv("RESUME_PATH", "./data/Vaibhav_Pandey_Intern_Resume.pdf")
    if os.path.exists(resume_path):
        ingestion.ingest_resume(resume_path)
    else:
        print(f"❌ Resume not found at {resume_path}")
        print("   Place your resume at data/resume.pdf")
    
    # Ingest GitHub repos
    github_username = os.getenv("GITHUB_USERNAME")
    github_repos = os.getenv("GITHUB_REPOS", "").split(",")
    github_repos = [r.strip() for r in github_repos if r.strip()]
    
    if github_username:
        ingestion.ingest_github_repos(
            github_username,
            github_repos if github_repos else None
        )
    else:
        print("⚠ Warning: GITHUB_USERNAME not set in .env")
    
    # Create vector store
    if ingestion.documents:
        ingestion.create_vectorstore()
        print("\n" + "="*60)
        print("✅ Data ingestion complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run backend: cd backend && python -m uvicorn app:app --reload")
        print("2. Test chat: http://localhost:8000/health")
    else:
        print("\n❌ No documents ingested. Check your configuration.")

if __name__ == "__main__":
    main()
