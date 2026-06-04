from typing import Iterable


def search_records(records: Iterable[dict], term: str, keys: list[str]) -> list[dict]:
    if not term:
        return list(records)

    normalized = term.casefold()
    results: list[dict] = []
    for record in records:
        for key in keys:
            value = record.get(key)
            if value is None:
                continue
            if normalized in str(value).casefold():
                results.append(record)
                break
    return results
