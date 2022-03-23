from typing import TypeVar, Generic, List as tpList, Union, Any, Optional, Mapping
import sys
import ast
from ast import iter_fields, AST, Load, Store, Del
from pyjsaw.stream import Stream, Scope, PREFIX


T = TypeVar('T', bound=ast.AST)


def _make_precedence():
    opsets = [
        # lowest precedence
        ["||"],
        ["&&"],
        ["|"],
        ["^"],
        ["&"],
        ["==", "===", "!=", "!=="],
        ["<", ">", "<=", ">=", "in", "instanceof"],
        [">>", "<<", ">>>"],
        ["+", "-"],
        ["*", "/", "//", "%"],
        ["**"]
        # highest precedence
    ]
    ret = {}
    for i, opset in enumerate(opsets):
        for op in opset:
            ret[op] = i + 1
    return ret


PRECEDENCE = _make_precedence()
del _make_precedence


class Entity:

    def __init__(self, name: str, kind: str = None, value: 'RSNode[ast.AST]' = None):
        self.name = name
        self.kind = kind
        self.value = value


class NodeAttr:
    def __init__(self, src_name: str = None):
        self.src_name = src_name


class NodeMeta(type):
    def __init__(cls: 'RSNode', name, bases, dct):
        if name == 'RSNode':
            return
        cls.__node_attrs_map__ = cls._get_node_attrs_map(cls)


class RSNode(Generic[T], metaclass=NodeMeta):
    generic_attrs = True

    __node_attrs_map__ = {}

    @staticmethod
    def _get_node_attrs_map(it):
        map = {}
        for dst_name in dir(it):
            v = getattr(it, dst_name)
            if not isinstance(v, NodeAttr):
                continue
            map[v.src_name or dst_name] = dst_name
        return map

    def __init__(self, node: T, **kw):
        self._created_invoked = False
        self._pynode = node
        self._output: Stream = None
        self._init(**kw)

    def _init(self, **kw):
        if not kw:
            return
        # since we have kw it is not init from visitor
        # so set to None NodeAttrs
        node_attrs = {*self.__node_attrs_map__.values()}
        for k in dir(self):
            v = kw.pop(k, ...)
            if v is not ...:
                setattr(self, k, v)
            elif k in node_attrs and isinstance(getattr(self, k), NodeAttr):
                setattr(self, k, None)
        if kw:
            raise AttributeError(f'Unknown attrs: {kw}')

    def created(self) -> Optional['RSNode']:
        self._created_invoked = True

    def morph(self) -> Optional['RSNode']:
        pass

    @property
    def ctx_stack(self):
        return self._output.ctx_stack

    @property
    def current_scope(self):
        return self._output.ctx_stack.current_scope

    @property
    def requires_parens(self):
        return False

    def _print(self):
        raise NotImplementedError()

    def print(self, output: Stream, *, force_parens=False):
        if not self._created_invoked:
            replaced = self.created()
            if replaced is not None:
                replaced.print(output)
                return

        self._output = output
        output.push_node(self)
        replaced = self.morph()
        if replaced is not None:
            output.pop_node()
            self._output = None
            replaced.print(output)
            return

        generator = self._print
        if force_parens or self.requires_parens:
            with output.in_parens():
                generator()
        else:
            generator()
        output.pop_node()
        self._output = None

class stmt(RSNode[ast.stmt]):
    pass

class ModuleBodyWrapper(RSNode, Scope):
    body: tpList[stmt] = None
    exports: Mapping[str, Union['ClassDef', 'FunctionDef']] = None
    export_as_dict = False

    def on_directive(self, name, value):
        if name == 'EXPORTS_AS_DICT' and value:
            self.export_as_dict = True

    def on_assign(self, var: Entity):
        if var.name == '__all__':
            value = var.value
            self.exports[var.name] = ['__name__', *[name.value for name in value.elts]]
        elif not var.name.startswith((PREFIX, '_')):
            self.exports[var.name] = True
        return self.BUBBLE

    def _print(self):
        out = self._output
        self.exports = {'__name__': True}
        out.push_scope(self)
        for st in self.body:
            with out.as_statement():
                st.print(out)
                if isinstance(st, (FunctionDef, ClassDef)):  # TODO use emit as it maybe wrapped in if-else
                    self.exports[st.name] = st
        out.pop_scope()

class Exports(RSNode):
    body_wrapper: ModuleBodyWrapper = None

    def _print_as_dict(self):
        out = self._output
        exports = self.body_wrapper.exports
        out.emit_exports(exports)
        out.newline()
        out.print_line('// exports')
        out.print_stmt(f'var {PREFIX}_mod = {PREFIX}_modules["{PREFIX}:{out.module_id}"]')
        with out.as_statement():
            out.print_(f'Object.assign({PREFIX}_modules["{PREFIX}:{out.module_id}"].exports, {{')
            out.sequence(*self.body_wrapper.exports)
            out.print_('})')
        out.print_stmt(f'return {PREFIX}_mod')

    def _print(self):
        if self.body_wrapper.export_as_dict:
            self._print_as_dict()
            return

        out = self._output
        exports = self.body_wrapper.exports
        if '__all__' in exports:
            exports = exports['__all__']
        out.emit_exports(exports)

        seen = set()
        out.newline()
        out.print_line('// exports')
        out.print_stmt(f'var {PREFIX}_mod = {PREFIX}_modules["{PREFIX}:{out.module_id}"]')
        out.print_line(f'{PREFIX}_mod.export([')
        with out.indented():
            nl = False
            for name in exports:
                if name in seen:
                    continue
                if nl:
                    out.comma(space=False)
                    out.newline()
                seen.add(name)
                out.indent()
                out.print_(self._get_export_str(name))
                nl = True

        out.newline()
        out.print_line(']);')
        out.print_stmt(f'return {PREFIX}_mod')

    def _get_export_str(self, name):
        if name == '__name__':
            setter = 'null'
        else:
            setter = f'(v)=>{{if (typeof {name} !== "undefined") {name} = v;}})'

        return f'["{name}", ()=>{name}, {setter}]'


class JSModule(RSNode[ast.Module]):
    body: tpList[RSNode[ast.AST]] = None
    mod_id: str = None
    include_exports = True

    def _make_header(self):
        ret = [
            Assign(
                None,
                kind='var',
                targets=[Name(None, id='__name__')],
                value=Constant(None, value=self.mod_id),
                emit=False
            )
        ]
        return ret

    def _make_mod_fun_body(self):
        header = self._make_header()
        body_wrapper = ModuleBodyWrapper(None, body=self.body)
        body = [*header, body_wrapper]
        if self.include_exports:
            body.append(Exports(None, body_wrapper=body_wrapper))
        return body

    def _make_mod_fun(self):
        mod_fun = FunctionDef(
            None,
            name='',
            body=self._make_mod_fun_body()
        )
        return mod_fun

    def _print(self):
        out = self._output
        mod_id = self.mod_id
        body_fun = self._make_mod_fun()

        mod_obj_ref = Name(None, id=f'{PREFIX}_modules["{PREFIX}:{mod_id}"]')
        mod_assign = Assign(
            None,
            targets=[Attribute(None, value=mod_obj_ref, attr=f'{PREFIX}_body')],
            value=body_fun
        )
        mod_assign.print(out)


class MainModule(JSModule):

    include_exports = False

    def _print(self):
        out = self._output
        self.mod_id = '__main__'
        body_fun = self._make_mod_fun()
        run_main = Call(
            None,
            func=body_fun,
        )
        run_main.print(out)


class Module(RSNode[ast.Module]):
    body: tpList[RSNode[ast.AST]] = NodeAttr()

    def morph(self):
        out = self._output
        if out.module_id:
            mod = JSModule(None, body=self.body, mod_id=out.module_id)
        else:
            mod = MainModule(None, body=self.body)
        return mod


class alias(RSNode[ast.alias]):
    name: str = NodeAttr()
    asname: Optional[str] = NodeAttr()


class Import(RSNode[ast.Import]):
    names: tpList[alias] = NodeAttr()
    from_module: str = None
    level: int = 0
    is_fake = False
    no_emits = False

    def created(self):
        super().created()
        self.is_fake = bool(self.from_module and self.from_module.startswith('js_'))
        if not self.is_fake:
            self.names = [n for n in self.names if not n.name.startswith('js_')]

    def _print(self):
        if self.is_fake or not self.names:
            return

        out = self._output
        first = True
        for imp in self.names:
            var_name = imp.asname or imp.name.split('.', 1)[0]
            from_module = self.from_module
            if self.level:
                from_module = out.resolve_import(from_module or '', self.level)
            mod_key = from_module or imp.name
            if not self.no_emits:
                out.emit_import(mod_key)
            if not first:
                out.end_statement()
                out.indent()
            out.assign_vars(f'var {var_name}')
            out.print_(f'{PREFIX}_modules["{mod_key}"]')
            if from_module:
                out.print_(f'.{imp.name}')
                if not self.no_emits:
                    out.emit_import(f'{mod_key}.{imp.name}')
            if not self.no_emits:
                out.emit_assignment(Entity(var_name, 'var'))  # TODO
            first = False


class ImportFrom(RSNode[ast.ImportFrom]):
    module: str = NodeAttr()
    names: tpList[alias] = NodeAttr()
    level: int = NodeAttr()

    def created(self) -> Optional['RSNode']:
        super().created()
        ret = Import(self._pynode, names=self.names, from_module=self.module, level=self.level)
        ret.created()
        return ret


class Name(RSNode[ast.Name]):
    id: str = NodeAttr()
    ctx: Union[Load, Del, Store] = NodeAttr()

    def _init(self, **kw):
        super()._init(**kw)
        if self.ctx is None:
            self.ctx = Load()

    def _print(self):
        self._output.print_(self.id)

    @property
    def name(self):
        return self.id


class expr(RSNode[ast.expr]):
    pass


class Expr(RSNode[ast.Expr]):
    value: expr = NodeAttr()

    def _print(self):
        self.value.print(self._output)


class Constant(RSNode[ast.Name]):
    value: Any = NodeAttr()
    kind: str = NodeAttr()
    _constant_map = {
        'True': 'true',
        'False': 'false',
        'None': 'null',
    }

    def _print(self):
        out = self._output
        v = self.value
        if isinstance(v, str):
            v = out.make_string(v, True)
        else:
            v = self._constant_map.get(str(v), v)
        out.print_(v)


class AnnAssign(RSNode[ast.AnnAssign]):
    target: expr = NodeAttr()
    annotation: expr = NodeAttr()
    value: Optional[expr] = NodeAttr()
    simple: int = NodeAttr()

    def created(self):
        return Assign(
            self._pynode,
            targets=[self.target],
            value=self.value,
            annotation=self.annotation
        )


class _Directive(RSNode[None]):
    name: str = None
    value: expr = None

    def _print(self):
        out = self._output
        out.emit_directive(self.name, self.value)

class operator(RSNode[ast.AST]):
    value: str

class AugAssign(RSNode[ast.AugAssign]):
    target: expr = NodeAttr()
    op: operator = NodeAttr()
    value: expr = NodeAttr()

    def _print(self):
        out = self._output
        with out.as_statement():
            out.spaced(self.target, f'{self.op.value}=', self.value)


class Assign(RSNode[ast.Assign]):
    targets: tpList[expr] = NodeAttr()
    value: Union[Expr, Constant] = NodeAttr()
    emit = True
    kind = ''  # var, const, let
    annotation: expr = None

    def created(self):
        if isinstance(self.targets[0], Attribute) and self.targets[0].is_directive:
            value = self.value
            if isinstance(value, Tuple):
                value = value.elts
            elif isinstance(value, Constant):
                value = value.value
            return _Directive(None, name=self.targets[0].attr, value=value)

    def _emit_assign_targets(self, targets: list, value):
        out = self._output
        for t in targets:
            if isinstance(t, Name):
                out.emit_assignment(Entity(t.id, self.kind, value))
            elif isinstance(t, (Tuple, List)):
                # it is destructuring, so we cant pass value
                self._emit_assign_targets(t.elts, None)

    def _print(self):
        if self.value is None:
            return
        out = self._output
        if not self.emit and len(self.targets) > 1:
            raise SyntaxError('Statement `var foo = bar = baz = 1` produces global vars (bar, baz)')

        self._emit_assign_targets(self.targets, self.value)

        if self.kind:
            out.print_(self.kind)
            out.space()
        out.sequence(*self.targets, sep=' =')
        out.space()
        out.print_('=')
        out.space()
        self.value.print(out)


class unaryop(RSNode[ast.AST]):
    value: str = None

class Invert(unaryop):
    value = '~'

class Not(unaryop):
    value = '!'

class UAdd(unaryop):
    value = '+'

class USub(unaryop):
    value = '-'

class TypeOf(unaryop):
    value = 'typeof'

class UnaryOp(RSNode[ast.UnaryOp]):
    op: unaryop = NodeAttr()
    operand: expr = NodeAttr()

    def _print(self):
        out = self._output
        op = self.op.value
        out.print_(op)
        if len(op) > 1:
            # it is keyword
            out.space()
        self.operand.print(out)

    @property
    def requires_parens(self):
        out = self._output
        p = out.parent()
        # (new bar())()
        if isinstance(p, Call) and p.func is self:
            return True

        # (new bar())["prop"], (new bar()).prop
        if isinstance(p, (Attribute, Subscript)) and p.value is self:
            return True


class FuncOp(operator):
    value: 'Call'
    baselib_fun: str = None
    mangled: str = None

    def set_args(self, args):
        assert isinstance(self.value, Call)
        self.value.args = args

    def print(self, output: Stream, *args):
        self.set_args(args)
        self.value.print(output)
        if self.baselib_fun:
            output.emit_use_baselib_fun(self.baselib_fun, self.mangled)

class Add(operator):
    value = '+'

class BitAnd(operator):
    value = '&'

class BitOr(operator):
    value = '|'

class BitXor(operator):
    value = '^'

class Div(operator):
    value = '/'

class FloorDiv(operator):
    value = '/'

class LShift(operator):
    value = '<<'

class Mod(operator):
    value = '%'

class Mult(operator):
    value = '*'

class InstanceOf(operator):
    value = 'instanceof'

class Pow(FuncOp):

    def created(self):
        super().created()
        math_pow = Attribute(None, value=Name(None, id='Math'), attr='pow', ctx=Load())
        self.value = Call(None, func=math_pow)


'''
class MatMult(operator):
    value = None
'''

class keyword(RSNode[ast.AST]):
    arg: str = NodeAttr()
    value: expr = NodeAttr()

class BaseCall(RSNode[ast.Call]):
    pass


class Embed(RSNode[None]):
    ctx_key: str = None

    def _print(self):
        out = self._output
        v = out.get_embed(self.ctx_key)
        out.print_(v)

class Call(BaseCall):
    func: expr = NodeAttr()
    args: tpList[expr] = NodeAttr()
    keywords: tpList[keyword] = NodeAttr()
    func_name: str = None

    def created(self):
        super().created()
        if self.args is None:
            self.args = []
        if isinstance(self.func, Attribute) and self.func.is_directive:
            if self.func.attr == 'EMBED':
                return Embed(None, ctx_key=self.args[0].value)
        elif isinstance(self.func, Name):
            if self.func.id == 'isinstance':
                if isinstance(self.args[1], Name):
                    ret = BinOp(self._pynode, op=InstanceOf(None))
                    ret.left, ret.right = self.args
                    return ret
                elif isinstance(self.args[1], Tuple):
                    lst = self.args[1].elts
                    first = True
                    or_list = []
                    for exp in lst:
                        if first:
                            first = False
                            left = self.args[0]
                            if not isinstance(left, (Name, Constant)):
                                left = CachedExpr(left)
                        instof_exp = BinOp(
                            self._pynode,
                            left=left, op=InstanceOf(None), right=exp
                        )
                        or_list.append(instof_exp)
                    ret = BoolOp(None, op=Or(None), values=or_list)
                    return ret
            elif self.func.id in ['typeof', 'new']:
                ret = UnaryOp(self._pynode)
                ret.op = unaryop(None, value=self.func.id)
                ret.operand = self.args[0]
                return ret
            elif self.func.id == 'hasattr':
                ret = Compare(
                    self._pynode, ops=[JSIn(None)], left=self.args[1], comparators=[self.args[0]]
                )
                return ret
            elif self.func.id == 'VTempl':
                vdict = self.args[0]
                assert isinstance(vdict, Dict)
                return VDict(
                    self._pynode,
                    keys=vdict.keys,
                    values=vdict.values,
                )
            else:
                self.func_name = self.func.id

    def _print(self):
        if self.func_name == 'iif':
            self._print_iif()
            return
        out = self._output
        if self.func_name:
            out.emit_maybe_baselib_fun(self.func_name)
        self.func.print(out)
        with out.in_parens():
            out.sequence(*self.args)
            if self.keywords:
                if self.args:
                    out.comma()
                # (foo, bar, **kw)
                with out.in_braces():
                    for i, kw in enumerate(self.keywords):
                        if i:
                            out.comma()
                        if not kw.arg:  # **kw
                            out.print_('...')
                            kw.value.print(out)
                        else:
                            out.print_(kw.arg)
                            out.colon()
                            kw.value.print(out)

    def _print_iif(self):
        out = self._output
        cond = self.args[0]
        p = out.parent()
        with out.in_parens(isinstance(p, (BinOp, UnaryOp, Compare, Subscript))):
            cond.print(
                out, force_parens=not isinstance(cond, (Name, Call))
            )
            out.space()
            out.print_('?')
            out.space()
            self.args[1].print(out)
            out.space()
            out.colon()
            self.args[2].print(out)


class IfExp(RSNode[ast.IfExp]):
    test: expr = NodeAttr()
    body: expr = NodeAttr()
    orelse: expr = NodeAttr()

    def created(self):
        return Call(
            self._pynode,
            func=Name(None, id='iif'),
            args=[self.test, self.body, self.orelse]
        )


class RShift(operator):
    value = '>>'

class Sub(operator):
    value = '-'

class cmpop(operator):
    pass

class Eq(cmpop):
    value = '==='

class Gt(cmpop):
    value = '>'

class GtE(cmpop):
    value = '>='

class Is(cmpop):
    value = '==='

class IsNot(cmpop):
    value = '!=='

class Lt(cmpop):
    value = '<'

class LtE(cmpop):
    value = '<='

class NotEq(cmpop):
    value = '!=='

class JSIn(cmpop):
    value = 'in'

class In(FuncOp):
    baselib_fun = 'is_in'
    mangled = f'{PREFIX}_in'

    def created(self):
        super().created()
        self.value = Call(
            None,
            func=Name(None, id=self.mangled),
        )


class NotIn(In):
    value: UnaryOp

    def set_args(self, args):
        self.value.operand.args = args

    def created(self):
        super().created()
        call = self.value
        self.value = UnaryOp(
            None,
            op=Not(None),
            operand=call
        )

class boolop(operator):
    pass

class And(boolop):
    value = '&&'

class Or(boolop):
    value = '||'

class BoolOp(RSNode[ast.BoolOp]):
    op: boolop = NodeAttr()
    values: tpList[expr] = NodeAttr()

    @property
    def requires_parens(self):
        out = self._output
        p = out.parent()
        # (foo && bar)()
        if isinstance(p, Call) and p.func is self:
            return True

        # typeof (foo && bar)
        if isinstance(p, (UnaryOp, BinOp, Compare, Starred)):
            return True

        if isinstance(p, BoolOp):
            po = p.op.value
            so = self.op.value
            return po == '&&' and so == '||'

        # (foo && bar)["prop"], (foo && bar).prop
        if isinstance(p, (Attribute, Subscript)) and p.value is self:
            return True

        # this deals with precedence: 3 * (2 + 1)

    def _print(self):
        out = self._output
        out.sequence(*self.values, sep=f' {self.op.value}')


class BinOp(RSNode[ast.BinOp]):
    left: expr = NodeAttr()
    op: operator = NodeAttr()
    right: expr = NodeAttr()

    @property
    def requires_parens(self):
        out = self._output
        p = out.parent()
        # (foo && bar)()
        if isinstance(p, Call) and p.func is self:
            return True

        # typeof (foo && bar)
        if isinstance(p, (UnaryOp, Starred)):
            return True

        # (foo && bar)["prop"], (foo && bar).prop
        if isinstance(p, (Attribute, Subscript)) and p.value is self:
            return True

        # this deals with precedence: 3 * (2 + 1)
        if isinstance(p, BinOp) and not isinstance(self.op, FuncOp):
            po = p.op.value
            pp = PRECEDENCE[po]
            so = self.op.value
            sp = PRECEDENCE[so]
            if pp > sp or pp == sp and self is p.right and not (so == po and (so == "*" or so == "&&" or so == "||")):
                return True

    def _print(self):
        out = self._output
        if isinstance(self.op, FuncOp):
            self.op.print(out, self.left, self.right)
        else:
            out.spaced(self.left, self.op.value, self.right)


class CachedExpr:
    def __init__(self, expr: expr):
        self.expr = expr
        self.name = None

    def print(self, output: Stream):
        if self.name is not None:
            # TODO assert self.name in current scope
            output.print_(self.name)
            return

        out = output
        cache_var = self.name = out.newTemp()
        with out.in_parens():
            out.assign_vars(cache_var)
            if isinstance(self.expr, str):
                out.print_(self.expr)
            else:
                self.expr.print(out)


class Compare(RSNode[ast.Compare]):
    left: expr = NodeAttr()
    ops: tpList[operator] = NodeAttr()
    comparators: tpList[expr] = NodeAttr()

    @property
    def requires_parens(self):
        out = self._output
        p = out.parent()
        # not (foo > bar)
        if isinstance(p, UnaryOp):
            return True
        # foo + (a > b)
        if isinstance(p, (BinOp, Compare)):
            return True

    def _print(self):
        out = self._output
        exprs = iter(self.comparators)
        left = self.left
        right = None
        simple = len(self.ops) == 1
        for i, op in enumerate(self.ops):
            if i:
                out.space()
                out.print_('&&')
                out.space()
                left = right
            right = next(exprs)
            if not (simple or isinstance(right, (Name, Constant, CachedExpr))):
                right = CachedExpr(right)
            if isinstance(op, FuncOp):
                op.print(out, left, right)
            else:
                left.print(out)
                out.space()
                out.print_(op.value)
                out.space()
                right.print(out)


class arg(RSNode[ast.AST]):
    arg: str = NodeAttr()
    annotation: Optional[expr] = NodeAttr()
    default = None

    def _print(self):
        out = self._output
        out.print_(self.arg)
        default = self.default
        if default is not None:
            out.print_('=')
            if isinstance(default, RSNode):
                default.print(out)
            else:
                out.print_(default)


class arguments(RSNode[ast.AST]):
    if sys.version_info >= (3, 8):
        posonlyargs: tpList[arg] = NodeAttr()
    args: tpList[arg] = NodeAttr()
    vararg: Optional[arg] = NodeAttr()
    kwonlyargs: tpList[arg] = NodeAttr()
    kw_defaults: tpList[Optional[expr]] = NodeAttr()
    kwarg: Optional[arg] = NodeAttr()
    defaults: tpList[expr] = NodeAttr()

    def _print(self):
        out = self._output
        defs = self.defaults or []
        def_idx = len(defs) - len(self.args)
        pos_args = []
        for pos_arg in self.args:
            if def_idx >= 0:
                pos_arg.default = defs[def_idx]
            def_idx += 1
            pos_args.append(pos_arg)
        out.sequence(*pos_args)
        kw = self.kwonlyargs
        if kw:
            if self.vararg:
                raise SyntaxError('starargs + kwonlyargs is not supported')
            kw_args = []
            defs = self.kw_defaults
            def_idx = len(defs) - len(kw)
            for kwarg in kw:
                if def_idx >= 0:
                    kwarg.default = defs[def_idx]
                def_idx += 1
                kw_args.append(kwarg)
            out.comma()
            with out.in_braces():
                out.sequence(*kw_args)
            out.print_('={}')


class BaseFunctionDef(expr):
    args: arguments = NodeAttr()
    body: Union[expr, tpList[stmt]] = NodeAttr()
    is_generator = False

    @property
    def requires_parens(self):
        p = self._output.parent()
        return isinstance(p, Call) and p.func is self


class Lambda(BaseFunctionDef):
    _pynode: ast.Lambda

    def _print(self):
        out = self._output
        if self.is_generator:
            raise SyntaxError('Arrow function cannot be generator')
        with out.in_parens():
            if self.args:
                self.args.print(out)
        out.space()
        out.print_('=>')
        out.space()
        if isinstance(self.body, list):
            with out.in_braces():
                out.sequence(*self.body, sep=';')
        else:
            self.body.print(out)


class DecoratedExpr(expr):

    def __init__(self, func: expr, dec_list: tpList[expr]):
        super().__init__(None)
        self.func = func
        self.decorator_list = dec_list

    def _print(self):
        out = self._output
        tmp = Name(None)
        tmp.id = out.newTemp()
        arg = self.func
        with out.in_parens():
            for dec in reversed(self.decorator_list):
                out.assign_vars(tmp, spaced=False)
                dec_call = Call(None)
                dec_call.keywords = []
                dec_call.func = dec
                dec_call.args = [arg]
                dec_call.print(out)
                out.comma()
                arg = tmp
            tmp.print(out)


class FunctionDef(BaseFunctionDef, Scope):
    _pynode: ast.FunctionDef

    name: str = NodeAttr()
    decorator_list: tpList[expr] = NodeAttr()
    returns: Optional[expr] = NodeAttr()

    kind = 'function'
    _name: Name = None
    no_locals = False

    # Scope stuff
    nonlocals: dict

    vars: Mapping[str, bool]

    def on_assign(self, var: Entity):
        if self.no_locals and not var.name.startswith(PREFIX):
            return Scope.BUBBLE
        if var.name not in self.nonlocals and not var.kind:
            self.vars[var.name] = True

    def on_yield(self):
        if isinstance(self, JSDescriptor):
            raise SyntaxError(f'JS descriptor can`t be generator: {self.name}')
        self.is_generator = True

    def _print_vars(self, output: Stream):
        if not self.vars:
            return
        out = output
        with out.as_statement():
            out.print_('var')
            out.space()
            out.sequence(*self.vars)

    def created(self):
        if self.decorator_list:
            decorator_list = [*self.decorator_list]
            prop_dec = None
            static_dec = None
            classmeth_dec = None
            for dec in self.decorator_list:
                pop_dec = False
                if isinstance(dec, Name):
                    if dec.id == 'property':
                        prop_dec = dec
                        pop_dec = True
                    elif dec.id == 'staticmethod':
                        static_dec = dec
                        pop_dec = True
                    elif dec.id == 'classmethod':
                        classmeth_dec = dec
                        pop_dec = True
                elif isinstance(dec, Attribute) and dec.attr == 'setter':
                    assert isinstance(dec.value, Name)
                    prop_dec = Name(dec._pynode, id=dec.value.id)
                    pop_dec = True

                if pop_dec:
                    decorator_list.pop(decorator_list.index(dec))

            if prop_dec or static_dec or classmeth_dec:
                if static_dec and classmeth_dec:
                    raise SyntaxError('Special decorators conflict: staticmethod & classmethod')
                if prop_dec:
                    cls = Getter if prop_dec.id == 'property' else Setter
                else:
                    cls = JSMethod
                static = static_dec is not None
                ret = cls.from_func_def(
                    self,
                    decorator_list=decorator_list,
                    static=static,
                    classmeth=classmeth_dec is not None,
                    has_self_arg=not static
                )
                return ret

        super().created()
        if self.name == '__init__':
            self.name = 'constructor'
        self._name = Name(None, id=self.name, ctx=Load())
        self.nonlocals = {}
        cnt = 0
        for i, st in enumerate(self.body):
            if isinstance(st, (Global, Nonlocal)):
                self.nonlocals.update({k: True for k in st.names})
                if i > cnt:
                    raise SyntaxError('nonlocal/global must be first statements')
                cnt += 1

    def morph(self):
        out = self._output
        p = out.parent()
        if isinstance(p, ClassDef):
            js_meth = JSMethod.from_func_def(self)
            return js_meth

    def _print(self):
        out = self._output
        self._print_def()
        if self.decorator_list:
            dec_expr = DecoratedExpr(self._name, self.decorator_list)
            out.end_statement()
            out.indent()
            out.assign_vars(self.name)
            dec_expr.print(out)

    def _print_def(self):
        out = self._output
        if self.kind:
            out.print_(self.kind)
            out.space()
        gen_mark = out.print_bookmark('')
        if self.name:
            out.print_(self.name)
        with out.in_parens():
            if self.args:
                self.args.print(out)

        with out.in_block(scope=self):
            self.vars = {}
            with out.start_local_buffer(self._print_vars):
                # `(a,b,c, *args`) -> var args = [...arguments].slice(3)
                if self.args and self.args.vararg:
                    self.on_assign(Entity(self.args.vararg.arg, None))
                    with out.as_statement():
                        out.assign_vars(self.args.vararg.arg)
                        out.print_(f'[...arguments].slice({len(self.args.args)})')

                for st in self.body:
                    out.print_stmt(st)
        if self.is_generator:
            gen_mark.set('*')


class Yield(RSNode[ast.Yield]):
    value: Optional[expr] = NodeAttr()
    is_yield_from = False

    def _print(self):
        out = self._output
        star = '*' if self.is_yield_from else ''
        seq = [f"yield{star}"]
        if self.value:
            seq.append(self.value)
        with out.as_statement():
            out.spaced(*seq)
        out.emit_yield()


class YieldFrom(RSNode[ast.YieldFrom]):
    value: expr = NodeAttr()

    def created(self) -> Optional['RSNode']:
        return Yield(self._pynode, value=self.value, is_yield_from=True)


class expr_context(RSNode[ast.AST]):
    pass

class Tuple(RSNode[ast.Tuple]):
    elts: tpList[expr] = NodeAttr()
    ctx: Union[Load, Store] = NodeAttr()

    multilined = False

    def _print(self):
        out = self._output
        if not self.elts:
            out.print_('[]')
            return
        with out.in_square():
            if self.multilined:
                out.newline()
                with out.indented():
                    for i, expr in enumerate(self.elts):
                        if i:
                            out.comma()
                            out.newline()
                        out.indent()
                        expr.print(out)
                out.newline()
            else:
                out.sequence(*self.elts)

class List(Tuple):
    pass

class Set(Tuple):
    pass


class Dict(RSNode[ast.Dict]):
    keys: tpList[Optional[expr]] = NodeAttr()
    values: tpList[expr] = NodeAttr()

    def _print(self):
        out = self._output
        if not self.keys:
            out.print_('{}')
            return
        with out.in_block():
            for i, (k, v) in enumerate(zip(self.keys, self.values)):
                if i:
                    out.comma()
                    out.newline()
                out.indent()
                if not isinstance(k, Constant):
                    with out.in_square():
                        k.print(out)
                else:
                    k.print(out)
                out.colon()
                v.print(out)
            out.newline()

class Starred(RSNode[ast.Starred]):
    value: expr = NodeAttr()
    ctx: Union[Store, Load] = NodeAttr()

    def _print(self):
        out = self._output
        out.print_('...')
        self.value.print(out)


class Slice(RSNode[ast.Slice]):
    lower: Optional[expr] = NodeAttr()
    upper: Optional[expr] = NodeAttr()
    step: Optional[expr] = NodeAttr()

    def _print(self):
        out = self._output
        if self.step:
            raise SyntaxError('Stepped slice is not supported')
        out.print_('.slice')
        with out.in_parens():
            out.sequence(self.lower, self.upper)


class Attribute(RSNode[ast.Attribute]):
    value: expr = NodeAttr()
    attr: str = NodeAttr()
    ctx: expr_context = NodeAttr()
    is_directive = False

    def created(self):
        if isinstance(self.value, Name) and self.value.id == '__RSDirectives__':
            self.is_directive = True

    def _print(self):
        out = self._output
        self.value.print(out)
        out.print_('.')
        out.print_(self.attr)


class Subscript(RSNode[ast.Subscript]):
    value: expr = NodeAttr()
    slice: expr = NodeAttr()
    ctx: Union[Load, Store]

    def _print(self):
        out = self._output
        v = self.value
        neg_index = isinstance(self.slice, UnaryOp) and self.slice.op.value == '-'
        if neg_index and not isinstance(v, Name):
            v = CachedExpr(v)
        v.print(out)
        if isinstance(self.slice, Slice):
            self.slice.print(out)
        else:
            with out.in_square():
                if neg_index:
                    # [<self.value>.length - <self.slice.operand>]
                    idx_exp = BinOp(
                        None,
                        left=Attribute(None, value=v, attr='length'),
                        op=Sub(None),
                        right=self.slice.operand,
                    )
                    idx_exp.print(out)
                elif type(self.slice) is Tuple:
                    # allow to Array negative index by wrapping in tuple: arr[(-1,)] -> arr[-1]
                    assert len(self.slice.elts) == 1
                    self.slice.elts[0].print(out)
                else:
                    self.slice.print(out)


class If(RSNode[ast.If]):
    test: expr = NodeAttr()
    body: tpList[stmt] = NodeAttr()
    orelse: tpList[stmt] = NodeAttr()

    def _print_block(self, keyword, cond: expr, body: tpList[stmt]):
        out = self._output
        out.print_(keyword)
        if cond:
            with out.in_parens():
                cond.print(out)
        with out.in_block():
            for st in body:
                with out.as_statement():
                    st.print(out)

    def _print(self):
        out = self._output
        p = out.parent()
        kw = 'if'
        if isinstance(p, If) and p.elif_node is self:
            kw = 'else if'
        self._print_block(kw, self.test, self.body)
        if self.orelse:
            elif_node = self.elif_node
            if elif_node:
                elif_node.print(out)
            else:
                self._print_block('else', None, self.orelse)

    @property
    def elif_node(self):
        if len(self.orelse) == 1 and isinstance(self.orelse[0], If):
            return self.orelse[0]


class For(RSNode[ast.For]):
    target: expr = NodeAttr()
    iter: expr = NodeAttr()
    body: tpList[stmt] = NodeAttr()
    orelse: tpList[stmt] = NodeAttr()

    def _emit_assign_target(self, t: Union[Tuple, List, Name]):
        out = self._output
        targets = [t]
        for t in targets:
            if isinstance(t, Name):
                out.emit_assignment(Entity(t.id, ''))
            elif isinstance(t, (Tuple, List)):
                targets.extend(t.elts)

    def _print_iter(self, iter):
        out = self._output
        if (
            isinstance(iter, Tuple)
            or isinstance(iter, Call) and (
                isinstance(iter.func, Name) and iter.func.id == 'iterable'
                or isinstance(iter.func, Attribute) and isinstance(iter.func.value, Name)
                and iter.func.value.id == 'Object'
                and iter.func.attr in ['keys', 'values', 'entries', 'getOwnPropertyNames', 'getOwnPropertySymbols']
            )
        ):
            iter.print(out)
            return

        iterable = Call(
            None,
            func=Name(None, id=f'{PREFIX}_iterable'),
            args=[iter]
        )
        iterable.print(out)
        out.emit_use_baselib_fun('iterable', f'{PREFIX}_iterable')

    def _print(self):
        out = self._output
        iter = self.iter
        counter = None
        target = self.target
        op = 'of'
        if isinstance(iter, Call) and isinstance(iter.func, Name):
            # TODO check whether `enumerate/range` is overloaded by user functions
            if iter.func.id == 'range':
                self._print_range()
                return
            elif iter.func.id == 'enumerate':
                iter = iter.args[0]
                counter: Name
                if isinstance(target, Tuple):
                    assert len(target.elts) == 2
                    counter = target.elts[0]
                    target = target.elts[1]
                else:
                    raise SyntaxError('Enumerating with a single target is not supported')

                assert isinstance(counter, Name)
                tmp_counter = Name(None)
                tmp_counter.id = out.newTemp()

                tmp_counter_assign = Assign(None)
                tmp_counter_assign.targets = [tmp_counter]
                tmp_counter_assign.value = Constant(None)
                tmp_counter_assign.value.value = 0
                with out.as_statement():
                    tmp_counter_assign.print(out)

                counter_assign = Assign(None)
                counter_assign.targets = [counter]
                counter_assign.value = tmp_counter
            elif iter.func.id == 'dir':
                iter = iter.args[0]
                op = 'in'

        self._emit_assign_target(target)
        out.print_('for')
        with out.in_parens():
            target.print(out)
            out.space()
            out.print_(op)
            out.space()
            if op == 'of':
                self._print_iter(iter)
            else:
                iter.print(out)
        with out.in_block():
            if counter:
                with out.as_statement():
                    counter_assign.print(out)
                    # TODO use augassign
                    out.print_('++')
            for st in self.body:
                with out.as_statement():
                    st.print(out)

    def _print_range(self):
        out = self._output

        args = self.iter.args
        step = 1
        # end
        if len(args) == 1:
            start = Constant(None)
            start.value = 0
            end = args[0]
        # start, end, [step]
        elif len(args) >= 2:
            start = args[0]
            end = args[1]

        # start, end, step
        if len(args) == 3:
            step = args[2]

        if not isinstance(end, (Name, Constant)):
            tmp = out.newTemp()
            out.assign_vars(tmp)
            end.print(out)
            out.end_statement()
            out.indent()
            end = Name(None)
            end.id = tmp

        if not isinstance(step, (Name, Constant)):
            tmp = out.newTemp()
            out.assign_vars(tmp)
            step.print(out)
            out.end_statement()
            out.indent()
            step = Name(None)
            step.id = tmp

        cond = Compare(None)
        cond.left = self.target
        cond.ops = [Lt]
        cond.comparators = [end]

        out.print_('for')
        with out.in_parens():
            out.print_('var')
            out.space()
            out.assign_vars(self.target)
            start.print(out)
            out.semicolon(space=True)
            cond.print(out)
            out.semicolon(space=True)
            self.target.print(out)
            if step == 1:
                out.print_('++')
            else:
                out.print_(' += ')  # TODO - augassign
                step.print(out)
        with out.in_block():
            for st in self.body:
                with out.as_statement():
                    st.print(out)


class While(RSNode[ast.While]):
    test: expr = NodeAttr()
    body: tpList[stmt] = NodeAttr()
    orelse: tpList[stmt] = NodeAttr()

    def _print(self):
        out = self._output
        out.print_('while')
        with out.in_parens():
            self.test.print(out)
        with out.in_block():
            for st in self.body:
                with out.as_statement():
                    st.print(out)


class Break(RSNode[ast.Break]):
    def _print(self):
        out = self._output
        out.print_('break')

class Continue(RSNode[ast.Continue]):
    def _print(self):
        out = self._output
        out.print_('continue')


class _externals:
    names: tpList[str]

    def _print(self: Union[RSNode, '_externals']):
        tp = self.__class__.__name__.lower()
        out = self._output
        names = ', '.join(self.names)
        out.print_(f'// {tp}: {names}')


class Global(_externals, RSNode[ast.Global]):
    names: tpList[str] = NodeAttr()


class Nonlocal(_externals, RSNode[ast.Nonlocal]):
    names: tpList[str] = NodeAttr()


class Pass(RSNode[ast.Pass]):
    def _print(self):
        pass


class Return(RSNode[ast.Return]):
    value: Optional[expr] = NodeAttr()

    def _print(self):
        out = self._output
        out.print_('return')
        if self.value:
            out.space()
            self.value.print(out)


class FormattedValue(RSNode[ast.FormattedValue]):
    value: expr = NodeAttr()
    conversion: Optional[int] = NodeAttr()
    format_spec: Optional[expr] = NodeAttr()


class JoinedStr(RSNode[ast.JoinedStr]):
    values: tpList[expr] = NodeAttr()

    def _print(self):
        out = self._output
        # f'{"raw js goes here"}'
        if (
            len(self.values) == 1
            and isinstance(self.values[0], FormattedValue)
            and isinstance(self.values[0].value, Constant)
        ):
            out.print_(self.values[0].value.value)
            return

        out.print_('`')
        for v in self.values:
            if isinstance(v, Constant):
                if isinstance(v.value, str):
                    # TODO - do we need to escape '${' as '\${' ?
                    pass
                out.print_(v.value)
            else:
                v = v.value
                out.print_('${')
                v.print(out)
                out.print_('}')
        out.print_('`')


class JSMethod(FunctionDef):
    kind = ''  # no `function` before method name
    has_self_arg = True
    static = False
    classmeth = False

    def morph(self):
        pass

    @classmethod
    def from_func_def(cls, func_def: FunctionDef, **kw):
        attrs = {k: getattr(func_def, k) for k in FunctionDef.__node_attrs_map__.values()}
        attrs.update(kw)
        return cls(
            func_def._pynode,
            **attrs
        )

    def created(self):
        super().created()
        if self.has_self_arg:
            if not self.args.args:
                raise SyntaxError('At least one arg required (self)')
            self_arg = self.args.args.pop(0)
            self_name = Name(None, id=self_arg.arg)
            this_name = Name(None, id='this')
            self_assign = Assign(None, targets=[self_name], value=this_name)
            self.body.insert(0, self_assign)

    def _print(self):
        # In fact, in JS any static method is classmethod, as it gets this==class.
        # So in our case classmethod should have fake first arg (e.g. `cls` with auto assignment `cls = this`)
        # and it is not exposed at instance level to force user to call it
        # with class context as `self.__class__.some()`
        if self.static or self.classmeth:
            out = self._output
            out.print_('static')
            out.space()
        self._print_def()


class JSDescriptor(JSMethod):
    pass

class Getter(JSDescriptor):
    kind = 'get'

class Setter(JSDescriptor):
    kind = 'set'


class ClassDef(RSNode[ast.ClassDef], Scope):
    name: str = NodeAttr()
    bases: tpList[expr] = NodeAttr()
    keywords: tpList[keyword] = NodeAttr()
    body: tpList[stmt] = NodeAttr()
    decorator_list: tpList[expr] = NodeAttr()

    methods: tpList[Union[FunctionDef, JSMethod]]
    class_attrs: tpList[Assign]

    _in_postproc = False

    def _this_constructor(self):
        this_name = Name(None, id='this')
        ret_expr = Attribute(
            None,
            value=this_name,
            attr='constructor'
        )
        return ret_expr

    def _this_constructor_attr(self, a: str):
        ret_expr = Attribute(
            None,
            value=self._this_constructor(),
            attr=a
        )
        return ret_expr

    def _inst_class_attr_getter(self, a: str, getter_name: str = None):
        getter_name = getter_name or a
        assert getter_name
        value = self._this_constructor_attr(a) if a else self._this_constructor()
        getter = Getter(
            None,
            has_self_arg=False,
            name=getter_name,
            body=[Return(None, value=value)]
        )
        return getter

    def _inst_attr_setter(self, a: str):
        args = [
            Name(None, id='this'),
            Constant(None, value=a),
            Name(None, id='{value: v, writable: true, enumerable: true, configurable: true}'),  # TODO
        ]
        obj_def = Call(
            None,
            func=Name(None, id='Object.defineProperty'),
            args=args
        )
        setter = Setter(
            None,
            has_self_arg=False,
            args=arguments(None, args=[arg(None, arg='v')]),
            name=a,
            body=[obj_def]
        )
        return setter

    def created(self):
        super().created()
        class_getter = self._inst_class_attr_getter('', '__class__')
        self.body.insert(0, class_getter)

    def _print(self):
        self._in_postproc = False
        self.methods = []
        self.class_attrs: tpList[Name] = []
        out = self._output
        out.spaced('class', self.name)
        if self.bases:
            out.space()
            out.spaced('extends', self.bases[0])
        with out.in_block(scope=self):
            for st in self.body:
                if isinstance(st, Assign):
                    self.class_attrs.extend(st.targets)
                    with out.as_statement():
                        out.spaced('static', st)
                elif isinstance(st, FunctionDef):
                    self.methods.append(st)
                    with out.as_statement():
                        st.print(out)
                    if isinstance(st, JSMethod) and st.static:
                        self.class_attrs.append(st._name)
            self._print_footer()
        out.end_statement()
        self._apply_decorators()
        out.newline()

    def _print_footer(self):
        if not self.class_attrs:
            return
        out = self._output
        out.indent()
        out.print_('// expose static class attrs at instance level (except @classmethod)')
        out.newline()
        for st in self.class_attrs:
            getter = self._inst_class_attr_getter(st.id)
            setter = self._inst_attr_setter(st.id)
            with out.as_statement():
                getter.print(out)
            with out.as_statement():
                setter.print(out)

    def _apply_decorators(self):
        out = self._output
        params = []
        for m in self.methods:
            if not m.decorator_list:
                continue
            kind = Constant(None, value=m.kind)
            dec_expr = DecoratedExpr(Name(None, id='func'), m.decorator_list)
            static = m.static or m.classmeth if isinstance(m, JSMethod) else False
            params.append([static, m.name, m.kind, m.decorator_list])
        if params:
            self_proto = f'{self.name}.prototype'
            for static, name, kind, dec_list in params:
                with out.as_statement():
                    if kind not in ['get', 'set']:
                        attr_name = Attribute(
                            None,
                            value=Name(None, id=self_proto if not static else self.name),
                            attr=name
                        )
                        assign = Assign(
                            None,
                            targets=[attr_name],
                            value=DecoratedExpr(attr_name, dec_list)
                        )
                        assign.print(out)
                    else:
                        obj = self_proto if not static else self.name
                        tmp = Name(None, id=out.newTemp())
                        get_descr = Call(
                            None,
                            func=Name(None, id='Object.getOwnPropertyDescriptor'),
                            args=[
                                Name(None, id=obj),
                                Constant(None, value=name)
                            ]
                        )
                        tmp_assign = Assign(None, targets=[tmp], value=get_descr)
                        getter_attr = Attribute(None, value=tmp, attr=kind)
                        tmp_assign_decr = Assign(
                            None,
                            targets=[getter_attr],
                            value=DecoratedExpr(getter_attr, dec_list)
                        )
                        set_descr = Call(
                            None,
                            func=Name(None, id='Object.defineProperty'),
                            args=[
                                Name(None, id=obj),
                                Constant(None, value=name),
                                tmp
                            ]
                        )
                        with out.in_parens():
                            out.sequence(tmp_assign, tmp_assign_decr, set_descr)

        # decorate class
        if self.decorator_list:
            self_name = Name(None, id=self.name)
            dec_expr = DecoratedExpr(self_name, self.decorator_list)
            self_decorate = Assign(None, targets=[self_name], value=dec_expr)
            with out.as_statement():
                self_decorate.print(out)


class ForComp(For):
    ifexp: expr = None

class comprehension(RSNode[ast.comprehension]):
    target: expr = NodeAttr()
    iter: expr = NodeAttr()
    ifs: tpList[expr] = NodeAttr()
    is_async: int = NodeAttr()

    def created(self):
        return ForComp(
            self._pynode,
            target=self.target,
            iter=self.iter,
            ifexp=self.ifs[0] if self.ifs else None
        )

class BaseComp(RSNode[None]):
    generators: tpList[ForComp] = NodeAttr()

    generator: ForComp = None
    body: list = None
    result: Name = None

    def created(self):
        super().created()
        self.generator = self.generators.pop()
        if self.generators:
            raise NotImplementedError('Nested comprehensions are not supported')
        gen = self.generator
        if gen.ifexp:
            self.body = []
            cond = If(gen.ifexp._pynode, test=gen.ifexp, body=self.body)
            gen.body = [cond]
        else:
            self.body = gen.body = []

    def _make_header(self):
        raise NotImplementedError()

    def _print(self):
        out = self._output
        lambda_body = [self._make_header(), self.generator, Return(None, value=self.result)]
        call = Call(None, func=Lambda(None, body=lambda_body))
        with out.inlined():
            call.print(out)


class ListComp(BaseComp):
    elt: expr = NodeAttr()

    def _make_header(self):
        out = self._output
        tmp = Name(None, id=out.newTemp(kind='var'), ctx=Store())
        tmp_assign = Assign(None, targets=[tmp], value=List(None, elts=None), kind='var')
        push = Call(
            None,
            func=Attribute(None, value=tmp, attr='push'),
            args=[self.elt]
        )
        self.body.append(push)
        self.result = tmp
        return tmp_assign


class DictComp(BaseComp):
    key: expr = NodeAttr()
    value: expr = NodeAttr()

    def _make_header(self):
        out = self._output
        tmp = Name(None, id=out.newTemp(kind='var'), ctx=Store())
        tmp_assign = Assign(None, targets=[tmp], value=Dict(None, keys=None), kind='var')
        trg = Subscript(None, value=tmp, slice=self.key)
        self.body.append(
            Assign(None, targets=[trg], value=self.value)
        )
        self.result = tmp
        return tmp_assign


class GeneratorExp(BaseComp):
    elt: expr = NodeAttr()

    def _print(self):
        out = self._output
        self.body.append(Yield(None, value=self.elt))
        call = Call(None, func=FunctionDef(None, body=[self.generator], no_locals=True))
        with out.inlined():
            call.print(out)


class Raise(RSNode[ast.Raise]):
    exc: Optional[expr] = NodeAttr()
    cause: Optional[expr] = NodeAttr()

    def _print(self):
        out = self._output
        with out.as_statement():
            out.print_('throw')
            out.space()
            if not self.exc:
                out.print_(f'{PREFIX}Exception')
            else:
                self.exc.print(out)


class ExceptHandler(RSNode[ast.ExceptHandler]):
    type: Optional[expr] = NodeAttr()
    name: Optional[str] = NodeAttr()
    body: tpList[stmt] = NodeAttr()
    is_default: bool = False

    def created(self):
        if isinstance(self.type, Name) and self.type.id in ['Exception', 'BaseException']:
            self.is_default = True
            self.type = None


class Try(RSNode[ast.Try]):
    body: tpList[stmt] = NodeAttr()
    handlers: tpList[ExceptHandler] = NodeAttr()
    orelse: tpList[stmt] = NodeAttr()
    finalbody: tpList[stmt] = NodeAttr()
    catch_body: tpList[expr] = None

    err_name_required = False

    def created(self) -> Optional['RSNode']:
        super().created()
        if not self.handlers:
            return
        if len(self.handlers) == 1 and not self.handlers[0].type:
            h = self.handlers[0]
            self.catch_body = h.body
            if h.name:
                err_var = Assign(None, kind='var', targets=[Name(None, id=h.name)], value=self._catch_error())
                h.body.insert(0, err_var)
        else:
            self.catch_body = self._make_catch_body()

    def _catch_error(self):
        self.err_name_required = True
        return Name(None, id=f'{PREFIX}Exception')

    def _make_catch_body(self):
        top_if = None
        default_handler = None
        first = True
        last = self.handlers[-1] if self.handlers else None
        for h in self.handlers:
            if not default_handler and h.is_default:
                default_handler = h
            if h.type:
                test = Call(None, func=Name(None, id='isinstance'), args=[self._catch_error(), h.type])
            else:
                test = Constant(None, value=True)
            if h.name:
                err_var = Assign(None, kind='var', targets=[Name(None, id=h.name)], value=self._catch_error())
                h.body.insert(0, err_var)
            curIf = If(h._pynode, test=test, body=h.body, orelse=[])
            if first:
                prev_if = top_if = curIf
                first = False
            else:
                if h is last and h is default_handler:
                    prev_if.orelse = curIf.body
                else:
                    prev_if.orelse.append(curIf)
                prev_if = curIf

        if not default_handler:
            prev_if.orelse.append(Raise(None, exc=self._catch_error()))
        return [top_if]

    def _print(self):
        out = self._output
        out.print_('try')
        with out.in_block():
            for st in self.body:
                with out.as_statement():
                    st.print(out)
        if self.catch_body:
            out.print_('catch')
            if self.err_name_required:
                with out.in_parens():
                    self._catch_error().print(out)
            with out.in_block():
                for stmt in self.catch_body:
                    with out.as_statement():
                        stmt.print(out)
        if self.finalbody:
            out.print_('finally')
            with out.in_block():
                for stmt in self.finalbody:
                    with out.as_statement():
                        stmt.print(out)


class VCall(Call):
    'v.bind(item="item", foo="bar || baz")'

    v_attr: str = None
    v_bindings: dict = None
    v_exp: str = None

    def _format_attr(self, a: str):
        map = {
            'elif': 'else-if'
        }
        a = a.lower()
        return map.get(a, a)

    def get_value(self) -> tpList[str]:
        self._parse()
        if self.v_exp:
            return [f'{self.v_attr}="{self.v_exp}"']
        elif self.v_bindings:
            buf = []
            for dst, src in self.v_bindings.items():
                if dst == 'Class':
                    dst = dst.lower()
                attr_value = f'{self.v_attr}:{dst}="{src}"'
                buf.append(attr_value)
            return buf
        else:
            'v-else'
            return [f'{self.v_attr}']

    def _parse(self):
        assert isinstance(self.func, Attribute)
        assert isinstance(self.func.value, Name)
        assert self.func.value.id == 'v'
        attr = self._format_attr(self.func.attr)
        self.v_attr = f'v-{attr}'
        self._parse_args()

    def _parse_args(self):
        self.v_bindings = {}
        if self.args:
            if len(self.args) == 1 and isinstance(self.args[0], Constant):
                a = self.args[0]
                assert isinstance(a.value, str)
                self.v_exp = a.value
                return
            else:
                # v.bind(('[foo]', bar), some='baz')
                for a in self.args:
                    assert isinstance(a, Tuple) and len(a.elts) == 2
                    assert all(isinstance(c, Constant) for c in a.elts)
                    dst, src = [c.value for c in a.elts]
                    self.v_bindings[dst] = src
        for kw in self.keywords:
            assert isinstance(kw.value, Constant)
            dst = kw.arg
            self.v_bindings[dst] = kw.value.value


class VTag(Call):
    args: tpList[VCall] = None

    @property
    def tag_name(self) -> str:
        return self.func.id

    def created(self):
        args = []
        for a in self.args:
            assert isinstance(a, Call)
            args.append(
                VCall(
                    None,
                    func=a.func,
                    args=a.args,
                    keywords=a.keywords
                )
            )
        self.args[:] = args

    def _print(self):
        out = self._output
        buf = []
        for a in self.args:
            buf.extend(a.get_value())
        for kw in self.keywords:
            attr = kw.arg
            if attr == 'Class':
                attr = attr.lower()
            v = kw.value.value
            if isinstance(v, bool):
                if v:
                    buf.append(attr)
                continue
            buf.append(f'{attr}="{v}"')

        attrs = ', '.join(buf)
        assert isinstance(self.func, Name)
        tag = self.func.id
        if attrs:
            tag_exp = f'<{tag} {attrs} >'
        else:
            tag_exp = f'<{tag}>'
        out.print_(tag_exp)


class VDict(Dict):

    def _transform(self):
        for idx, k in enumerate(self.keys):
            assert isinstance(k, Call)
            tag = k.func
            if isinstance(tag, Attribute):
                # h.div
                tag = Name(None, id=tag.attr)
            else:
                assert isinstance(tag, Name)
            self.keys[idx] = VTag(
                k._pynode,
                func=tag,
                args=k.args,
                keywords=k.keywords
            )
        for idx, v in enumerate(self.values):
            if isinstance(v, Dict):
                self.values[idx] = VDict(
                    v._pynode,
                    keys=v.keys,
                    values=v.values
                )
            elif isinstance(v, Constant) and not v.value:
                # no content
                self.values[idx] = None

    def _print(self):
        self._transform()
        out = self._output
        nested = isinstance(out.parent(), VDict)
        with out.as_string(not nested):
            with out.inlined():
                for tag, body in zip(self.keys, self.values):
                    tag: VTag
                    tag.print(out)
                    if body is not None:
                        out.newline()
                        with out.indented():
                            out.indent()
                            body.print(out)
                        out.newline()
                    out.indent()
                    out.print_(f'</{tag.tag_name}>')
