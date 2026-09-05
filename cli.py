#!/usr/bin/env python3
"""Unified CLI for Spirometry Curve Analyzer.

Supports both legacy spirometry analysis commands (single, predicted, batch)
and enterprise agent commands (audit, chat, verify-audit, serve).
"""
import sys
import json
from spiro_analyze import main as legacy_main


def _audit_command(args):
    """Run an enterprise audit task via the agent system."""
    import argparse
    parser = argparse.ArgumentParser(prog="cli audit")
    parser.add_argument("--task-id", required=True, help="Task identifier")
    parsed, _ = parser.parse_known_args(args)

    from agents.supervisor import SystemSupervisor
    from agents.models import SystemTaskPayload, UrgencyLevel

    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id=parsed.task_id,
        target_identifier=f"AUDIT-{parsed.task_id}",
        primary_metric=10.0,
        secondary_metric=3.0,
        status_descriptor="NOMINAL",
    )
    dossier = supervisor.process_task(payload)
    print(json.dumps(dossier.to_dict(), indent=2, default=str))
    return 0


def _chat_command(args):
    """Run a supervisor chat query."""
    from agents.supervisor import SystemSupervisor

    query = " ".join(args) if args else "General inquiry"
    supervisor = SystemSupervisor(model_provider="mock")
    response = supervisor.query_supervisory_chat(query)
    print(json.dumps({"query": query, "response": response}, indent=2))
    return 0


def _verify_audit_command(args):
    """Verify the HMAC-SHA256 audit trail integrity."""
    from agents.base import AuditLogger

    verified = AuditLogger.verify_integrity()
    trail_len = len(AuditLogger.get_trail())
    print(json.dumps({
        "audit_integrity_verified": verified,
        "trail_entries": trail_len,
    }, indent=2))
    return 0 if verified else 1


def _serve_command(args):
    """Start the FastAPI REST API server."""
    import argparse
    parser = argparse.ArgumentParser(prog="cli serve")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parsed, _ = parser.parse_known_args(args)

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required for the serve command. Install with: pip install uvicorn", file=sys.stderr)
        return 1

    from agents.api import app
    uvicorn.run(app, host=parsed.host, port=parsed.port, reload=parsed.reload)
    return 0


def main(argv=None):
    """Main entry point dispatching to subcommands."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python cli.py <command> [options]", file=sys.stderr)
        print("\nSpirometry commands:", file=sys.stderr)
        print("  single       Interpret single spirometry result", file=sys.stderr)
        print("  predicted    Calculate predicted values", file=sys.stderr)
        print("  batch        Batch process CSV", file=sys.stderr)
        print("\nEnterprise commands:", file=sys.stderr)
        print("  audit        Run an enterprise audit task", file=sys.stderr)
        print("  chat         Query the supervisor chat", file=sys.stderr)
        print("  verify-audit Verify HMAC-SHA256 audit trail integrity", file=sys.stderr)
        print("  serve        Start the FastAPI REST API server", file=sys.stderr)
        return 1

    command = argv[0]

    # Enterprise agent commands
    if command == "audit":
        return _audit_command(argv[1:])
    if command == "chat":
        return _chat_command(argv[1:])
    if command == "verify-audit":
        return _verify_audit_command(argv[1:])
    if command == "serve":
        return _serve_command(argv[1:])

    # Legacy spirometry commands delegate to spiro_analyze.main()
    return legacy_main(argv)


if __name__ == "__main__":
    sys.exit(main())
