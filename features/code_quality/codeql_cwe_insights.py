from openai import AzureOpenAI
import os
import csv
from collections import Counter, defaultdict

def analyze_security_scan(scan_results):
    """Analyze security scan results and categorize issues by severity level."""
    summary = {
        "high": [],
        "medium": [],
        "low": [],
        "info": []
    }

    for result in scan_results:
        severity = result.get("severity", "info")
        if severity not in summary:
            severity = "info"
        summary[severity].append(result)
        
    return summary

def enhance_with_cwe(scan_results, client=None):
    enhanced_results = []
    for result in scan_results:
        cwe_id = result.get("cwe_id")
        cwe_info = CWE_INFO.get(cwe_id)
        if cwe_info:
            result["cwe_title"] = cwe_info["title"]
            result["cwe_description"] = cwe_info["description"]
            # Only generate remediation tip if client is provided
            if client is not None:
                result["remediation_tip"] = get_remediation_tip_llm(
                    client, cwe_id, cwe_info["title"], cwe_info["description"]
                )
            else:
                result["remediation_tip"] = "No LLM client provided."
        enhanced_results.append(result)
    return enhanced_results

def generate_security_scan_summary(scan_results: list, client=None) -> dict:
    """Generate a summary of security scan results with CWE insights."""
    categorized_results = analyze_security_scan(scan_results)
    # Pass the client argument to enhance_with_cwe
    high_severity_results = enhance_with_cwe(categorized_results["high"], client)

    summary = {
        "total_issues": sum(len(v) for v in categorized_results.values()),
        "high_severity": len(high_severity_results),
        "medium_severity": len(categorized_results["medium"]),
        "low_severity": len(categorized_results["low"]),
        "info_severity": len(categorized_results["info"]),
        "high_severity_details": high_severity_results
    }

    return summary

def load_cwe_titles(csv_path=None):
    if csv_path is None:
        # Automatically get the path relative to this script's location
        csv_path = os.path.join(os.path.dirname(__file__), "cwe_information.csv")
    cwe_titles = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cwe_id = row['CWE-ID']
            name = row['Name']
            description = row.get('Description', '')
            cwe_titles[f"CWE-{cwe_id}"] = name
    return cwe_titles

def load_cwe_info(csv_path=None):
    if csv_path is None:
        # Automatically get the path relative to this script's location
        csv_path = os.path.join(os.path.dirname(__file__), "cwe_information.csv")
    cwe_info = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cwe_id = row['CWE-ID']
            name = row['Name']
            description = row.get('Description', '')
            cwe_info[f"CWE-{cwe_id}"] = {
                "title": name,
                "description": description
            }
    return cwe_info

def get_remediation_tip_llm(client, cwe_id, title, description):
    prompt = (
        f"You are a security expert. "
        f"Given the following CWE information, provide a concise, actionable remediation tip for developers. "
        f"Respond with only the tip, no extra text.\n\n"
        f"CWE ID: {cwe_id}\n"
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"Remediation Tip:"
    )
    response = client.chat.completions.create(
        model="reportr",  # or your deployed model name
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

remediation_cache = {}

def get_remediation_tip_cached(client, cwe_id, title, description):
    if cwe_id in remediation_cache:
        return remediation_cache[cwe_id]
    tip = get_remediation_tip_llm(client, cwe_id, title, description)
    remediation_cache[cwe_id] = tip
    return tip

CWE_TITLES = load_cwe_titles()
CWE_INFO = load_cwe_info()

def generate_codeql_cwe_insights(scan_results: list, client=None) -> str:
    # Group by CWE
    cwe_counter = Counter()
    cwe_details = defaultdict(list)
    severity_score_map = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    total_score = 0

    for issue in scan_results:
        cwe_id = issue.get("cwe_id", "Unknown")
        cwe_counter[cwe_id] += 1
        cwe_details[cwe_id].append(issue)
        severity = issue.get("severity", "info").lower()
        total_score += severity_score_map.get(severity, 1)

    # Top 5 CWEs
    top_cwes = cwe_counter.most_common(5)

    # Risk Score Calculation
    max_score = len(scan_results) * max(severity_score_map.values()) if scan_results else 1
    risk_percent = int((total_score / max_score) * 100)
    if risk_percent >= 80:
        risk_level = "🔥 High"
    elif risk_percent >= 50:
        risk_level = "🟠 Medium"
    else:
        risk_level = "🟢 Low"

    # Executive Summary
    exec_summary = (
        f"Executive Summary:\n"
        f"- Total findings: {len(scan_results)}\n"
        f"- Unique CWEs: {len(cwe_counter)}\n"
        f"- Top CWE: {top_cwes[0][0]} ({top_cwes[0][1]} findings)\n"
        f"- Risk Score: {risk_level} ({risk_percent}%)"
    ) if top_cwes else "No CWEs found."

    # Build output
    output = []
    output.append("🧠 CodeQL CWE Insights\n" + "="*28)
    output.append(exec_summary)
    output.append("\nTop 5 Most Common CWEs:")
    for cwe_id, count in top_cwes:
        cwe_info = CWE_INFO.get(cwe_id, {})
        title = cwe_info.get("title", cwe_id)
        description = cwe_info.get("description", "")
        # Optionally generate remediation tip with LLM if client is provided
        remediation = ""
        if client:
            remediation = get_remediation_tip_cached(client, cwe_id, title, description)
        output.append(
            f"{cwe_id} ({title}) - {count} finding(s)\n"
            f"   Description: {description}\n"
            f"   Remediation: {remediation if remediation else 'See CWE documentation.'}\n"
            f"   🔗 https://cwe.mitre.org/data/definitions/{cwe_id.split('-')[-1]}.html"
        )
    output.append(f"\nRisk Score: {risk_level} ({risk_percent}%)")
    output.append("\nLegend: 🔴 High | 🟠 Medium | 🟡 Low | 🔵 Info")

    return "\n".join(output)

