"""
Load Testing for RAG System using Locust
Simulates realistic user traffic patterns.
"""

import random
import time

from locust import HttpUser, between, task


class RAGUser(HttpUser):
    """Simulated user for RAG system load testing."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between requests

    # Sample queries representing different use cases
    QUERIES = [
        # Policy questions
        "What is our company's vacation policy?",
        "How many sick days do employees get?",
        "What is the work from home policy?",
        "What are the travel expense guidelines?",
        "How do I request parental leave?",

        # Process questions
        "How do I submit an expense report?",
        "What is the process for requesting time off?",
        "How do I request a new software license?",
        "What is the onboarding process for new employees?",
        "How do I report a security incident?",

        # Technical questions
        "What are the password requirements?",
        "How do I access the VPN?",
        "What is the data retention policy?",
        "How do I set up two-factor authentication?",
        "What are the approved cloud services?",

        # Benefits questions
        "What medical insurance options are available?",
        "How does the 401k matching work?",
        "What is the employee stock purchase plan?",
        "Are there education reimbursement benefits?",
        "What wellness programs are offered?",
    ]

    FILTERS = [
        {"department": "HR"},
        {"department": "IT"},
        {"department": "Finance"},
        {"business_unit": "Corporate"},
        {"doc_type": "policy"},
        {"doc_type": "procedure"},
        {},  # No filter
    ]

    def on_start(self):
        """Initialize user session."""
        self.session_id = f"load-test-{time.time()}-{random.randint(1000, 9999)}"

    @task(10)
    def query_rag(self):
        """Main RAG query task - weighted heavily."""
        query = random.choice(self.QUERIES)
        filters = random.choice(self.FILTERS)

        with self.client.post(
            "/query",
            json={
                "query": query,
                "filters": filters,
                "session_id": self.session_id,
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "answer" in data and len(data["answer"]) > 0:
                    response.success()
                else:
                    response.failure("Empty or missing answer")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def query_with_conversation(self):
        """Query with conversation history."""
        queries = random.sample(self.QUERIES, 3)

        conversation = [
            {"role": "user", "content": queries[0]},
            {"role": "assistant", "content": "Previous response..."},
        ]

        with self.client.post(
            "/query",
            json={
                "query": queries[1],
                "conversation_history": conversation,
                "session_id": self.session_id,
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def health_check(self):
        """Health endpoint check."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def submit_feedback(self):
        """Submit feedback on a response."""
        with self.client.post(
            "/feedback",
            json={
                "query_id": f"query-{random.randint(1000, 9999)}",
                "rating": random.randint(1, 5),
                "feedback_type": random.choice(["helpful", "not_helpful", "inaccurate"]),
                "session_id": self.session_id,
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            else:
                response.failure(f"Feedback failed: {response.status_code}")


class PowerUser(HttpUser):
    """Simulated power user with higher query frequency."""

    wait_time = between(0.5, 2)
    weight = 1  # 10% of users

    COMPLEX_QUERIES = [
        "Compare the vacation policies for full-time and part-time employees",
        "What are all the steps required to submit and get approval for international travel?",
        "Summarize the key differences between our three health insurance plans",
        "What security requirements apply to storing customer data?",
        "Explain the complete process for hiring a new contractor",
    ]

    @task
    def complex_query(self):
        """Complex queries that require more processing."""
        query = random.choice(self.COMPLEX_QUERIES)

        with self.client.post(
            "/query",
            json={
                "query": query,
                "include_citations": True,
                "max_chunks": 10,
            },
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
