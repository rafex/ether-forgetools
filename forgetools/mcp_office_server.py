"""Domain MCP server for office documents, PDFs, and report artifacts."""
from __future__ import annotations

from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources
from forgetools.mcp_domain_server import build_domain_server

server = build_domain_server("forgetools-office", ("office",))
register_domain_resources(server, "office")
register_domain_prompts(server, "office")


@server.prompt()
def office_executive_report(topic: str, audience: str = "executive stakeholders") -> str:
    """Plan and generate an executive report with PDF/DOCX outputs."""
    return f"""\
# Executive Report Workflow

Topic: `{topic}`
Audience: `{audience}`

Use `mcp-office` to produce reviewable and publishable artifacts:

1. Draft the report in Markdown with an executive summary, findings, risks, and next actions.
2. Generate editable output with `office_docx_create`.
3. Generate immutable output with `office_pdf_create`.
4. If tabular data is provided, use `office_table_report` and attach it with `office_pdf_append_tables`.
5. Validate the final PDF with `office_pdf_metadata` and `office_pdf_text`.
6. Add a visible status stamp with `office_pdf_stamp` when the document is draft, confidential, or reviewed.
"""


@server.prompt()
def office_appendix_bundle(report_name: str, table_sources: str) -> str:
    """Create a PDF report bundle with tabular appendices."""
    return f"""\
# Office Appendix Bundle

Report: `{report_name}`
Tables: `{table_sources}`

Workflow:

1. Convert each CSV/XLSX source with `office_table_report`.
2. Generate or identify the base report PDF.
3. Append table PDFs to the base document with `office_pdf_append_tables`.
4. Extract metadata with `office_pdf_metadata`.
5. Extract text with `office_pdf_text` to verify searchability.
6. If needed, extract embedded images with `office_pdf_images` for audit.
"""


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
