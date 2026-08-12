import pygame


def _capacity(target):
    try:
        return max(1, int(getattr(target, "item_count", 1)))
    except (TypeError, ValueError):
        return 1


def _clean_entry(entry):
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not name:
        return None
    return {
        "name": name,
        "base_name": entry.get("base_name") or name,
        "index": entry.get("index"),
    }


def load_attached_items(target, data):
    entries = []
    raw_entries = data.get("dragged_items")
    if isinstance(raw_entries, list):
        entries = [clean for raw in raw_entries if (clean := _clean_entry(raw))]
    elif data.get("dragged_item_name"):
        entries = [{
            "name": data.get("dragged_item_name"),
            "base_name": data.get("dragged_item_basename") or data.get("dragged_item_name"),
            "index": data.get("dragged_item_index"),
        }]
    target.dragged_items = entries[:_capacity(target)]
    target.dragged_icon_item_images = []
    sync_legacy_attachment(target)


def sync_legacy_attachment(target):
    entries = getattr(target, "dragged_items", [])
    current = entries[-1] if entries else None
    target.dragged_item_name = current.get("name") if current else None
    target.dragged_item_basename = current.get("base_name") if current else None
    target.dragged_item_index = current.get("index") if current else None
    images = getattr(target, "dragged_icon_item_images", [])
    target.dragged_icon_item_image = images[-1] if images else None


def add_attached_item(target, name, base_name, index=None):
    entries = getattr(target, "dragged_items", None)
    if entries is None:
        entries = []
        target.dragged_items = entries
    capacity = _capacity(target)
    new_entry = {
        "name": name,
        "base_name": base_name or name,
        "index": index,
    }
    if len(entries) >= capacity:
        if capacity == 1:
            entries[0] = new_entry
            sync_legacy_attachment(target)
            return True
        return False
    entries.append(new_entry)
    sync_legacy_attachment(target)
    return True


def remove_last_attached_item(target):
    entries = getattr(target, "dragged_items", [])
    if not entries:
        return False
    entries.pop()
    sync_legacy_attachment(target)
    return True


def serialize_attached_items(target):
    return [dict(entry) for entry in getattr(target, "dragged_items", [])]


def attached_item_names(target):
    return [
        entry.get("name")
        for entry in getattr(target, "dragged_items", [])
        if entry.get("name")
    ]


def refresh_attached_images(target, tracker, icon_size):
    images = []
    for entry in getattr(target, "dragged_items", []):
        finder = getattr(tracker, "find_item", None)
        item = (finder(
            entry["name"], entry["name"] == entry.get("base_name"))
            if callable(finder) else None)
        source_image = None
        if item:
            index = entry.get("index")
            if hasattr(item, "next_items") and isinstance(index, int) and index >= 0:
                try:
                    source_image = item.next_items[index]["Image"]
                except (IndexError, KeyError, TypeError):
                    source_image = None
            if source_image is None:
                source_image = getattr(item, "colored_image", None)
        if isinstance(source_image, pygame.Surface):
            images.append(pygame.transform.smoothscale(source_image, icon_size))
    target.dragged_icon_item_images = images
    sync_legacy_attachment(target)
    return images