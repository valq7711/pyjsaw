from typing import Dict
from pathlib import Path
import ast
from ast import AST
from pyjsaw.stream import Stream
import pyjsaw.ast_print as ast_print
from pyjsaw.ast_print import PREFIX, Import, alias


class NodeTransformer:

    def visit(self, node):
        cls_name = node.__class__.__name__
        visitor = getattr(self, f'visit_{cls_name}', None)
        if visitor is not None:
            return visitor(node)
        factory = getattr(ast_print, cls_name, None)
        if factory is None or not issubclass(factory, ast_print.RSNode):
            raise NotImplementedError(cls_name)
        new_node: ast_print.RSNode = factory(node)
        if new_node.generic_attrs:
            self.generic_visit(node, new_node)
        replaced = new_node.created()
        if replaced is not None:
            new_node = replaced
        return new_node

    def generic_visit(self, node: ast.AST, dst_node: ast_print.RSNode):

        for field, dst_field in dst_node.__node_attrs_map__.items():
            if field not in node._fields:
                raise AttributeError(field)
            old_value = getattr(node, field, None)
            new_value = old_value
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif isinstance(value, list):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                new_value = new_values
            elif isinstance(old_value, AST):
                new_value = self.visit(old_value)

            setattr(dst_node, dst_field, new_value)
        return dst_node

    def visit_Store(self, node: AST):
        return node

    def visit_Load(self, node: AST):
        return node

    def visit_Del(self, node: AST):
        return node


class Module:
    ast: ast_print.Module

    def __init__(self, fp: Path, mod_id: str = None, top_level: 'Module' = None, *, embed_ctx: dict = None):
        self.fp = fp
        self.dir = self.fp.parent
        self.mod_id = mod_id
        self.output = None
        self.all_modules: Dict[str, Module] = {}
        self.deps = {}
        self._top_level = top_level
        self.import_stack = []
        self.exports = {}
        self.subs = {}
        self.from_baselib_import = {}
        self.baselib_imports: Dict[str, bool] = {}
        self.embed_ctx = embed_ctx or {}

        self._baselib_mod = None
        if not top_level:
            self._baselib_mod = self._import_baselib()

    def _import_baselib(self):
        baselib = Module(Path(__file__).parent / 'baselib.py', 'baselib', self)
        baselib.compile()
        return baselib

    @property
    def top_level(self):
        return self._top_level or self

    def get_embed(self, key: str):
        if key in self.embed_ctx:
            return self.embed_ctx[key]
        else:
            return self.top_level.embed_ctx[key]

    def set_exports(self, exp):
        self.exports = exp

    def print_baselib(self, output: Stream):

        # print def_modules
        def_modules = Module(Path(__file__).parent / 'def_modules.py')
        def_modules.compile(only_body=True)
        output.print_(
            def_modules.output.replace('{PREFIX}', PREFIX).replace('__def_modules__', f'{PREFIX}_def_modules')
        )
        output.newline()
        with output.as_statement():
            output.spaced(f'var {PREFIX}_modules', '=', f'{PREFIX}_def_modules()')
        with output.as_statement():
            output.spaced(f'var {PREFIX}_defmod', '=', f'{PREFIX}_modules.{PREFIX}_defmod')

        # print baselib
        baselib = self._baselib_mod
        output.print_(baselib.output)
        output.newline()

        # print baselib's imports
        # baselib.foo -> RS_foo
        # trailing underscores will be removed, e.g.:
        #   baselib.in_ -> RS_in
        names = [
            alias(None, name=imp, asname=asname)
            for imp, asname in self.baselib_imports.items()
        ]
        baselib_imp = Import(None, from_module='baselib', names=names, no_emits=True)
        output.print_stmt(baselib_imp)

    def compile(self, only_body=False):
        src = self.fp.read_text()
        src_ast = ast.parse(src)
        self.ast = NodeTransformer().visit(src_ast)
        stream = Stream(self, {})
        stream.module_id = self.mod_id
        if only_body:
            for st in self.ast.body:
                st.print(stream)
            self.output = stream.get()
            return

        self.ast.print(stream)
        self.output = stream.get()
        if self.top_level is self:
            self.print_baselib(stream)
            stream.newline()
            for mod_id, mod_obj in self.all_modules.items():
                stream.print_stmt(f'{PREFIX}_defmod("{mod_id}")')

            # define subs
            for mod_id, mod_obj in self.all_modules.items():
                for sub in mod_obj.subs:
                    stream.print_stmt(
                        f'{PREFIX}_modules["{PREFIX}:{mod_id}"].export("{sub}", "{mod_id}.{sub}")'
                    )
            stream.sequence(*[m.output for m in self.all_modules.values()], sep='\n\n')
            stream.newline()
            stream.print_(self.output)
            self.output = stream.get()

    def wrapped(self):
        return '\n'.join(['(function(){', self.output, '})()'])

    def request_baselib_fun(self, fun: str, mangled: str = None, *, maybe=False):
        if maybe:
            if fun in self.top_level._baselib_mod.exports:
                if not mangled:
                    mangled = fun
            else:
                return
        self.from_baselib_import[fun] = mangled
        self.top_level.baselib_imports[fun] = mangled

    def request_import(self, mod_id: str):
        self.top_level._request_import(mod_id)
        self.deps[mod_id] = True

    def _request_import(self, mod_id: str):
        if mod_id in self.all_modules:
            return
        if mod_id in self.import_stack:
            raise RuntimeError(f'Recursive imports detected: {mod_id}, stack={self.import_stack}')
        mod_path = self.dir / mod_id.replace('.', '/')
        if mod_path.is_dir():
            mod_path = mod_path / '__init__.py'
        else:
            mod_path = mod_path.with_suffix('.py')

        pkg = None
        if '.' in mod_id:
            pkg = '.'.join(mod_id.split('.')[:-1])
            if pkg not in self.import_stack:
                self.request_import(pkg)
            if mod_id in self.all_modules:
                return

        if not mod_path.exists():
            # assuming it is `from module import indentifier` - check that
            if not pkg:
                raise RuntimeError(f'Not found: {mod_path}')
            pkg_mod = self.all_modules.get(pkg)
            if not pkg_mod:
                raise RuntimeError(f'Not found: {pkg_mod}')
            if mod_id.split('.')[-1] not in pkg_mod.exports:
                raise RuntimeError(f'Not found: {mod_id}')
            return

        self.import_stack.append(mod_id)
        mod = Module(mod_path, mod_id, self)
        mod.compile()
        self.all_modules[mod_id] = mod
        self.import_stack.pop()

        if pkg:
            pkg_mod = self.all_modules[pkg]
            pkg_mod.subs[mod_id.split('.')[-1]] = True


mod_fp = (Path(__file__).parent / 'for_ast.py')

mod = Module(mod_fp, embed_ctx={'templ': "'qq jamba'"})

mod.compile()

print(mod.wrapped())

#print(ast.dump(mast, indent=2))



