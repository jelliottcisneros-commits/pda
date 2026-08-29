import re
from pathlib import Path


INSERT_RE = re.compile(
    r"INSERT INTO (?:public\.)?core_question \((?P<columns>.*?)\) VALUES \((?P<values>.*)\);"
)

QUESTION_COLUMNS = {
    "id",
    "number",
    "title",
    "sociocultural_location",
    "primary_power_perspective",
    "secondary_power_perspective",
    "secondary_demographic_type",
    "secondary_demographic_choice",
}


def parse_postgres_values(text):
    values = []
    index = 0

    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1

        if index < len(text) and text[index] == "'":
            index += 1
            chars = []
            while index < len(text):
                char = text[index]
                if char == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        chars.append("'")
                        index += 2
                    else:
                        index += 1
                        break
                else:
                    chars.append(char)
                    index += 1
            values.append("".join(chars))
        else:
            start = index
            while index < len(text) and text[index] != ",":
                index += 1
            token = text[start:index].strip()
            if token.upper() == "NULL":
                values.append(None)
            elif token:
                values.append(int(token))
            else:
                values.append("")

        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == ",":
            index += 1

    return values


def parse_question_dump(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = INSERT_RE.match(line)
        if not match:
            continue

        columns = [column.strip() for column in match.group("columns").split(",")]
        unexpected_columns = set(columns) - QUESTION_COLUMNS
        if unexpected_columns:
            raise ValueError("Unexpected core_question columns: %s" % sorted(unexpected_columns))

        values = parse_postgres_values(match.group("values"))
        if len(columns) != len(values):
            raise ValueError("Column/value mismatch while parsing %s" % path)
        rows.append(dict(zip(columns, values)))

    return rows
