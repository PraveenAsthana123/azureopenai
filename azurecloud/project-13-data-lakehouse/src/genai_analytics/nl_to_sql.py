"""
Natural Language to SQL Analytics Engine
==========================================
Converts natural language queries to SQL using Azure OpenAI
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from azure.identity import DefaultAzureCredential
from azure.synapse.artifacts import ArtifactsClient
from openai import AzureOpenAI
import pyodbc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    SYNAPSE_WORKSPACE_NAME = os.getenv("SYNAPSE_WORKSPACE_NAME")
    SYNAPSE_SQL_ENDPOINT = os.getenv("SYNAPSE_SQL_ENDPOINT")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "gold_layer")
    GPT_MODEL = "gpt-4o"


# ==============================================================================
# Schema Management
# ==============================================================================

@dataclass
class TableSchema:
    """Represents a table schema for context."""
    name: str
    columns: List[Dict[str, str]]
    description: str
    sample_data: Optional[List[Dict]] = None
    relationships: Optional[List[str]] = None


class SchemaManager:
    """Manages database schema metadata for AI context."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._schema_cache: Dict[str, TableSchema] = {}

    def get_table_schemas(self, tables: List[str] = None) -> List[TableSchema]:
        """Retrieve schema information for specified tables."""
        if self._schema_cache:
            if tables:
                return [self._schema_cache[t] for t in tables if t in self._schema_cache]
            return list(self._schema_cache.values())

        schemas = []
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()

            # Get table list
            if tables:
                table_list = tables
            else:
                cursor.execute("""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_TYPE = 'BASE TABLE'
                """)
                table_list = [row[0] for row in cursor.fetchall()]

            for table_name in table_list:
                # Get columns
                cursor.execute(f"""
                    SELECT
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                """)

                columns = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "default": row[3]
                    }
                    for row in cursor.fetchall()
                ]

                # Get sample data (top 3 rows)
                try:
                    cursor.execute(f"SELECT TOP 3 * FROM {table_name}")
                    sample_data = [
                        dict(zip([col[0] for col in cursor.description], row))
                        for row in cursor.fetchall()
                    ]
                except Exception:
                    sample_data = None

                schema = TableSchema(
                    name=table_name,
                    columns=columns,
                    description=self._get_table_description(table_name),
                    sample_data=sample_data
                )

                schemas.append(schema)
                self._schema_cache[table_name] = schema

        return schemas

    def _get_table_description(self, table_name: str) -> str:
        """Get human-readable table description."""
        descriptions = {
            "customers": "Customer master data including demographics and segments",
            "orders": "Sales orders with customer, product, and transaction details",
            "products": "Product catalog with pricing and category information",
            "daily_sales": "Aggregated daily sales metrics by product and region",
            "customer_segments": "Customer segmentation with RFM scores and lifetime value",
            "revenue_summary": "Financial revenue aggregations by period and dimension"
        }
        return descriptions.get(table_name, f"Table containing {table_name} data")

    def format_schema_for_prompt(self, schemas: List[TableSchema]) -> str:
        """Format schemas for inclusion in AI prompt."""
        schema_text = "DATABASE SCHEMA:\n\n"

        for schema in schemas:
            schema_text += f"TABLE: {schema.name}\n"
            schema_text += f"Description: {schema.description}\n"
            schema_text += "Columns:\n"

            for col in schema.columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                schema_text += f"  - {col['name']} ({col['type']}) {nullable}\n"

            if schema.sample_data:
                schema_text += "Sample data:\n"
                for row in schema.sample_data[:2]:
                    schema_text += f"  {json.dumps(row, default=str)}\n"

            schema_text += "\n"

        return schema_text


# ==============================================================================
# Natural Language to SQL Engine
# ==============================================================================

class NLToSQLEngine:
    """Converts natural language queries to SQL using GPT-4o."""

    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=lambda: self.credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-06-01"
        )

        # Initialize schema manager
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={Config.SYNAPSE_SQL_ENDPOINT};"
            f"Database={Config.DATABASE_NAME};"
            f"Authentication=ActiveDirectoryDefault;"
        )
        self.schema_manager = SchemaManager(connection_string)

        # Conversation history for context
        self.conversation_history: List[Dict] = []

    def generate_sql(self, user_query: str, include_explanation: bool = True) -> Dict:
        """
        Generate SQL from natural language query.

        Args:
            user_query: Natural language question
            include_explanation: Whether to include query explanation

        Returns:
            {
                "sql": str,
                "explanation": str,
                "tables_used": List[str],
                "confidence": float
            }
        """
        # Get schema context
        schemas = self.schema_manager.get_table_schemas()
        schema_context = self.schema_manager.format_schema_for_prompt(schemas)

        # Build system prompt
        system_prompt = f"""You are an expert SQL analyst for Azure Synapse Analytics.
Your task is to convert natural language questions into valid T-SQL queries.

{schema_context}

RULES:
1. Generate ONLY valid T-SQL compatible with Azure Synapse Analytics
2. Use table aliases for readability
3. Always include appropriate WHERE clauses for performance
4. Use aggregate functions (SUM, COUNT, AVG) with GROUP BY when needed
5. Format dates using CONVERT or FORMAT functions
6. Limit results to 1000 rows unless user specifies otherwise
7. Handle NULL values appropriately
8. Use CTEs for complex queries

OUTPUT FORMAT:
Return a JSON object with:
- "sql": The generated SQL query
- "explanation": Brief explanation of what the query does
- "tables_used": List of tables referenced
- "confidence": Your confidence in the query (0.0-1.0)

If you cannot generate a valid query, return:
- "sql": null
- "error": Explanation of why the query cannot be generated
- "suggestions": List of alternative questions the user could ask
"""

        # Build messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]

        # Add relevant conversation history (last 4 turns)
        for turn in self.conversation_history[-8:]:
            messages.append(turn)

        # Add current query
        messages.append({"role": "user", "content": user_query})

        try:
            response = self.openai_client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=messages,
                max_tokens=1000,
                temperature=0.1,  # Low temperature for consistent SQL
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            self.conversation_history.append({
                "role": "assistant",
                "content": response.choices[0].message.content
            })

            return result

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                "sql": None,
                "error": str(e),
                "suggestions": ["Please try rephrasing your question"]
            }

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax without executing.

        Returns:
            (is_valid, error_message)
        """
        if not sql:
            return False, "No SQL provided"

        # Basic syntax checks
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
        sql_upper = sql.upper()

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Query contains prohibited keyword: {keyword}"

        # Check for SELECT statement
        if not sql_upper.strip().startswith("SELECT") and not sql_upper.strip().startswith("WITH"):
            return False, "Only SELECT queries are allowed"

        return True, None

    def execute_query(self, sql: str, max_rows: int = 1000) -> Dict:
        """
        Execute validated SQL query.

        Returns:
            {
                "success": bool,
                "data": List[Dict],
                "row_count": int,
                "columns": List[str],
                "error": Optional[str]
            }
        """
        # Validate first
        is_valid, error = self.validate_sql(sql)
        if not is_valid:
            return {"success": False, "error": error}

        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={Config.SYNAPSE_SQL_ENDPOINT};"
            f"Database={Config.DATABASE_NAME};"
            f"Authentication=ActiveDirectoryDefault;"
        )

        try:
            with pyodbc.connect(connection_string) as conn:
                cursor = conn.cursor()

                # Add TOP clause if not present
                if "TOP" not in sql.upper():
                    sql = sql.replace("SELECT", f"SELECT TOP {max_rows}", 1)

                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                data = [dict(zip(columns, row)) for row in rows]

                return {
                    "success": True,
                    "data": data,
                    "row_count": len(data),
                    "columns": columns
                }

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": str(e)}

    def generate_summary(self, query: str, results: Dict) -> str:
        """Generate natural language summary of query results."""
        if not results.get("success"):
            return f"Query failed: {results.get('error')}"

        data = results.get("data", [])
        row_count = results.get("row_count", 0)

        if row_count == 0:
            return "The query returned no results."

        # Build summary prompt
        prompt = f"""Based on the user's question and the query results, provide a brief natural language summary.

User Question: {query}
Results: {json.dumps(data[:10], default=str)}  # First 10 rows
Total Rows: {row_count}

Provide a 2-3 sentence summary highlighting key insights. Be specific with numbers."""

        try:
            response = self.openai_client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Retrieved {row_count} rows."

    def suggest_follow_ups(self, query: str, sql: str) -> List[str]:
        """Suggest follow-up questions based on the query."""
        prompt = f"""Based on this analytics question and SQL query, suggest 3 relevant follow-up questions.

Original Question: {query}
SQL: {sql}

Return a JSON array of 3 follow-up questions that would provide deeper insights."""

        try:
            response = self.openai_client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
        except Exception:
            return []


# ==============================================================================
# Analytics Session Manager
# ==============================================================================

class AnalyticsSession:
    """Manages a user's analytics session with conversation context."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.engine = NLToSQLEngine()
        self.query_history: List[Dict] = []

    def ask(self, question: str) -> Dict:
        """
        Process a natural language analytics question.

        Returns full response including SQL, results, and summary.
        """
        # Generate SQL
        sql_result = self.engine.generate_sql(question)

        if not sql_result.get("sql"):
            return {
                "success": False,
                "error": sql_result.get("error", "Could not generate SQL"),
                "suggestions": sql_result.get("suggestions", [])
            }

        sql = sql_result["sql"]

        # Validate SQL
        is_valid, validation_error = self.engine.validate_sql(sql)
        if not is_valid:
            return {
                "success": False,
                "error": validation_error,
                "sql": sql
            }

        # Execute query
        exec_result = self.engine.execute_query(sql)

        if not exec_result.get("success"):
            return {
                "success": False,
                "error": exec_result.get("error"),
                "sql": sql
            }

        # Generate summary
        summary = self.engine.generate_summary(question, exec_result)

        # Generate follow-up suggestions
        follow_ups = self.engine.suggest_follow_ups(question, sql)

        # Store in history
        result = {
            "success": True,
            "question": question,
            "sql": sql,
            "explanation": sql_result.get("explanation"),
            "data": exec_result.get("data"),
            "row_count": exec_result.get("row_count"),
            "columns": exec_result.get("columns"),
            "summary": summary,
            "follow_up_questions": follow_ups,
            "confidence": sql_result.get("confidence", 0.8)
        }

        self.query_history.append(result)

        return result

    def get_history(self) -> List[Dict]:
        """Get query history for the session."""
        return self.query_history

    def clear_context(self):
        """Clear conversation context for fresh start."""
        self.engine.conversation_history = []
        self.query_history = []


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example session
    session = AnalyticsSession(user_id="analyst@company.com")

    # Example queries
    queries = [
        "Show me top 10 customers by revenue in the last quarter",
        "What's the month-over-month growth rate for each product category?",
        "Which regions have the highest customer churn rate?",
        "Compare this year's sales to last year by month"
    ]

    for query in queries:
        print(f"\nQuestion: {query}")
        print("-" * 50)

        result = session.ask(query)

        if result["success"]:
            print(f"SQL: {result['sql']}")
            print(f"Summary: {result['summary']}")
            print(f"Rows: {result['row_count']}")
            print(f"Follow-ups: {result['follow_up_questions']}")
        else:
            print(f"Error: {result['error']}")
