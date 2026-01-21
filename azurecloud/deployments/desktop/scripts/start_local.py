#!/usr/bin/env python3
"""
Desktop RAG Platform - Local Startup Script.

Starts all local services:
- Ollama (LLM)
- ChromaDB (Vector DB)
- FastAPI (RAG API)

Usage:
    python -m scripts.start_local
    python -m scripts.start_local --mode hybrid
    python -m scripts.start_local --gpu
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LocalServices:
    """Manager for local RAG services."""

    def __init__(self, mode: str = "local", use_gpu: bool = False):
        self.mode = mode
        self.use_gpu = use_gpu
        self.processes: list[subprocess.Popen] = []
        self.ollama_url = "http://localhost:11434"
        self.chromadb_url = "http://localhost:8001"
        self.api_url = "http://localhost:8000"

    async def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5)
                return response.status_code == 200
        except Exception:
            return False

    async def check_chromadb(self) -> bool:
        """Check if ChromaDB is running."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.chromadb_url}/api/v1/heartbeat", timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False

    async def check_api(self) -> bool:
        """Check if RAG API is running."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/health", timeout=5)
                return response.status_code == 200
        except Exception:
            return False

    async def wait_for_service(
        self, name: str, check_fn, timeout: int = 120
    ) -> bool:
        """Wait for a service to become available."""
        logger.info(f"Waiting for {name}...")
        start = time.time()

        while time.time() - start < timeout:
            if await check_fn():
                logger.info(f"{name} is ready!")
                return True
            await asyncio.sleep(2)

        logger.error(f"{name} failed to start within {timeout}s")
        return False

    async def pull_ollama_model(self, model: str):
        """Pull an Ollama model if not present."""
        logger.info(f"Checking/pulling Ollama model: {model}")
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                # Check if model exists
                response = await client.get(f"{self.ollama_url}/api/tags")
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]

                if model in model_names or f"{model}:latest" in model_names:
                    logger.info(f"Model {model} already available")
                    return

                # Pull model
                logger.info(f"Pulling model {model}... (this may take a while)")
                async with client.stream(
                    "POST",
                    f"{self.ollama_url}/api/pull",
                    json={"name": model}
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "status" in data:
                                print(f"  {data['status']}", end="\r")

                logger.info(f"Model {model} pulled successfully")

        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")

    def start_docker_compose(self):
        """Start services using Docker Compose."""
        docker_dir = Path(__file__).parent.parent / "docker"

        # Determine profile based on mode
        profiles = []
        if self.mode in ["local", "hybrid"]:
            profiles.append("local" if self.use_gpu else "cpu")
        if self.mode == "hybrid":
            profiles.append("hybrid")

        env = os.environ.copy()
        env["RAG_DEPLOYMENT_MODE"] = self.mode

        cmd = ["docker", "compose", "-f", str(docker_dir / "docker-compose.yml")]
        for profile in profiles:
            cmd.extend(["--profile", profile])
        cmd.extend(["up", "-d"])

        logger.info(f"Starting Docker services: {' '.join(cmd)}")
        subprocess.run(cmd, env=env, check=True)

    def start_ollama_native(self):
        """Start Ollama natively (not in Docker)."""
        logger.info("Starting Ollama...")

        # Check if ollama is installed
        if subprocess.run(["which", "ollama"], capture_output=True).returncode != 0:
            logger.error("Ollama not found. Install from https://ollama.ai")
            sys.exit(1)

        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(process)
        return process

    def start_api(self):
        """Start the FastAPI application."""
        logger.info("Starting RAG API...")

        env = os.environ.copy()
        env["RAG_DEPLOYMENT_MODE"] = self.mode

        process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "src.api.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            env=env,
            cwd=Path(__file__).parent.parent
        )
        self.processes.append(process)
        return process

    async def start_all(self, use_docker: bool = True):
        """Start all services."""
        logger.info(f"Starting RAG Platform in {self.mode.upper()} mode")
        logger.info(f"GPU: {'enabled' if self.use_gpu else 'disabled'}")

        if use_docker:
            self.start_docker_compose()
        else:
            # Native start
            if self.mode in ["local", "hybrid"]:
                self.start_ollama_native()

        # Wait for Ollama
        if self.mode in ["local", "hybrid"]:
            if not await self.wait_for_service("Ollama", self.check_ollama):
                return False

            # Pull required models
            await self.pull_ollama_model(os.getenv("OLLAMA_MODEL", "llama3.2"))
            await self.pull_ollama_model(
                os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            )

        # Start API (if not using Docker)
        if not use_docker:
            self.start_api()

        # Wait for API
        if not await self.wait_for_service("RAG API", self.check_api):
            return False

        logger.info("=" * 60)
        logger.info("RAG Platform started successfully!")
        logger.info(f"Mode: {self.mode.upper()}")
        logger.info(f"API: {self.api_url}")
        logger.info(f"Docs: {self.api_url}/docs")
        if self.mode in ["local", "hybrid"]:
            logger.info(f"Ollama: {self.ollama_url}")
        logger.info("=" * 60)

        return True

    def stop_all(self):
        """Stop all services."""
        logger.info("Stopping services...")

        # Stop subprocess
        for process in self.processes:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

        # Stop Docker services
        docker_dir = Path(__file__).parent.parent / "docker"
        subprocess.run(
            ["docker", "compose", "-f", str(docker_dir / "docker-compose.yml"), "down"],
            capture_output=True
        )

        logger.info("Services stopped")


async def main():
    parser = argparse.ArgumentParser(description="Start Desktop RAG Platform")
    parser.add_argument(
        "--mode",
        choices=["local", "hybrid", "azure"],
        default="local",
        help="Deployment mode (default: local)"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Enable GPU support for Ollama"
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Run services natively instead of Docker"
    )

    args = parser.parse_args()

    services = LocalServices(mode=args.mode, use_gpu=args.gpu)

    # Handle shutdown
    def shutdown_handler(signum, frame):
        logger.info("Received shutdown signal")
        services.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start services
    success = await services.start_all(use_docker=not args.no_docker)

    if success:
        # Keep running
        logger.info("Press Ctrl+C to stop")
        while True:
            await asyncio.sleep(1)
    else:
        services.stop_all()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
