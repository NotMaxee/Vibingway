

def create_table_representation(rows: list[dict]) -> str:
    """Generate a tabular representation from a set of rows."""
    headers: list[str] = list(rows[0].keys())

    # Calculate widths
    widths: list[int] = [len(str(header)) for header in headers]
    for row in rows:
        for i in range(len(widths)):
            widths[i] = max(widths[i], len(str(row[i])))
    
    separator = "+" + "+".join((" " + "-" * w + " ") for w in widths) + "+"

    # Generate lines
    def line(widths, row):
        columns = [str(column) for column in row]
        formatted = " | ".join(f"{v:{widths[i]}}" for i, v in enumerate(columns))
        return f"| {formatted} |"

    lines: list[str] = []
    lines.append(line(widths, headers))
    lines.append(separator)
    for row in rows:
        lines.append(line(widths, row))
    
    return "\n".join(lines)
    
