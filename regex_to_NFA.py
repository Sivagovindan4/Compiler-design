from collections import defaultdict
from itertools import count

EPS = None

def add_concat(r):
    out, prev = [], None
    for c in r:
        if prev and prev not in '|(' and c not in '|)*+?':
            out.append('.')
        out.append(c)
        prev = c
    return ''.join(out)

def to_postfix(r):
    prec = {'*': 3, '+': 3, '?': 3, '.': 2, '|': 1}
    out, st = [], []
    for c in r:
        if c == '(':
            st.append(c)
        elif c == ')':
            while st and st[-1] != '(':
                out.append(st.pop())
            st.pop() if st else None
        elif c in prec:
            while st and st[-1] != '(' and prec.get(st[-1], 0) >= prec[c]:
                out.append(st.pop())
            st.append(c)
        else:
            out.append(c)
    out.extend(reversed(st))
    return ''.join(out)

def build(postfix):
    gen = count()
    stack = []
    for t in postfix:
        if t == '.':
            s2, s1 = stack.pop(), stack.pop()
            st1, acc1, tr1 = s1
            st2, acc2, tr2 = s2
            for a in acc1:
                tr1[a].append((EPS, st2))
            for k, v in tr2.items():
                tr1[k].extend(v)
            stack.append((st1, acc2, tr1))
        elif t == '|':
            s2, s1 = stack.pop(), stack.pop()
            st1, acc1, tr1 = s1
            st2, acc2, tr2 = s2
            s, f = next(gen), next(gen)
            tr = defaultdict(list)
            for k, v in tr1.items():
                tr[k].extend(v)
            for k, v in tr2.items():
                tr[k].extend(v)
            tr[s].extend([(EPS, st1), (EPS, st2)])
            for a in acc1 | acc2:
                tr[a].append((EPS, f))
            stack.append((s, {f}, tr))
        elif t in '*+?':
            st, acc, tr0 = stack.pop()
            s, f = next(gen), next(gen)
            tr = defaultdict(list)
            for k, v in tr0.items():
                tr[k].extend(v)
            tr[s].extend([(EPS, st), (EPS, f)] if t == '?' else [(EPS, st)])
            for a in acc:
                tr[a].extend([(EPS, st), (EPS, f)] if t != '?' else [(EPS, f)])
            if t != '?':
                tr[s].append((EPS, f))
            stack.append((s, {f}, tr))
        else:
            s, f = next(gen), next(gen)
            stack.append((s, {f}, defaultdict(list, {s: [(t, f)]})))
    return stack[0]

def eps_closure(states, tr):
    res, stk = set(states), list(states)
    while stk:
        s = stk.pop()
        for sym, d in tr.get(s, []):
            if sym is EPS and d not in res:
                res.add(d)
                stk.append(d)
    return res

def move(states, ch, tr):
    return {d for s in states for sym, d in tr.get(s, []) if sym == ch}

def matches(nfa, s):
    st, acc, tr = nfa
    cur = eps_closure({st}, tr)
    for ch in s:
        cur = eps_closure(move(cur, ch, tr), tr)
        if not cur:
            return False
    return bool(cur & acc)

if __name__ == '__main__':
    cases = [("a(b|c)*d", ["ad", "abcd"], ["a"]),
             ("a|b", ["a", "b"], [""]),
             ("ab+c", ["abc", "abbc"], ["ac"])]
    for regex, yes, no in cases:
        proc = add_concat(regex)
        postfix = to_postfix(proc)
        nfa = build(postfix)
        for s in yes + no:
            print(f"{regex}: '{s}' -> {matches(nfa, s)}")