from typing import List, Union
from contextlib import contextmanager
import re


Error = RuntimeError

PREFIX = 'ϟ'

def _noop():
    pass


class Scope:
    BUBBLE = object()

    def on_define(self, payload):
        pass

    def on_assign(self, payload):
        pass

    def on_yield(self):
        pass

    def on_directive(self, name: str, value):
        pass

    def on_method(self, meth_def):
        pass

    def get_from_ctx(self, name):
        pass


class Bookmark:
    def __init__(self, buf: 'Buffer', idx: int):
        self.buffer = buf
        self.idx = idx

    def set(self, str_: str):
        self.buffer.output[self.idx] = str_

    def get(self):
        return self.buffer.output[self.idx]


class Buffer:
    def __init__(self) -> None:
        self.output: List[str] = []

    def make_bookmark(self):
        return Bookmark(self, len(self.output) - 1)


class Stream:
    def __init__(self, mod_obj, options: dict):
        self.mod_obj = mod_obj
        self.options = options
        self.indentation = 0
        self.current_col = 0
        self.current_line = 1
        self.current_pos = 0
        self.buffers: List[Buffer] = [Buffer()]
        self.last: str = ''
        self.tmp_index = {
            "itr": 0,  # iterator
            "idx": 0,  # index
            "upk": 0,  # unpack
            "_": 0,    # default
        }
        self.node_stack = []
        self.ns_stack: List[Scope] = []
        self.modules = {}
        self.is_top_level = True
        self.module_id: str = self.mod_obj.mod_id
        self.sol = True
        self._inlined = 0

    def get_embed(self, key: str):
        return self.mod_obj.get_embed(key)

    def emit_yield(self):
        if self.ns_stack:
            for ns in reversed(self.ns_stack):
                if ns.on_yield() is not Scope.BUBBLE:
                    break

    def emit_maybe_baselib_fun(self, fun: str):
        self.mod_obj.request_baselib_fun(fun, maybe=True)

    def emit_use_baselib_fun(self, fun: str, mangled: str):
        self.mod_obj.request_baselib_fun(fun, mangled)

    def emit_import(self, mod_id):
        self.mod_obj.request_import(mod_id)

    def emit_exports(self, exports):
        self.mod_obj.set_exports(exports)

    def emit_typing_module(self):
        self.mod_obj.is_typing = True

    def get_obj(self, imp_id):
        return self.mod_obj.get_obj(imp_id)

    def is_typing_module(self, imp_pth):
        return self.mod_obj.is_typing_module(imp_pth)

    def get_from_ctx(self, name):
        if self.ns_stack:
            for ns in reversed(self.ns_stack):
                ret = ns.get_from_ctx(name)
                if ret not in [None, Scope.BUBBLE]:
                    return ret

    def resolve_import(self, name: str, dot_count: int):
        abs_name = self.mod_obj.resolve_import(f'{"." * dot_count}{name}')
        return abs_name

    def compile(self, mod_ast, module_id=None):
        self.is_top_level = not module_id
        self.module_id = module_id
        mod_ast.print(self)

    def emit_assignment(self, payload):
        if self.ns_stack:
            for ns in reversed(self.ns_stack):
                if ns.on_assign(payload) is not Scope.BUBBLE:
                    break

    def emit_define(self, payload):
        if self.ns_stack:
            for ns in reversed(self.ns_stack):
                if ns.on_define(payload) is not Scope.BUBBLE:
                    break

    def emit_directive(self, name, value):
        if self.ns_stack:
            for ns in reversed(self.ns_stack):
                if ns.on_directive(name, value) is not Scope.BUBBLE:
                    break

    def emit_method(self, meth_def):
        cls_def = self.ns_stack[-1]
        cls_def.on_method(meth_def)



    def push_node(self, node):
        self.node_stack.append(node)

    def pop_node(self):
        self.node_stack.pop()

    def push_scope(self, scope: Scope):
        self.ns_stack.append(scope)

    def pop_scope(self):
        self.ns_stack.pop()

    def parent(self, n: int = 0):
        stack = self.node_stack
        stack_len = len(stack)
        parent_neg_idx = 2 + n
        if stack_len - parent_neg_idx < 0:
            return None
        return stack[-parent_neg_idx]

    def print_buffer_output(self, buf_out: List[str]):
        out = ''.join(buf_out)
        self.print_(out)

    def make_string(self, str_: str, quotes: bool = False) -> str:
        dq = 0
        sq = 0

        def replacer(m: re.Match):
            nonlocal dq, sq
            tmp_ = m.group(0)
            if tmp_ == "\\":
                return "\\\\"
            elif tmp_ == "\b":
                return "\\b"
            elif tmp_ == "\f":
                return "\\f"
            elif tmp_ == "\n":
                return "\\n"
            elif tmp_ == "	":
                return "\\t"
            elif tmp_ == "\r":
                return "\\r"
            elif tmp_ == "\u2028":
                return "\\u2028"
            elif tmp_ == "\u2029":
                return "\\u2029"
            elif tmp_ == '"':
                dq += 1
                return '"'
            elif tmp_ == "'":
                sq += 1
                return "'"
            elif tmp_ == "\0":
                return "\\0"
            return tmp_

        ret = re.sub(r'[\\b\f\n\r\t\x22\x27\u2028\u2029\0]', replacer, str_)

        if quotes:
            if dq > sq:
                return "'" + ret.replace('\'', "\\'") + "'"
            else:
                return '"' + ret.replace('"', '\\"') + '"'
        else:
            return ret

    def make_name(self, name: str) -> str:
        name = str(name)
        return name

    def make_indent(self):
        return " " * (self.options.get('indent_start', 0) + self.indentation)

    def print_(self, str_: str):
        str_ = str(str_)
        a = re.split(r'\r?\n', str_)
        n = len(a) - 1
        self.current_line += n
        if n == 0:
            self.current_col += len(a[n])
        else:
            self.current_col = len(a[n])

        self.current_pos += len(str_)
        if str_.strip():
            self.last = str_
        self.buffers[-1].output.append(str_)
        self.sol = False

    def print_bookmark(self, str_: str):
        self.print_(str_)
        return self.buffers[-1].make_bookmark()

    def print_line(self, v: str):
        if not self.sol:
            self.newline()
        self.indent()
        self.print_(v)
        self.newline()

    def space(self):
        self.print_(" ")

    def indent(self):
        if not self.sol or self._inlined:
            return
        self.print_(self.make_indent())

    def next_indent(self):
        return self.indentation + self.options.get('indent_level', 4)

    @contextmanager
    def inlined(self):
        self._inlined += 1
        yield
        self._inlined -= 1

    @contextmanager
    def indented(self, col: int = None):
        if col is None:
            col = self.next_indent()

        save_indentation = self.indentation
        self.indentation = col
        yield
        self.indentation = save_indentation

    def newline(self):
        if self._inlined:
            return
        self.print_('\n')
        self.sol = True

    def semicolon(self, *, space=False):
        if self.last != '{':
            self.print_(';')
            if space:
                self.space()

    def sequence(self, *items, sep=','):
        for i, it in enumerate(items):
            if i:
                self.print_(sep)
                self.space()
            it_print = getattr(it, 'print', None)
            if it_print is not None:
                it.print(self)
            else:
                self.print_(it)

    def spaced(self, *items):
        for i, it in enumerate(items):
            if i > 0:
                self.space()
            it_print = getattr(it, 'print', None)
            if it_print is not None:
                it.print(self)
            else:
                self.print_(it)

    def end_statement(self):
        if self.last not in ['\n', ';']:
            self.semicolon()
            self.newline()

    @contextmanager
    def in_braces(self, cond=True):
        if cond:
            self.print_("{")
        yield
        if cond:
            self.print_("}")

    @contextmanager
    def in_block(self, scope: Scope = None):
        self.print_("{")
        self.newline()
        if scope is not None:
            self.push_scope(scope)
        with self.indented():
            yield
        if scope is not None:
            self.pop_scope()
        self.indent()
        self.print_("}")

    @contextmanager
    def in_parens(self, cond=True):
        if cond:
            self.print_("(")
        yield
        if cond:
            self.print_(")")

    @contextmanager
    def in_square(self):
        self.print_("[")
        yield
        self.print_("]")

    @contextmanager
    def as_statement(self):
        self.indent()
        yield
        self.end_statement()

    @contextmanager
    def as_string(self, cond):
        if not cond:
            yield
            return
        self.startLocalBuffer()
        yield
        str_buf = self.buffers.pop()
        s = ''.join(str_buf.output)
        self.print_(self.make_string(s, quotes=True))

    def print_stmt(self, stmt):
        with self.as_statement():
            stmt_print = getattr(stmt, 'print', None)
            if stmt_print is not None:
                stmt_print(self)
            else:
                self.print_(stmt)

    def comma(self, space=True):
        self.print_(",")
        if space:
            self.space()

    def colon(self):
        self.print_(":")
        self.space()

    @contextmanager
    def start_local_buffer(self, print_header=None):
        self.buffers.append(Buffer())
        yield
        local_buffer = self.buffers.pop()
        if print_header:
            print_header(self)
        self.buffers[-1].output.extend(local_buffer.output)

    def startLocalBuffer(self):
        # helper method for abstracting scope creation a bit, allows us cleaner injection of temp vars
        self.buffers.append(Buffer())

    def endLocalBuffer(self):
        # flushes local buffer, declaring the requested localvars
        local_buffer = self.buffers.pop()
        self.buffers[-1].output.extend(local_buffer.output)

    def get(self):
        buffers = self.buffers
        if len(self.buffers) > 1:
            raise Error('Something went wrong, output generator didn\'t exit all of its scopes properly.')

        out = buffers[0].output
        buffers[0].output = []

        if self.options.get('private_scope', False):
            with self.in_parens():
                self.print_("function()")
                with self.in_block():
                    # strict mode is more verbose about errors, and less forgiving about them, similar to Python
                    self.print_('"use strict"')
                    self.end_statement()
                    self.print_buffer_output(out)
            self.print_("();")
            self.newline()
        else:
            self.print_buffer_output(out)
        ret = buffers[0].output[0]
        assert len(buffers) == 1
        buffers[0].output.clear()
        return ret

    # generates: '[name] = '
    def assign_vars(self, *names, spaced=True):
        space = self.space if spaced else _noop
        if len(names) == 1:
            name = names[0]
            if isinstance(name, str):
                self.print_(name)
            else:
                name.print(self)
        else:
            assert names
            with self.in_square():
                self.sequence(names)
        space()
        self.print_("=")
        space()

    # TEMP VAR MANIPULATION
    def newTemp(self, subtype="_", kind=''):
        # convenience method for generating unused temporary\ variable
        from pyjsaw.ast_print import Entity
        self.tmp_index[subtype] += 1
        tmp = f'{PREFIX}{subtype}{self.tmp_index[subtype]}'
        self.emit_assignment(Entity(tmp, kind))
        return tmp

    def prevTemp(self, subtype="_"):
        # returns most recently declared temporary variable
        return f'{PREFIX}{subtype}{self.tmp_index[subtype]}'


if __name__ == '__main__':
    def main():
        stream = Stream({})
        s = stream.make_string('\b\\g\tasd')
        print(s)
        print(ord(s[0]), ord('\b'))

    main()
