from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sap_query_assistant import SAPQueryAssistant, QueryResponse

app = FastAPI(
    title="SAP HANA B1 Query Assistant",
    description="AI-powered assistant that translates natural language questions into SAP HANA B1 SQL queries",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    execute_query: bool = True

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query and return structured response.
    
    Args:
        request (QueryRequest): Natural language business query and execution flag
        
    Returns:
        QueryResponse: Structured response containing SQL query, visualization type, summary, and results
    """
    try:
        assistant = SAPQueryAssistant()
        result = assistant.process_query(request.query, execute_query=request.execute_query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 