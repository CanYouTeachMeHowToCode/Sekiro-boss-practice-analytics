"""Decompile a stripped Lua 5.0 bytecode chunk (FromSoftware AI script) into readable pseudo-Lua.

Usage: python -I lua50_decompile.py <file.lua> [out.txt]

The chunk has no debug information, so registers are named r0, r1, ... (parameters p0, p1, ...).
Compiler temporaries that are read exactly once are inlined into the expression that uses them.
Forward conditional jumps are turned back into if / elseif / else blocks where the jump pattern
allows; anything else stays as `goto Ln` with labels, so the output is always complete.
Instruction format (Lua 5.0, lopcodes.h): OP 6 bits, C 9, B 9, A 8; RK operand >= 250 is a constant.
"""
import struct
import sys

MAXSTACK = 250
FPF = 32
OPS = ["MOVE", "LOADK", "LOADBOOL", "LOADNIL", "GETUPVAL", "GETGLOBAL", "GETTABLE", "SETGLOBAL",
       "SETUPVAL", "SETTABLE", "NEWTABLE", "SELF", "ADD", "SUB", "MUL", "DIV", "POW", "UNM", "NOT",
       "CONCAT", "JMP", "EQ", "LT", "LE", "TEST", "CALL", "TAILCALL", "RETURN", "FORLOOP", "TFORLOOP",
       "TFORPREP", "SETLIST", "SETLISTO", "CLOSE", "CLOSURE"]
BINOPS = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "POW": "^"}


# ----------------------------------------------------------------------------- loading
class Reader:
    def __init__(self, b):
        self.b, self.o = b, 0

    def take(self, n):
        v = self.b[self.o:self.o + n]
        self.o += n
        return v

    def byte(self):
        return self.take(1)[0]

    def int(self):
        return struct.unpack("<i", self.take(4))[0]

    def size_t(self):
        return struct.unpack("<Q", self.take(8))[0]

    def string(self):
        n = self.size_t()
        return None if n == 0 else self.take(n)[:-1].decode("latin-1")


class Proto:
    pass


def load_function(r):
    f = Proto()
    f.source = r.string()
    f.line = r.int()
    f.nups, f.numparams, f.is_vararg, f.maxstack = r.byte(), r.byte(), r.byte(), r.byte()
    r.take(4 * r.int())
    for _ in range(r.int()):
        r.string(); r.int(); r.int()
    for _ in range(r.int()):
        r.string()
    f.k = []
    for _ in range(r.int()):
        t = r.byte()
        if t == 3:
            f.k.append(("n", struct.unpack("<d", r.take(8))[0]))
        elif t == 4:
            f.k.append(("s", r.string()))
        elif t == 0:
            f.k.append(("nil", None))
        else:
            raise ValueError(f"constant type {t}")
    f.p = [load_function(r) for _ in range(r.int())]
    f.code = [struct.unpack("<I", r.take(4))[0] for _ in range(r.int())]
    f.name = None
    return f


def load(path):
    b = open(path, "rb").read()
    assert b[:5] == b"\x1bLuaP", "not Lua 5.0 bytecode"
    assert b[5:14] == bytes([1, 4, 8, 4, 6, 8, 9, 9, 8]), "unexpected header"
    r = Reader(b)
    r.o = 22
    main = load_function(r)
    assert r.o == len(b), f"parsed {r.o} of {len(b)} bytes"
    return main


def decode(i):
    return {"op": OPS[i & 0x3F], "A": (i >> 24) & 0xFF, "B": (i >> 15) & 0x1FF, "C": (i >> 6) & 0x1FF,
            "Bx": (i >> 6) & 0x3FFFF, "sBx": ((i >> 6) & 0x3FFFF) - 131071}


# ----------------------------------------------------------------------------- expressions
def fmt_const(c):
    t, v = c
    if t == "n":
        return str(int(v)) if v == int(v) and abs(v) < 1e15 else repr(v)
    if t == "s":
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "nil"


def is_ident(s):
    return s and (s[0].isalpha() or s[0] == "_") and all(ch.isalnum() or ch == "_" for ch in s)


class Expr:
    """An expression string plus its precedence (higher binds tighter)."""

    def __init__(self, text, prec=100):
        self.text, self.prec = text, prec

    def wrap(self, prec):
        return self.text if self.prec >= prec else f"({self.text})"


NEG = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "~=", "~=": "=="}


class Cond:
    """A condition for a jump: left op right, or a truth test (op None)."""

    def __init__(self, left, op, right, negated=False):
        self.left, self.op, self.right, self.negated = left, op, right, negated

    def negate(self):
        return Cond(self.left, self.op, self.right, not self.negated)

    def text(self):
        if self.op is None:
            return self.left.text if not self.negated else "not " + self.left.wrap(90)
        op = NEG[self.op] if self.negated else self.op
        return f"{self.left.wrap(50)} {op} {self.right.wrap(50)}"


class Bool:
    """A compound jump condition: op is "and" or "or"; negate applies De Morgan."""

    def __init__(self, op, items):
        flat = []
        for it in items:
            flat.extend(it.items if isinstance(it, Bool) and it.op == op else [it])
        self.op, self.items = op, flat

    @property
    def prec(self):
        return 20 if self.op == "and" else 10

    def negate(self):
        return Bool("or" if self.op == "and" else "and", [i.negate() for i in self.items])

    def text(self):
        parts = []
        for it in self.items:
            t = it.text()
            parts.append(f"({t})" if isinstance(it, Bool) and it.prec < self.prec else t)
        return f" {self.op} ".join(parts)


def cond_or(conds):
    return " or ".join(c.text() if len(conds) == 1 else f"({c.text()})" if " and " in c.text() or " or " in c.text() else c.text() for c in conds)


def cond_and_not(conds):
    """The condition under which none of the jumps is taken."""
    parts = [c.negate().text() for c in conds]
    return " and ".join(p if len(parts) == 1 or (" or " not in p) else f"({p})" for p in parts)


# ----------------------------------------------------------------------------- per-function decompiler
class Stmt:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)


class FunctionDecompiler:
    def __init__(self, f):
        self.f = f
        self.ins = [decode(i) for i in f.code]
        self.n = len(self.ins)

    def rname(self, r):
        return f"p{r}" if r < self.f.numparams else f"r{r}"

    # -- control flow: which instructions are skipped pseudo-ops, block leaders, jump targets
    def analyse(self):
        ins = self.ins
        self.pseudo = set()
        for pc, x in enumerate(ins):
            if x["op"] == "CLOSURE":
                for j in range(self.f.p[x["Bx"]].nups):
                    self.pseudo.add(pc + 1 + j)
        self.succ = {}
        self.targets = set()
        for pc, x in enumerate(ins):
            if pc in self.pseudo:
                continue
            op = x["op"]
            nxt = pc + 1
            while nxt in self.pseudo:
                nxt += 1
            if op == "JMP":
                t = pc + 1 + x["sBx"]
                self.succ[pc] = [t]
                self.targets.add(t)
            elif op in ("EQ", "LT", "LE", "TEST", "TFORLOOP"):
                self.succ[pc] = [pc + 1, pc + 2]
                self.targets.add(pc + 2)
            elif op == "LOADBOOL" and x["C"]:
                self.succ[pc] = [pc + 2]
                self.targets.add(pc + 2)
            elif op == "FORLOOP":
                t = pc + 1 + x["sBx"]
                self.succ[pc] = [nxt, t]
                self.targets.add(t)
            elif op == "TFORPREP":
                t = pc + 1 + x["sBx"]
                self.succ[pc] = [t]
                self.targets.add(t)
            elif op in ("RETURN", "TAILCALL"):
                self.succ[pc] = []
            else:
                self.succ[pc] = [nxt]
        leaders = {0} | self.targets
        for pc, s in self.succ.items():
            if len(s) != 1 or s[0] != pc + 1:
                leaders.add(pc + 1)
        self.leaders = sorted(l for l in leaders if l < self.n)

    # -- register reads and writes of one instruction, for liveness
    def rw(self, pc):
        x = self.ins[pc]
        op, A, B, C = x["op"], x["A"], x["B"], x["C"]
        rk = lambda v: [] if v >= MAXSTACK else [v]
        if op == "MOVE":
            return [B], [A]
        if op in ("LOADK", "GETGLOBAL", "GETUPVAL", "NEWTABLE", "LOADBOOL", "CLOSURE"):
            reads = []
            if op == "CLOSURE":
                for j in range(self.f.p[x["Bx"]].nups):
                    y = self.ins[pc + 1 + j]
                    if y["op"] == "MOVE":
                        reads.append(y["B"])
            return reads, [A]
        if op == "LOADNIL":
            return [], list(range(A, B + 1))
        if op in ("SETGLOBAL", "SETUPVAL"):
            return [A], []
        if op == "GETTABLE":
            return [B] + rk(C), [A]
        if op == "SETTABLE":
            return [A] + rk(B) + rk(C), []
        if op == "SELF":
            return [B] + rk(C), [A, A + 1]
        if op in BINOPS:
            return rk(B) + rk(C), [A]
        if op in ("UNM", "NOT"):
            return [B], [A]
        if op == "CONCAT":
            return list(range(B, C + 1)), [A]
        if op in ("EQ", "LT", "LE"):
            return rk(B) + rk(C), []
        if op == "TEST":
            return [B], [A] if A != B else []
        if op in ("CALL", "TAILCALL"):
            nargs = B - 1 if B else max(0, self.f.maxstack - A - 1)
            nres = C - 1 if C else max(0, self.f.maxstack - A)
            return list(range(A, A + 1 + nargs)), list(range(A, A + nres))
        if op == "RETURN":
            return list(range(A, A + B - 1)) if B else list(range(A, self.f.maxstack)), []
        if op == "FORLOOP":
            return [A, A + 1, A + 2], [A]
        if op == "TFORLOOP":
            return [A, A + 1, A + 2], list(range(A + 2, A + 3 + C))
        if op == "TFORPREP":
            return [A], [A, A + 1, A + 2]
        if op in ("SETLIST", "SETLISTO"):
            n = x["Bx"] % FPF + 1
            return list(range(A, A + 1 + n)), []
        return [], []

    def liveness(self):
        blocks = []
        for i, s in enumerate(self.leaders):
            e = self.leaders[i + 1] if i + 1 < len(self.leaders) else self.n
            blocks.append((s, e))
        self.blocks = blocks
        self.block_of = {}
        for bi, (s, e) in enumerate(blocks):
            for pc in range(s, e):
                self.block_of[pc] = bi
        use, defs = [], []
        for s, e in blocks:
            u, d = set(), set()
            for pc in range(s, e):
                if pc in self.pseudo:
                    continue
                rd, wr = self.rw(pc)
                u |= set(rd) - d
                d |= set(wr)
            use.append(u)
            defs.append(d)
        succ_b = []
        for s, e in blocks:
            last = e - 1
            while last in self.pseudo:
                last -= 1
            succ_b.append({self.block_of[t] for t in self.succ.get(last, []) if t in self.block_of})
        live_in = [set() for _ in blocks]
        live_out = [set() for _ in blocks]
        changed = True
        while changed:
            changed = False
            for bi in reversed(range(len(blocks))):
                out = set().union(*[live_in[s] for s in succ_b[bi]]) if succ_b[bi] else set()
                inn = use[bi] | (out - defs[bi])
                if out != live_out[bi] or inn != live_in[bi]:
                    live_out[bi], live_in[bi] = out, inn
                    changed = True
        self.live_out = live_out

    def inlinable(self, pc, reg):
        """A register written at pc is inlined when it is read exactly once, later in the same block,
        before being written again, and is not live after the block."""
        s, e = self.blocks[self.block_of[pc]]
        reads = 0
        redefined = False
        for q in range(pc + 1, e):
            if q in self.pseudo:
                continue
            rd, wr = self.rw(q)
            reads += rd.count(reg)
            if reg in wr:
                redefined = True
                break
        if reads != 1:
            return False
        return redefined or reg not in self.live_out[self.block_of[pc]]

    # -- linear statements with symbolic expressions
    def linear(self):
        self.analyse()
        self.liveness()
        ins, k = self.ins, self.f.k
        out = []
        pending = {}

        def R(r):
            if r in pending:
                return pending.pop(r)
            return Expr(self.rname(r))

        def RK(v):
            return Expr(fmt_const(k[v - MAXSTACK])) if v >= MAXSTACK else R(v)

        def flush():
            for r in sorted(pending):
                out.append(Stmt("assign", pc=None, targets=[self.rname(r)], value=pending[r]))
            pending.clear()

        def put(pc, reg, e):
            if self.inlinable(pc, reg):
                pending[reg] = e
            else:
                flush()
                out.append(Stmt("assign", pc=pc, targets=[self.rname(reg)], value=e))

        def index(base, key):
            kt = key.text
            if kt.startswith('"') and is_ident(kt[1:-1]):
                return Expr(f"{base.wrap(100)}.{kt[1:-1]}")
            return Expr(f"{base.wrap(100)}[{kt}]")

        pc = 0
        while pc < self.n:
            if pc in self.pseudo:
                pc += 1
                continue
            if pc in self.targets or pc in self.leaders:
                flush()
                out.append(Stmt("label", pc=pc))
            x = ins[pc]
            op, A, B, C = x["op"], x["A"], x["B"], x["C"]
            if op == "MOVE":
                put(pc, A, R(B))
            elif op == "LOADK":
                put(pc, A, Expr(fmt_const(k[x["Bx"]])))
            elif op == "LOADBOOL":
                put(pc, A, Expr("true" if B else "false"))
                if C:
                    flush()
                    out.append(Stmt("goto", pc=pc, target=pc + 2))
            elif op == "LOADNIL":
                for r in range(A, B + 1):
                    put(pc, r, Expr("nil"))
            elif op == "GETUPVAL":
                put(pc, A, Expr(f"upval{B}"))
            elif op == "GETGLOBAL":
                put(pc, A, Expr(k[x["Bx"]][1]))
            elif op == "GETTABLE":
                key = RK(C)
                base = R(B)
                put(pc, A, index(base, key))
            elif op == "SETGLOBAL":
                v = R(A)
                flush()
                out.append(Stmt("assign", pc=pc, targets=[k[x["Bx"]][1]], value=v))
            elif op == "SETUPVAL":
                v = R(A)
                flush()
                out.append(Stmt("assign", pc=pc, targets=[f"upval{B}"], value=v))
            elif op == "SETTABLE":
                v = RK(C)
                key = RK(B)
                base = R(A)
                flush()
                out.append(Stmt("assign", pc=pc, targets=[index(base, key).text], value=v))
            elif op == "NEWTABLE":
                put(pc, A, Expr("{}"))
            elif op == "SELF":
                key = RK(C)
                obj = R(B)
                name = key.text[1:-1] if key.text.startswith('"') else key.text
                # A holds the method, A+1 the object; a CALL on A renders obj:method(...)
                pending[A] = Expr(f"{obj.wrap(100)}:{name}")
                pending[A + 1] = Expr("__self__")
            elif op in BINOPS:
                c = RK(C)
                b = RK(B)
                prec = 70 if op in ("ADD", "SUB") else 80 if op in ("MUL", "DIV") else 95
                put(pc, A, Expr(f"{b.wrap(prec)} {BINOPS[op]} {c.wrap(prec + 1)}", prec))
            elif op == "UNM":
                put(pc, A, Expr("-" + R(B).wrap(90), 90))
            elif op == "NOT":
                put(pc, A, Expr("not " + R(B).wrap(90), 90))
            elif op == "CONCAT":
                parts = [R(r) for r in range(B, C + 1)]
                put(pc, A, Expr(" .. ".join(p.wrap(61) for p in parts), 60))
            elif op == "JMP":
                flush()
                out.append(Stmt("goto", pc=pc, target=pc + 1 + x["sBx"]))
            elif op in ("EQ", "LT", "LE"):
                c = RK(C)
                b = RK(B)
                sym = {"EQ": "==", "LT": "<", "LE": "<="}[op]
                # if ((B op C) ~= A) skip the next JMP; so the JMP is taken when (B op C) == A
                cond = Cond(b, sym, c, negated=not A)
                flush()
                nxt = ins[pc + 1]
                assert nxt["op"] == "JMP", f"{op} not followed by JMP at {pc}"
                out.append(Stmt("if_goto", pc=pc, cond=cond, target=pc + 2 + nxt["sBx"]))
                pc += 2
                continue
            elif op == "TEST":
                v = R(B)
                flush()
                nxt = ins[pc + 1]
                assert nxt["op"] == "JMP", f"TEST not followed by JMP at {pc}"
                cond = Cond(v, None, None, negated=not C)
                if A != B:
                    out.append(Stmt("if_goto", pc=pc, cond=cond, target=pc + 2 + nxt["sBx"],
                                    assign=(self.rname(A), v.text)))
                else:
                    out.append(Stmt("if_goto", pc=pc, cond=cond, target=pc + 2 + nxt["sBx"]))
                pc += 2
                continue
            elif op in ("CALL", "TAILCALL"):
                nargs = B - 1 if B else None
                if nargs is None:
                    args = []
                    r = A + 1
                    while r in pending:
                        args.append(R(r))
                        r += 1
                else:
                    args = [R(r) for r in range(A + 1, A + 1 + nargs)]
                fn = R(A)
                if args and args[0].text == "__self__":
                    args = args[1:]
                text = f"{fn.wrap(100)}({', '.join(a.text for a in args)})"
                if op == "TAILCALL":
                    flush()
                    out.append(Stmt("return", pc=pc, values=[text]))
                elif C == 1:
                    flush()
                    out.append(Stmt("call", pc=pc, text=text))
                elif C == 2:
                    put(pc, A, Expr(text))
                else:
                    flush()
                    n = C - 1 if C else 1
                    tg = [self.rname(A + j) for j in range(n)] if C else [self.rname(A) + "..."]
                    out.append(Stmt("assign", pc=pc, targets=tg, value=Expr(text)))
            elif op == "RETURN":
                vals = [R(r).text for r in range(A, A + B - 1)] if B else [self.rname(A) + "..."]
                flush()
                out.append(Stmt("return", pc=pc, values=vals))
            elif op == "FORLOOP":
                flush()
                out.append(Stmt("raw", pc=pc, text=f"for-step {self.rname(A)} += {self.rname(A + 2)}; if {self.rname(A)} <= {self.rname(A + 1)} goto L{pc + 1 + x['sBx']}"))
                self.targets.add(pc + 1 + x["sBx"])
            elif op == "TFORLOOP":
                flush()
                out.append(Stmt("raw", pc=pc, text=f"{', '.join(self.rname(A + 2 + j) for j in range(C + 1))} = {self.rname(A)}({self.rname(A + 1)}, {self.rname(A + 2)}); if {self.rname(A + 2)} == nil skip next"))
            elif op == "TFORPREP":
                flush()
                out.append(Stmt("raw", pc=pc, text=f"tforprep {self.rname(A)}; goto L{pc + 1 + x['sBx']}"))
            elif op in ("SETLIST", "SETLISTO"):
                n = x["Bx"] % FPF + 1
                base = x["Bx"] - x["Bx"] % FPF
                vals = [R(r) for r in range(A + 1, A + 1 + n)]
                tbl = R(A)
                flush()
                for j, v in enumerate(vals):
                    out.append(Stmt("assign", pc=pc, targets=[f"{tbl.wrap(100)}[{base + j + 1}]"], value=v))
                if not self.inlinable(pc, A) and tbl.text != self.rname(A):
                    pass
            elif op == "CLOSE":
                pass
            elif op == "CLOSURE":
                sub = self.f.p[x["Bx"]]
                caps = []
                for j in range(sub.nups):
                    y = ins[pc + 1 + j]
                    caps.append(self.rname(y["B"]) if y["op"] == "MOVE" else f"upval{y['B']}")
                ref = f"<function #{sub.idx}>" + (f" capturing {', '.join(caps)}" if caps else "")
                put(pc, A, Expr(ref))
            else:
                flush()
                out.append(Stmt("raw", pc=pc, text=f"{op} {A} {B} {C}"))
            pc += 1
        flush()
        out.append(Stmt("label", pc=self.n))
        return out

    # -- structuring: turn forward conditional jumps back into if / elseif / else
    def merge_conditions(self, stmts, refs):
        """Fold short-circuit jump chains into single conditional jumps:
        - if c1 goto E; if c2 goto E            =>  if (c1 or c2) goto E
        - if c1 goto T; if c2 goto E; ::T::     =>  if (not c1 and c2) goto E   (T used only here)
        Unreferenced labels between the jumps are ignored."""
        def nxt(i):
            i += 1
            while i < len(stmts) and stmts[i].kind == "label" and refs[stmts[i].pc] == 0:
                i += 1
            return i

        plain_if = lambda st: st.kind == "if_goto" and not getattr(st, "assign", None)
        changed = True
        while changed:
            changed = False
            for i in range(len(stmts)):
                a = stmts[i]
                if a is None or not plain_if(a):
                    continue
                j = nxt(i)
                if j >= len(stmts) or not plain_if(stmts[j]):
                    continue
                b = stmts[j]
                if b.target == a.target:
                    b.cond = Bool("or", [a.cond, b.cond])
                    refs[a.target] -= 1
                    stmts[i] = Stmt("label", pc=-1)
                    changed = True
                    continue
                t = nxt(j)
                if t < len(stmts) and stmts[t].kind == "label" and stmts[t].pc == a.target and refs[a.target] == 1:
                    b.cond = Bool("and", [a.cond.negate(), b.cond])
                    refs[a.target] -= 1
                    stmts[i] = Stmt("label", pc=-1)
                    changed = True
            stmts[:] = [st for st in stmts if not (st.kind == "label" and st.pc == -1)]
        return stmts

    def structure(self, stmts):
        from collections import Counter
        refs0 = Counter(s.target for s in stmts if s.kind in ("goto", "if_goto"))
        stmts = self.merge_conditions(list(stmts), refs0)
        label_at = {s.pc: i for i, s in enumerate(stmts) if s.kind == "label"}
        self.refs = Counter(s.target for s in stmts if s.kind in ("goto", "if_goto"))
        jumpers = [(i, s.target) for i, s in enumerate(stmts) if s.kind in ("goto", "if_goto")]

        def entered_from_outside(lo, hi):
            inside = {stmts[i].pc for i in range(lo, hi) if stmts[i].kind == "label"}
            return any(t in inside and not (lo <= i < hi) for i, t in jumpers)

        def block(lo, hi):
            nodes = []
            i = lo
            while i < hi:
                s = stmts[i]
                if s.kind == "if_goto" and not getattr(s, "assign", None) and s.target in label_at:
                    j = i
                    conds = [s.cond]
                    while j + 1 < hi and stmts[j + 1].kind == "if_goto" and stmts[j + 1].target == s.target                             and not getattr(stmts[j + 1], "assign", None):
                        j += 1
                        conds.append(stmts[j].cond)
                    L = label_at[s.target]
                    if j < L <= hi and not entered_from_outside(j + 1, L):
                        then_lo, then_hi = j + 1, L
                        last = then_hi - 1
                        while last >= then_lo and stmts[last].kind == "label" and self.refs[stmts[last].pc] == 0:
                            last -= 1
                        if last >= then_lo and stmts[last].kind == "goto" and stmts[last].target in label_at:
                            E = label_at[stmts[last].target]
                            if L < E <= hi and not entered_from_outside(L + 1, E)                                     and not entered_from_outside(then_lo, last):
                                self.refs[s.target] -= len(conds)
                                self.refs[stmts[last].target] -= 1
                                nodes.append(("if", cond_and_not(conds), block(then_lo, last), block(L + 1, E)))
                                i = E
                                continue
                        self.refs[s.target] -= len(conds)
                        nodes.append(("if", cond_and_not(conds), block(then_lo, then_hi), None))
                        i = L
                        continue
                nodes.append(("stmt", s))
                i += 1
            return nodes

        tree = block(0, len(stmts))
        lines = []
        self.render(tree, 1, lines)
        return lines

    def visible(self, nodes):
        return [n for n in nodes if not (n[0] == "stmt" and n[1].kind == "label" and self.refs[n[1].pc] <= 0)]

    def render(self, nodes, depth, lines, as_elseif=False):
        pad = "    " * depth
        for n in nodes:
            if n[0] == "if":
                _, cond, then_nodes, else_nodes = n
                lines.append(pad + f"if {cond} then")
                self.render(then_nodes, depth + 1, lines)
                tail = else_nodes
                while tail is not None:
                    vis = self.visible(tail)
                    if len(vis) == 1 and vis[0][0] == "if":
                        _, c2, t2, e2 = vis[0]
                        lines.append(pad + f"elseif {c2} then")
                        self.render(t2, depth + 1, lines)
                        tail = e2
                    else:
                        if vis:
                            lines.append(pad + "else")
                            self.render(tail, depth + 1, lines)
                        tail = None
                lines.append(pad + "end")
            else:
                self.plain(n[1], lines, depth)

    def plain(self, s, lines, depth):
        pad = "    " * depth
        if s.kind == "label":
            if self.refs[s.pc] > 0:
                lines.append(f"::L{s.pc}::")
        elif s.kind == "assign":
            lines.append(pad + f"{', '.join(s.targets)} = {s.value.text}")
        elif s.kind == "call":
            lines.append(pad + s.text)
        elif s.kind == "goto":
            lines.append(pad + f"goto L{s.target}")
        elif s.kind == "if_goto":
            extra = f" {s.assign[0]} = {s.assign[1]};" if getattr(s, "assign", None) else ""
            lines.append(pad + f"if {s.cond.text()} then{extra} goto L{s.target} end")
        elif s.kind == "return":
            lines.append(pad + ("return " + ", ".join(s.values) if s.values else "return"))
        elif s.kind == "raw":
            lines.append(pad + s.text)


def number_protos(main):
    allp = []

    def walk(f):
        f.idx = len(allp)
        allp.append(f)
        for c in f.p:
            walk(c)
    walk(main)
    return allp


def name_protos(allp):
    """Name each function after what the parent assigns its closure to (Goal.Activate, Foo_Act01, ...)."""
    for f in allp:
        d = FunctionDecompiler(f)
        stmts = d.linear()
        for s in stmts:
            if s.kind == "assign" and s.value.text.startswith("<function #"):
                idx = int(s.value.text.split("#")[1].split(">")[0])
                if allp[idx].name is None:
                    allp[idx].name = s.targets[0]


def decompile(path):
    main = load(path)
    allp = number_protos(main)
    name_protos(allp)
    chunks = []
    for f in allp:
        d = FunctionDecompiler(f)
        stmts = d.linear()
        lines = d.structure(stmts)
        params = ", ".join(f"p{i}" for i in range(f.numparams)) + (", ..." if f.is_vararg else "")
        title = f.name or ("main chunk" if f.idx == 0 else "anonymous")
        chunks.append(f"-- function #{f.idx}: {title}  (defined at source line {f.line}, {len(f.code)} instructions)\n"
                      f"function({params})\n" + "\n".join(lines) + "\nend\n")
    return "\n".join(chunks)


if __name__ == "__main__":
    text = decompile(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(text)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
