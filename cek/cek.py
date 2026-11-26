import os
import sys
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor
from cek_error import cek_error, SKIP_DIRS

PY = Language(tspython.language())
parser = Parser(PY)

QUERY_KOMENTAR = Query(PY, "(comment) @komentar")
QUERY_FUNGSI = Query(PY, "(function_definition name: (identifier) @nama) @fn")

def cek_todo(path, tree):
    cursor = QueryCursor(QUERY_KOMENTAR)
    captures = cursor.captures(tree.root_node)
    for node in captures.get("komentar", []):
        teks = node.text.decode("utf-8", errors="replace").strip()
        if "TODO" in teks or "FIXME" in teks:
            baris = node.start_point[0] + 1
            print(f"{path}:{baris}: Komentar ditemukan -> {teks}")

def cek_fungsi_panjang(path, tree, batas=30):
    cursor = QueryCursor(QUERY_FUNGSI)
    for _, cap in cursor.matches(tree.root_node):
        fn_node = cap["fn"][0]
        nama = cap["nama"][0].text.decode("utf-8", errors="replace")
        baris_awal = fn_node.start_point[0] + 1
        baris_akhir = fn_node.end_point[0] + 1
        panjang = baris_akhir - baris_awal + 1
        if panjang > batas:
            print(f"{path}:{baris_awal}: Fungsi '{nama}' terlalu panjang ({panjang} baris > {batas})")

def pindai(target):
    total_file = 0
    for root_dir, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for nama in files:
            if not nama.endswith(".py"):
                continue
            path = os.path.join(root_dir, nama)
            total_file += 1
            with open(path, "rb") as f:
                tree = parser.parse(f.read())

            cek_error(path, tree)
            cek_todo(path, tree)
            cek_fungsi_panjang(path, tree)

    print(f"\nPemindaian selesai: {total_file} file Python diperiksa.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    pindai(target)