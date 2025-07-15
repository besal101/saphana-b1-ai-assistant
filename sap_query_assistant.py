import os
from typing import Dict, Literal, Optional, List, Any
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from hdbcli import dbapi

# Load environment variables
load_dotenv()

class QueryResponse(BaseModel):
    sqlQuery: str
    visualizationType: Literal["table", "bar_chart", "line_chart", "pie_chart"]
    summary: str
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class SAPQueryAssistant:
    def __init__(self):
        """Initialize the SAP Query Assistant with OpenAI configuration."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Database connection parameters
        self.db_params = {
            "address": os.getenv("SAP_HANA_HOST"),
            "port": int(os.getenv("SAP_HANA_PORT", "39015")),
            "user": os.getenv("SAP_HANA_USER"),
            "password": os.getenv("SAP_HANA_PASSWORD"),
            "database": os.getenv("SAP_HANA_DATABASE")
        }
        
        # Get the schema name from environment or use default
        self.schema = os.getenv("SAP_B1_SCHEMA", "SBODEMOUS")
        
        # Common SAP B1 table mappings with schema
        self.table_mappings = {
            "sales": [f"{self.schema}.OINV", f"{self.schema}.INV1", f"{self.schema}.OITM", f"{self.schema}.ORIN", f"{self.schema}.RIN1"],
            "inventory": [f"{self.schema}.OITM", f"{self.schema}.OITW", f"{self.schema}.OITB"],
            "customers": [f"{self.schema}.OCRD", f"{self.schema}.OCPR"],
            "purchases": [f"{self.schema}.OPOR", f"{self.schema}.POR1"],
            "financial": [f"{self.schema}.OJDT", f"{self.schema}.JDT1"],
            "brands": [f"{self.schema}.OITB"],
            "item_categories": [f"{self.schema}.OITC"],
            "item_groups": [f"{self.schema}.OITG"],
            "item_locations": [f"{self.schema}.OITL"],
            "items": [f"{self.schema}.OITM"],
            "warehouses": [f"{self.schema}.OITW"],
            "employees": [f"{self.schema}.OHEM"],
            "customers": [f"{self.schema}.OCRD"],
            "projects": [f"{self.schema}.OPRJ"],
            "journal_entries": [f"{self.schema}.OJDT"],
            "journal_entry_lines": [f"{self.schema}.JDT1"],
            "business_partners": [f"{self.schema}.OCRD"],
            "item_categories": [f"{self.schema}.OITC"],
        }

    def _get_db_connection(self):
        """Create and return a database connection."""
        try:
            conn = dbapi.connect(
                address=self.db_params["address"],
                port=self.db_params["port"],
                user=self.db_params["user"],
                password=self.db_params["password"],
                database=self.db_params["database"]
            )
            return conn
        except Exception as e:
            raise Exception(f"Failed to connect to SAP HANA database: {str(e)}")

    def _execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute the SQL query and return results as a list of dictionaries."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Execute the query
            cursor.execute(sql_query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch all results
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            conn.close()
            
            return results
        except Exception as e:
            raise Exception(f"Failed to execute query: {str(e)}")

    def _get_visualization_type(self, query: str) -> str:
        """Determine the most appropriate visualization type based on the query."""
        prompt = f"""
        Based on the following business query, determine the most appropriate visualization type:
        Query: {query}
        
        Choose from: table, bar_chart, line_chart, pie_chart
        
        Consider these specific rules:
        1. Use line_chart when the query mentions:
           - Time periods (days, months, years)
           - Trends, growth, or changes over time
           - Historical data
           - Words like 'trend', 'over time', 'history', 'growth'
        
        2. Use bar_chart when the query mentions:
           - Comparisons between categories
           - Rankings or top/bottom items
           - Aggregations by category
           - Words like 'top', 'bottom', 'compare', 'by category'
        
        3. Use pie_chart when the query mentions:
           - Proportions or percentages
           - Distribution of a whole
           - Market share
           - Words like 'distribution', 'percentage', 'share', 'proportion'
        
        4. Use table when:
           - Detailed data is needed
           - Multiple dimensions are involved
           - No clear visualization preference
           - Raw data is requested
        
        Return only the visualization type.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        
        viz_type = response.choices[0].message.content.strip().lower()
        return viz_type if viz_type in ["table", "bar_chart", "line_chart", "pie_chart"] else "table"

    def _generate_sql_query(self, query: str) -> str:
        """Generate SAP HANA SQL query from natural language input."""
        prompt = f"""
            Convert the following business question into a valid SAP HANA B1 SQL query:
            Question: {query}

            Requirements:
            1. Use proper SAP B1 table names and their documented relationships.
            2. Always include necessary JOINs between related tables (e.g., OINV with INV1, OCRD, etc.).
            3. Apply appropriate WHERE clauses based on user input or use-case.
            4. Use SAP HANA-specific SQL functions and syntax (e.g., TO_NVARCHAR(), CURRENT_DATE, etc.).
            5. Optimize queries for performance — avoid unnecessary subqueries, use indexes where applicable.
            6. Always prefix all table names with the provided schema: {self.schema}
            7. Strictly enclose all identifiers (table names, column names) in double quotes to maintain case sensitivity.
            8. ❌ NEVER create procedures or queries that perform CREATE, DELETE, or INSERT operations.
            9. If asked to perform create, delete, or insert operations, return the response:
                ERROR: Operation not allowed. This assistant only supports read-only SELECT queries.
            10. If the query is related to cancelled journal entries, check the "JDT1" table and the "Closed" column.


            Common tables:
            - "{self.schema}"."OINV": Sales Invoices
            - "{self.schema}"."ORIN": Credit Memos
            - "{self.schema}"."INV1": Invoice Lines
            - "{self.schema}"."RIN1": Credit Memo Lines
            - "{self.schema}"."OITM": Items
            - "{self.schema}"."OCRD": Business Partners
            - "{self.schema}"."OPRJ": Projects
            - "{self.schema}"."OJDT": Journal Entries
            - "{self.schema}"."OCRD": Business Partners
            - "{self.schema}"."OITB": Brands
            - "{self.schema}"."OITW": Warehouses
            - "{self.schema}"."OITC": Item Categories
            - "{self.schema}"."OITG": Item Groups
            - "{self.schema}"."OITL": Item Locations
            - "{self.schema}"."OITM": Items
            - "{self.schema}"."OHEM": Employees
            - "{self.schema}"."OPRJ": Projects
            - "{self.schema}"."OJDT": Journal Entries
            - "{self.schema}"."JDT1": Journal Entry Lines
            - "{self.schema}"."OCRD": Business Partners
            - "{self.schema}"."OITC": Item Categories

            Return only the SQL query.
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()

    def _generate_summary(self, query: str, sql_query: str, results: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate a human-readable summary of the query results."""
        prompt = f"""
        Create a concise, business-friendly summary of what the following SQL query will show:
        Query: {sql_query}
        
        Original question: {query}
        
        The summary should:
        1. Be clear and non-technical
        2. Focus on business insights
        3. Be no more than 2 sentences
        
        Return only the summary.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()

    def process_query(self, query: str, execute_query: bool = True) -> QueryResponse:
        """
        Process a natural language query and return structured response.
        
        Args:
            query (str): Natural language business query
            execute_query (bool): Whether to execute the query and return results
            
        Returns:
            QueryResponse: Structured response containing SQL query, visualization type, summary, and results
        """
        try:
            # Generate SQL query
            sql_query = self._generate_sql_query(query)
            
            # Determine visualization type
            viz_type = self._get_visualization_type(query)
            
            # Execute query if requested
            results = None
            error = None
            if execute_query:
                try:
                    results = self._execute_query(sql_query)
                except Exception as e:
                    error = str(e)
            
            # Generate summary
            summary = self._generate_summary(query, sql_query, results)
            
            return QueryResponse(
                sqlQuery=sql_query,
                visualizationType=viz_type,
                summary=summary,
                results=results,
                error=error
            )
            
        except Exception as e:
            raise Exception(f"Error processing query: {str(e)}")

# Example usage
if __name__ == "__main__":
    assistant = SAPQueryAssistant()
    result = assistant.process_query("Show me the top 5 selling products in the last 3 months")
    print(result.json(indent=2))