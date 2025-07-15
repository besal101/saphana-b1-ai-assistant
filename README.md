# SAP HANA B1 Query Assistant

An AI-powered assistant that translates natural language questions into SAP HANA B1 SQL queries.

## Features

- Natural language processing for business queries
- Automatic SQL query generation for SAP HANA B1
- Support for various visualization types
- Structured JSON output format
- Query optimization and validation
- Direct query execution and result retrieval
- Error handling and reporting

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:

```
OPENAI_API_KEY=your_api_key_here
SAP_HANA_HOST=your_host
SAP_HANA_PORT=39015
SAP_HANA_USER=your_username
SAP_HANA_PASSWORD=your_password
SAP_HANA_DATABASE=your_database
```

## Usage

The assistant accepts natural language questions about your SAP B1 data and returns:

- A valid SAP HANA SQL query
- Recommended visualization type
- Human-readable summary of the results
- Actual query results (if execution is enabled)
- Any errors that occurred during execution

Example:

```python
from sap_query_assistant import SAPQueryAssistant

assistant = SAPQueryAssistant()
result = assistant.process_query("Show me the top 5 selling products in the last 3 months")
print(result)
```

## API Usage

Send a POST request to `/query` endpoint:

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "Show me the top 5 selling products in the last 3 months",
           "execute_query": true
         }'
```

## Output Format

```json
{
  "sqlQuery": "SELECT TOP 5 T0.ItemCode, T1.ItemName, SUM(T0.Quantity) AS TotalSold FROM SBODEMOUS.INV1 T0 INNER JOIN SBODEMOUS.OITM T1 ON T0.ItemCode = T1.ItemCode INNER JOIN SBODEMOUS.OINV T2 ON T0.DocEntry = T2.DocEntry WHERE T2.DocDate >= ADD_MONTHS(CURRENT_DATE, -3) GROUP BY T0.ItemCode, T1.ItemName ORDER BY TotalSold DESC",
  "visualizationType": "bar_chart",
  "summary": "This chart shows the top 5 best-selling products over the past 3 months, ranked by total quantity sold.",
  "results": [
    {
      "ItemCode": "A001",
      "ItemName": "Product A",
      "TotalSold": 150
    },
    {
      "ItemCode": "B002",
      "ItemName": "Product B",
      "TotalSold": 120
    }
  ],
  "error": null
}
```

## Supported Query Types

- Sales analysis
- Inventory management
- Financial reporting
- Customer analytics
- Purchase order tracking
- Business partner information

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
