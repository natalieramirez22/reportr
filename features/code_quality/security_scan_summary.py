from typing import List, Dict

class SecurityScanResult:
    def __init__(self, description: str, severity: str, cwe_id: str):
        self.issue = description
        self.severity = severity
        self.cwe = cwe_id

    def __repr__(self):
        return f"{self.issue} (Severity: {self.severity}, CWE: {self.cwe})"


def summarize_security_scan(results: List[SecurityScanResult]) -> Dict[str, List[SecurityScanResult]]:
    summary = {
        "Critical": [],
        "High": [],
        "Medium": [],
        "Low": [],
        "Info": []
    }

    for result in results:
        # Normalize severity to title case (e.g., "high" -> "High")
        severity_key = result.severity.title()
        if severity_key in summary:
            summary[severity_key].append(result)

    return summary


def format_summary(summary: Dict[str, List[SecurityScanResult]]) -> str:
    severity_icons = {
        "Critical": "🛑",
        "High": "🔴",
        "Medium": "🟠",
        "Low": "🟡",
        "Info": "🔵"
    }
    output = []
    output.append("🔒 Security Scan Summary\n" + "="*28)
    for severity, issues in summary.items():
        icon = severity_icons.get(severity, "")
        header = f"{icon} {severity} Issues ({len(issues)})"
        if severity in ["Critical", "High"]:
            header += " [PRIORITY!]"
        output.append(header)
        if issues:
            for issue in issues:
                output.append(
                    f"  - {issue.issue}\n    Severity: {issue.severity.title()} | CWE: {issue.cwe}"
                )
        else:
            output.append("  - None found")
        output.append("")  # Blank line for spacing
    output.append("Legend: 🛑 Critical | 🔴 High | 🟠 Medium | 🟡 Low | 🔵 Info")
    return "\n".join(output)


def generate_security_scan_summary(results: List[SecurityScanResult]) -> str:
    summary = summarize_security_scan(results)
    return format_summary(summary)