
import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Any


def export_csv_bytes(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> bytes:
    """
    Export rows using (field_name, heading) column definitions.
    UTF-8 BOM improves compatibility with Microsoft Excel.
    """
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)

    writer.writerow([heading for _, heading in columns])

    for row in rows:
        values = []

        for key, _ in columns:
            value = row.get(key)

            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = format(value, "f")
            elif value is None:
                value = ""

            values.append(value)

        writer.writerow(values)

    return buffer.getvalue().encode("utf-8-sig")
