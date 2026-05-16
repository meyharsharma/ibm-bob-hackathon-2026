"""Command-line interface for The Time Machine."""

import argparse
import sys
from pathlib import Path

from .utils.config import Config
from .utils.logger import setup_logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="The Time Machine - 3D Git Repository Visualization"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest a git repository for visualization"
    )
    ingest_parser.add_argument(
        "repository",
        help="Path to local repository or remote URL"
    )
    ingest_parser.add_argument(
        "--name",
        help="Custom name for the repository (default: auto-detect)"
    )
    
    # Prepare demo command
    demo_parser = subparsers.add_parser(
        "prepare-demo",
        help="Pre-generate all narration for offline demo mode"
    )
    demo_parser.add_argument(
        "repository",
        help="Path to repository or repository name"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all ingested repositories"
    )
    
    # Server command
    server_parser = subparsers.add_parser(
        "serve",
        help="Start the web server"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=Config.FLASK_PORT,
        help=f"Port to run server on (default: {Config.FLASK_PORT})"
    )
    server_parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    
    args = parser.parse_args()
    
    # Setup logger
    logger = setup_logger(level=Config.LOG_LEVEL, log_file=Config.LOG_FILE)
    
    # Ensure directories exist
    Config.ensure_directories()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        if args.command == "ingest":
            from .ingestion import RepositoryIngester
            logger.info(f"Ingesting repository: {args.repository}")
            ingester = RepositoryIngester()
            result = ingester.ingest(args.repository, name=args.name)
            logger.info(f"Successfully ingested repository: {result['name']}")
            logger.info(f"Commits: {result['commit_count']}, Files: {result['file_count']}")
            
        elif args.command == "prepare-demo":
            from .narration import NarrationGenerator
            logger.info(f"Preparing demo for repository: {args.repository}")
            generator = NarrationGenerator()
            generator.prepare_demo(args.repository)
            logger.info("Demo preparation complete")
            
        elif args.command == "list":
            repos_dir = Config.REPOSITORIES_DIR
            if not repos_dir.exists():
                logger.info("No repositories found")
                return 0
            
            repos = [d.name for d in repos_dir.iterdir() if d.is_dir()]
            if repos:
                logger.info(f"Found {len(repos)} repositories:")
                for repo in repos:
                    logger.info(f"  - {repo}")
            else:
                logger.info("No repositories found")
                
        elif args.command == "serve":
            from .api import create_app
            logger.info(f"Starting server on port {args.port}")
            app = create_app()
            app.run(
                host="0.0.0.0",
                port=args.port,
                debug=args.debug or Config.FLASK_DEBUG
            )
            
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
