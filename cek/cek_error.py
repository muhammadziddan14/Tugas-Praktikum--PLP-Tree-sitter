import os
import sys
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY = Language(tspython.language())
parser = Parser(PY)

SKIP_DIRS = {"venv", ".venv", ".git", "node_modules", "__pycache__"}

def node_error_pertama(node):
    if node.is_error or node.is_missing:
        return node
    for child in node.children:
        if child.has_error or child.is_missing:
            hit = node_error_pertama(child)
            if hit:
                return hit
    return None

def cek_error(path, tree):
    if tree.root_node.has_error:
        e = node_error_pertama(tree.root_node)
        baris = e.start_point[0] + 1 if e else "?"
        kolom = e.start_point[1] if e else "?"
        jenis = "MISSING" if (e and e.is_missing) else "ERROR"
        print(f"{path}:{baris}:{kolom}: {jenis} sintaks")
        return True
    return False

def pindai_folder(target):
    total_file = 0
    total_error = 0

    for root_dir, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for nama in files:
            if not nama.endswith(".py"):
                continue
            path = os.path.join(root_dir, nama)
            total_file += 1
            with open(path, "rb") as f:
                tree = parser.parse(f.read())
            if cek_error(path, tree):
                total_error += 1

    print(f"\nSelesai: {total_file} file dipindai, {total_error} file memiliki syntax error.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    pindai_folder(target)