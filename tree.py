import os
import json

def build_tree(path=".", include_dirs=None, include_exts=None, exclude_dirs=None, root_path=None):
    include_dirs = include_dirs or []
    include_exts = include_exts or []
    exclude_dirs = exclude_dirs or []
    root_path = root_path or path

    tree = {"name": os.path.basename(path) or ".", "type": "directory", "children": []}

    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return tree

    for name in items:
        full_path = os.path.join(path, name)
        is_dir = os.path.isdir(full_path)
        ext = os.path.splitext(name)[1].lower()
        relative_path = os.path.relpath(full_path, root_path)

        # 🚫 Hariç tutulan klasörleri tamamen atla
        if any(name == ex or relative_path.startswith(ex + os.sep) for ex in exclude_dirs):
            continue

        # ✅ Dahil edilmesi gereken klasörler
        in_included_dir = not include_dirs or any(
            relative_path.startswith(d) or os.path.basename(full_path) == d
            for d in include_dirs
        )

        if include_dirs and not in_included_dir:
            # klasör değilse, yine de izinli dizin altındaysa dahil edilebilir
            if not any(d in relative_path for d in include_dirs):
                continue

        # 🔍 Dosya uzantısı filtrelemesi
        if not is_dir and include_exts and ext not in include_exts:
            continue

        if is_dir:
            subtree = build_tree(full_path, include_dirs, include_exts, exclude_dirs, root_path)
            tree["children"].append(subtree)
        else:
            tree["children"].append({"name": name, "type": "file"})

    return tree


def print_tree(tree, prefix="", is_last=True):
    """Terminal çıktısı"""
    connector = "└── " if is_last else "├── "
    print(prefix + connector + tree["name"])
    prefix += "    " if is_last else "│   "
    children = tree.get("children", [])
    for i, child in enumerate(children):
        print_tree(child, prefix, i == len(children) - 1)


def tree_to_text(tree, prefix="", is_last=True):
    """Tree'yi metin olarak döndürür"""
    lines = []
    connector = "└── " if is_last else "├── "
    lines.append(prefix + connector + tree["name"])
    prefix += "    " if is_last else "│   "
    children = tree.get("children", [])
    for i, child in enumerate(children):
        lines.extend(tree_to_text(child, prefix, i == len(children) - 1))
    return lines


if __name__ == "__main__":
    # 🔧 Filtreler
    include_dirs = ["."]  # sadece bu klasörler
    include_exts = [".py"]            # sadece bu uzantılar
    exclude_dirs = ["__pycache__","enviroment"]  # bunları hariç tut

    # 🌳 Tree oluştur
    tree = build_tree(".", include_dirs=include_dirs, include_exts=include_exts, exclude_dirs=exclude_dirs)

    # 📄 Konsola yaz
    print_tree(tree)

    # 🧱 JSON çıktısı
    with open("tree_output.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=4)

    # 📜 TXT çıktısı
    txt_lines = tree_to_text(tree)
    with open("tree_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    print("\n✅ JSON kaydedildi: tree_output.json")
    print("✅ TXT  kaydedildi: tree_output.txt")
