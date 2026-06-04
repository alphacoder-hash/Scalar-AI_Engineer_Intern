import os
from typing import List, Dict, Optional, AsyncIterator
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import uuid

class RAGEngine:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3, streaming=True)
        self.vectorstore = None
        self.sessions = {}
        self._initialize_vectorstore()
        
    def _initialize_vectorstore(self):
        """Load or create vector store"""
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        
        if os.path.exists(persist_dir):
            self.vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=self.embeddings
            )
        else:
            print("Warning: Vector store not initialized. Run ingest_data.py first.")
    
    def _get_session(self, session_id: Optional[str] = None) -> tuple:
        """Get or create session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.sessions:
            memory = ConversationBufferWindowMemory(
                k=5,
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            self.sessions[session_id] = memory
        
        return session_id, self.sessions[session_id]
    
    def _create_prompt(self) -> PromptTemplate:
        """Create grounded prompt template"""
        template = """You are an AI persona representing the candidate. Answer questions based ONLY on the provided context from their resume, GitHub repositories, and projects.

Context from knowledge base:
{context}

Chat History:
{chat_history}

Question: {question}

Instructions:
1. Answer ONLY using information from the context above
2. If the answer is not in the context, say "I don't have that specific information in my knowledge base"
3. Be conversational and natural, but stay grounded in facts
4. For GitHub repos, reference specific files, commits, or design decisions from the context
5. For availability questions, acknowledge and offer to check the calendar
6. DO NOT make up information or hallucinate

Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
    
    async def query(self, message: str, session_id: Optional[str] = None) -> Dict:
        """Query RAG system"""
        if not self.vectorstore:
            return {
                "answer": "RAG system not initialized. Please contact the administrator.",
                "session_id": session_id or str(uuid.uuid4()),
                "sources": []
            }
        
        session_id, memory = self._get_session(session_id)
        
        # Retrieve relevant documents
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 5}
        )
        
        # Create chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": self._create_prompt()},
            return_source_documents=True,
            verbose=False
        )
        
        # Query
        result = chain({"question": message})
        
        # Extract sources
        sources = []
        for doc in result.get("source_documents", []):
            sources.append({
                "content": doc.page_content[:200],
                "metadata": doc.metadata
            })
        
        return {
            "answer": result["answer"],
            "session_id": session_id,
            "sources": sources
        }
    
    async def query_stream(self, message: str, session_id: Optional[str] = None) -> AsyncIterator[Dict]:
        """Stream RAG responses for lower latency"""
        if not self.vectorstore:
            yield {
                "type": "error",
                "content": "RAG system not initialized"
            }
            return
        
        session_id, memory = self._get_session(session_id)
        
        # Retrieve relevant documents
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        docs = retriever.get_relevant_documents(message)
        
        # Build context
        context = "\n\n".join([doc.page_content for doc in docs])
        chat_history = memory.load_memory_variables({}).get("chat_history", [])
        
        # Stream response
        prompt = self._create_prompt().format(
            context=context,
            chat_history=chat_history,
            question=message
        )
        
        full_response = ""
        async for chunk in self.llm.astream(prompt):
            content = chunk.content
            full_response += content
            yield {
                "type": "content",
                "content": content,
                "session_id": session_id
            }
        
        # Save to memory
        memory.save_context({"question": message}, {"answer": full_response})
        
        # Send sources
        sources = [{"content": doc.page_content[:200], "metadata": doc.metadata} for doc in docs]
        yield {
            "type": "sources",
            "sources": sources,
            "session_id": session_id
        }
    
    def is_ready(self) -> bool:
        """Check if RAG is ready"""
        return self.vectorstore is not None
