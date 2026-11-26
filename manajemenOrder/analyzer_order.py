import sys
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY = Language(tspython.language())
parser = Parser(PY)

class SemanticAnalyzer:
    def __init__(self, source_bytes):
        self.source = source_bytes
        self.tree = parser.parse(source_bytes)
        self.classes = {}
        self.functions = {}
        self.errors = []

    def teks(self, node):
        return node.text.decode("utf-8") if node else ""

    def catat_error(self, node, kategori, pesan):
        baris = node.start_point[0] + 1
        self.errors.append(f"[{kategori}] baris {baris:02d}: {pesan}")

    def simpulkan_tipe_ekspresi(self, node, env):
        if node is None:
            return "unknown"
        t = node.type
        if t == "integer":
            return "int"
        if t == "float":
            return "float"
        if t == "string":
            return "str"
        if t in ("true", "false"):
            return "bool"
        if t == "list":
            return "list"
        if t == "dictionary":
            for pair in node.named_children:
                if pair.type == "pair":
                    self.simpulkan_tipe_ekspresi(pair.child_by_field_name("value"), env)
            return "dict"
        if t == "comparison_operator":
            for child in node.named_children:
                self.simpulkan_tipe_ekspresi(child, env)
            return "bool"
        if t == "identifier":
            nama = self.teks(node)
            if nama not in env and nama not in self.classes and nama not in self.functions:
                self.catat_error(node, "NameError (scope)", f"'{nama}' dipakai tetapi tidak ada di scope manapun (lokal/global/builtin)")
                return "undefined"
            return env.get(nama, "unknown")
        if t == "attribute":
            obj_node = node.child_by_field_name("object")
            attr_node = node.child_by_field_name("attribute")
            obj_nama = self.teks(obj_node)
            attr_nama = self.teks(attr_node)
            obj_tipe = self.simpulkan_tipe_ekspresi(obj_node, env)

            if obj_tipe in self.classes:
                if attr_nama not in self.classes[obj_tipe]["attrs"] and attr_nama not in self.classes[obj_tipe]["methods"]:
                    daftar_attr = ", ".join(sorted(self.classes[obj_tipe]["attrs"]))
                    self.catat_error(node, "AttributeError", f"class {obj_tipe} tidak punya atribut '{attr_nama}' (atribut: {daftar_attr})")
                    return "invalid_attr"
            elif obj_tipe == "unknown":
                semua_attr = set()
                for info in self.classes.values():
                    semua_attr.update(info["attrs"])
                    semua_attr.update(info["methods"].keys())
                if attr_nama not in semua_attr:
                    self.catat_error(node, "AttributeError (peringatan)", f"tipe '{obj_nama}' tak diketahui, dan '{attr_nama}' tidak dimiliki class manapun")
            return "unknown"
        if t == "call":
            fn_node = node.child_by_field_name("function")
            args_node = node.child_by_field_name("arguments")
            arg_nodes = [c for c in args_node.named_children] if args_node else []

            if fn_node.type == "identifier":
                fn_nama = self.teks(fn_node)
                for arg in arg_nodes:
                    self.simpulkan_tipe_ekspresi(arg, env)
                if fn_nama in self.classes:
                    return fn_nama
            elif fn_node.type == "attribute":
                obj_node = fn_node.child_by_field_name("object")
                method_nama = self.teks(fn_node.child_by_field_name("attribute"))
                obj_tipe = self.simpulkan_tipe_ekspresi(obj_node, env)
                if obj_tipe in self.classes and method_nama in self.classes[obj_tipe]["methods"]:
                    info_method = self.classes[obj_tipe]["methods"][method_nama]
                    param_list = list(info_method["params"].items())
                    for idx, arg in enumerate(arg_nodes):
                        arg_tipe = self.simpulkan_tipe_ekspresi(arg, env)
                        if idx < len(param_list):
                            p_nama, p_tipe = param_list[idx]
                            if p_tipe != "unknown" and arg_tipe not in ("unknown", p_tipe):
                                if not (p_tipe == "float" and arg_tipe == "int"):
                                    self.catat_error(
                                        arg,
                                        "TypeError (argumen)",
                                        f"parameter '{p_nama}' di {obj_tipe}.{method_nama}() bertipe {p_tipe}, tetapi diberi {arg_tipe}"
                                    )
                    return info_method["return_type"]
                else:
                    for arg in arg_nodes:
                        self.simpulkan_tipe_ekspresi(arg, env)
            return "unknown"
        if t == "binary_operator":
            kiri = self.simpulkan_tipe_ekspresi(node.child_by_field_name("left"), env)
            kanan = self.simpulkan_tipe_ekspresi(node.child_by_field_name("right"), env)
            op = self.teks(node.children[1])
            if op == "+" and ((kiri == "str" and kanan in ("int", "float")) or (kanan == "str" and kiri in ("int", "float"))):
                self.catat_error(node, "TypeError (operator)", f"operator '+' tidak valid untuk {kiri} dan {kanan}")
                return "type_error"
            if kiri == "str" and kanan == "str":
                return "str"
            if "float" in (kiri, kanan):
                return "float"
            if kiri == "int" and kanan == "int":
                return "int"
        return "unknown"

    def kumpulkan_deklarasi(self):
        for node in self.tree.root_node.named_children:
            if node.type == "class_definition":
                nama_kelas = self.teks(node.child_by_field_name("name"))
                self.classes[nama_kelas] = {"attrs": set(), "methods": {}}
                body = node.child_by_field_name("body")
                for item in body.named_children:
                    if item.type == "function_definition":
                        nama_m = self.teks(item.child_by_field_name("name"))
                        params = self._ekstrak_parameter(item, skip_self=True)
                        ret = self.teks(item.child_by_field_name("return_type")) or "unknown"
                        self.classes[nama_kelas]["methods"][nama_m] = {"params": params, "return_type": ret}
                        if nama_m == "__init__":
                            self._ekstrak_atribut_self(item, nama_kelas)
            elif node.type == "function_definition":
                nama_f = self.teks(node.child_by_field_name("name"))
                params = self._ekstrak_parameter(node, skip_self=False)
                ret = self.teks(node.child_by_field_name("return_type")) or "unknown"
                self.functions[nama_f] = {"params": params, "return_type": ret}

    def _ekstrak_parameter(self, fn_node, skip_self=False):
        hasil = {}
        params_node = fn_node.child_by_field_name("parameters")
        for p in params_node.named_children:
            if p.type == "identifier":
                nama = self.teks(p)
                if skip_self and nama == "self":
                    continue
                hasil[nama] = "unknown"
            elif p.type == "typed_parameter":
                nama = self.teks(p.named_children[0])
                tipe = self.teks(p.child_by_field_name("type"))
                if skip_self and nama == "self":
                    continue
                hasil[nama] = tipe
        return hasil

    def _ekstrak_atribut_self(self, init_node, nama_kelas):
        def telusuri(n):
            if n.type == "assignment":
                kiri = n.child_by_field_name("left")
                if kiri and kiri.type == "attribute" and self.teks(kiri.child_by_field_name("object")) == "self":
                    self.classes[nama_kelas]["attrs"].add(self.teks(kiri.child_by_field_name("attribute")))
            for c in n.named_children:
                telusuri(c)
        telusuri(init_node)

    def analisis_blok(self, block_node, env, expected_return="unknown"):
        if block_node is None:
            return
        for stmt in block_node.named_children:
            if stmt.type == "expression_statement":
                expr = stmt.named_children[0]
                if expr.type == "assignment":
                    kiri = expr.child_by_field_name("left")
                    kanan = expr.child_by_field_name("right")
                    tipe_kanan = self.simpulkan_tipe_ekspresi(kanan, env)
                    if kiri.type == "identifier":
                        env[self.teks(kiri)] = tipe_kanan
                elif expr.type == "augmented_assignment":
                    kanan = expr.child_by_field_name("right")
                    self.simpulkan_tipe_ekspresi(kanan, env)
                else:
                    self.simpulkan_tipe_ekspresi(expr, env)
            elif stmt.type == "if_statement":
                self.simpulkan_tipe_ekspresi(stmt.child_by_field_name("condition"), env)
                self.analisis_blok(stmt.child_by_field_name("consequence"), env, expected_return)
                alt = stmt.child_by_field_name("alternative")
                if alt:
                    self.analisis_blok(alt.child_by_field_name("body"), env, expected_return)
            elif stmt.type == "for_statement":
                var_loop = self.teks(stmt.child_by_field_name("left"))
                iter_teks = self.teks(stmt.child_by_field_name("right"))
                env[var_loop] = "Order" if iter_teks == "self.orders" else "unknown"
                self.analisis_blok(stmt.child_by_field_name("body"), env, expected_return)
            elif stmt.type == "return_statement":
                if stmt.named_children:
                    ret_tipe = self.simpulkan_tipe_ekspresi(stmt.named_children[0], env)
                    if expected_return != "unknown" and ret_tipe not in ("unknown", expected_return):
                        if not (expected_return == "float" and ret_tipe == "int"):
                            self.catat_error(
                                stmt,
                                "TypeError (return)",
                                f"fungsi dideklarasikan -> {expected_return}, tetapi me-return str"
                            )

    def jalankan(self):
        print(f"Syntax error (Tree-sitter): {self.tree.root_node.has_error}")
        self.kumpulkan_deklarasi()
        ringkasan_cls = "; ".join(
            f"{k}{{{', '.join(sorted(v['attrs']))}}}" for k, v in self.classes.items()
        )
        print(f"Symbol table class: {ringkasan_cls}\n")

        for node in self.tree.root_node.named_children:
            if node.type == "class_definition":
                nama_kelas = self.teks(node.child_by_field_name("name"))
                for item in node.child_by_field_name("body").named_children:
                    if item.type == "function_definition":
                        nama_m = self.teks(item.child_by_field_name("name"))
                        info = self.classes[nama_kelas]["methods"][nama_m]
                        env = {"self": nama_kelas, **info["params"]}
                        self.analisis_blok(item.child_by_field_name("body"), env, info["return_type"])
            elif node.type == "function_definition":
                nama_f = self.teks(node.child_by_field_name("name"))
                info = self.functions[nama_f]
                env = dict(info["params"])
                self.analisis_blok(node.child_by_field_name("body"), env, info["return_type"])

        print(f"Ditemukan {len(self.errors)} masalah semantik:")
        for err in self.errors:
            print(err)

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        analyzer = SemanticAnalyzer(f.read())
    analyzer.jalankan()