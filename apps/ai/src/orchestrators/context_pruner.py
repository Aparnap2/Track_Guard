from __future__ import annotations


def prune_tool_calls(messages: list[dict]) -> list[dict]:
    pruned: list[dict] = []
    tool_interactions: list[tuple[int, int]] = []
    i = 0
    while i < len(messages):
        if messages[i].get("role") == "assistant" and "tool_calls" in messages[i]:
            tool_start = i
            i += 1
            while i < len(messages) and messages[i].get("role") == "tool":
                i += 1
            tool_interactions.append((tool_start, i))
        else:
            i += 1

    if len(tool_interactions) <= 3:
        return messages

    skip_ranges: set[int] = set()
    for start, end in tool_interactions[:-3]:
        for j in range(start, end):
            skip_ranges.add(j)

    for i, msg in enumerate(messages):
        if i not in skip_ranges:
            pruned.append(msg)

    return pruned


def prune_oldest_messages(messages: list[dict], max_messages: int = 20) -> list[dict]:
    if len(messages) <= max_messages:
        return messages

    system_msg = None
    system_idx = -1
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            system_msg = msg
            system_idx = i
            break

    non_system = [m for i, m in enumerate(messages) if i != system_idx]

    last_user_idx = -1
    for i in range(len(non_system) - 1, -1, -1):
        if non_system[i].get("role") == "user":
            last_user_idx = i
            break

    last_user = non_system[last_user_idx] if last_user_idx >= 0 else None
    non_system = [m for i, m in enumerate(non_system) if i != last_user_idx]

    keep_count = max_messages
    if system_msg:
        keep_count -= 1
    if last_user:
        keep_count -= 1

    if keep_count <= 0:
        non_system = []
    elif len(non_system) > keep_count:
        non_system = non_system[-keep_count:]

    result: list[dict] = []
    if system_msg:
        result.append(system_msg)
    result.extend(non_system)
    if last_user:
        result.append(last_user)

    return result
