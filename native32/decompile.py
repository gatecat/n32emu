from actions import Action

binary_ops = {
    Action.Add: "+",
    Action.Subtract: "-",
    Action.Multiply: "*",
    Action.Divide: "/",
    Action.Equals: "==",
    Action.Less: "<",
    Action.And: "&",
    Action.Or: "|",
}

properties = ["_x", "_y", "_xscale", "_yscale", "_currentframe", "_totalframes", "_alpha", "_visible", "_width", "_height"]

def decompile(out, code, start_index, name):
    start_index -= 1 # native32 uses 1-based indexing
    print(f"def {name}:", file=out)
    # Discover extent of code and jump targets
    to_explore = [ start_index, ]
    explored = set()
    jump_targets = set()
    while len(to_explore) > 0:
        i = to_explore.pop()
        while i not in explored:
            explored.add(i)
            op, payload = code[i]
            if op == Action.End:
                break
            elif op in (Action.If, Action.Jump):
                dst = i + payload + 1 if payload >= 0 else i + payload
                jump_targets.add(dst)
                if dst not in explored:
                    to_explore.append(dst)
            i += 1
    stack = []

    def _prop(x):
        if x[0] == '"' and x[-1] == '"' and x[1:-1].isdigit() and int(x[1:-1]) < len(properties):
            return properties[int(x[1:-1])]
        else:
            return x

    def _get_var():
        top = stack.pop()
        if top[0] == '"' and top[-1] == '"':
            return top[1:-1]
        else:
            return f'__vars__[{top}]'

    for i in range(start_index, max(explored) + 1):
        if i in jump_targets:
            # spill stack before jump target
            for j, x in enumerate(stack):
                if x != f"t{j}":
                    print(f"    t{j} = {x}", file=out)
            print(f"l{i+1}:", file=out)
            stack = [f"t{j}" for j in range(len(stack))]
        op, payload = code[i]
        if op == Action.Push:
            stack.append(f'"{payload}"')
        elif op == Action.SetVariable:
            val = stack.pop()
            var = _get_var()
            print(f"    {var} = {val}", file=out)
        elif op == Action.GetVariable:
            stack.append(_get_var())
        elif op in (Action.Stop, Action.Play, Action.StopSounds, Action.NextFrame, Action.PreviousFrame):
            print(f"    {op.name}()", file=out)
        elif op == Action.End:
            print("    return", file=out)
        elif op in (Action.GotoFrame, Action.WaitForFrame, Action.SetTarget, Action.GotoLabel):
            print(f"    {op.name}({payload})", file=out)
        elif op == Action.Not:
            stack.append(f"(~{stack.pop()})")
        elif op == Action.If:
            print(f"    if {stack.pop()} goto l{i+payload+2 if payload >= 0 else i+payload+1}", file=out)
        elif op == Action.Call:
            print(f'    {stack.pop()}()', file=out)
        elif op in binary_ops:
            o2 = stack.pop()
            o1 = stack.pop()
            stack.append(f"({o1} {binary_ops[op]} {o2})")
        elif op in (Action.StringEquals, Action.StringAdd, Action.StringLess):
            o2 = stack.pop()
            o1 = stack.pop()
            stack.append(f"{op.name}({o1}, {o2})")
        elif op == Action.GetProperty:
            o2 = stack.pop()
            o1 = stack.pop()
            stack.append(f"{op.name}({o1}, {_prop(o2)})")
        elif op == Action.StringExtract:
            o3 = stack.pop()
            o2 = stack.pop()
            o1 = stack.pop()
            stack.append(f"{op.name}({o1}, {o2}, {o3})") 
        elif op in (Action.RandomNumber, Action.ToInteger, Action.CharToAscii, Action.AsciiToChar, Action.StringLength):
            stack.append(f"{op.name}({stack.pop()})")
        elif op == Action.GetTime:
            stack.append(f"GetTime()")
        elif op in (Action.GotoFrame2, Action.SetTarget2, Action.RemoveSprite):
            print(f"    {op.name}({stack.pop()})", file=out)
        elif op == Action.SetProperty:
            o3 = stack.pop()
            o2 = stack.pop()
            o1 = stack.pop()
            print(f"    SetProperty({o1}, {_prop(o2)}, {o3})", file=out)
        elif op == Action.CloneSprite:
            o3 = stack.pop()
            o2 = stack.pop()
            o1 = stack.pop()
            print(f"    CloneSprite({o1}, {o2}, {o3})", file=out)
        elif op == Action.Jump:
            print(f"    goto l{i+payload+2 if payload >= 0 else i+payload+1}", file=out)
        elif op == Action.Pop:
            stack.pop()
        elif op == Action.GetUrl2:
            o2 = stack.pop()
            o1 = stack.pop()
            print(f"    GetUrl2({o1}, {o2})", file=out)
        elif op == Action.Trace:
            print(f"    Trace({stack.pop()})", file=out)
        else:
            assert False, (op, payload)
    print("", file=out)
    print("", file=out)
