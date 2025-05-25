from actions import Action
from enum import IntEnum
from random import Random

class ActionProp(IntEnum):
    x = 0
    y = 1
    xscale = 2
    yscale = 3
    currentframe = 4
    totalframes = 5
    alpha = 6
    visible = 7
    width = 8
    height = 9
    name = 13

def _str(x):
    if isinstance(x, float):
        if x == int(x):
            return str(int(x))
        return str(x)
    return str(x)

def _float(x):
    if x == "":
        return 0
    try:
        return float(x)
    except ValueError:
        return 0

def _int(x):
    return int(_float(x))

ops = {
    Action.Not: (1, lambda a: int(not _int(a))),
    Action.Add: (2, lambda a, b: _float(a) + _float(b)),
    Action.Subtract: (2, lambda a, b: _float(a) - float(b)),
    Action.Multiply: (2, lambda a, b: _float(a) * _float(b)),
    Action.Divide: (2, lambda a, b: _float(a) / _float(b)),
    Action.Equals: (2, lambda a, b: int(_float(a) == _float(b))),
    Action.Less: (2, lambda a, b: int(_float(a) < _float(b))),
    Action.And: (2, lambda a, b: int(_int(a) and _int(b))),
    Action.Or: (2, lambda a, b: int(_int(a) or _int(b))),
    Action.StringEquals: (2, lambda a, b: _int(a == b)),
    Action.StringAdd: (2, lambda a, b: a + b),
    Action.StringLess: (2, lambda a, b: a < b),
    Action.StringExtract: (3, lambda a, b, c: a[int(b)-1:int(b)-1+int(c)]),
    Action.ToInteger: (1, lambda a: _int(a)),
    Action.CharToAscii: (1, lambda a: ord(a)),
    Action.AsciiToChar: (1, lambda a: chr(_int(a))),
    Action.StringLength: (1, lambda a: len(a)),
}

class ActionVM:
    def __init__(self, emu):
        self.emu = emu
        self.vars = {}
        self.rand = Random(0)
    def run(self, index, target=""):
        pc = index
        stack = []
        while True:
            npc = pc + 1
            op, payload = self.emu.r.get_action(pc)
            if op == Action.Push:
                stack.append(payload)
            elif op == Action.SetVariable:
                val = stack.pop()
                var = stack.pop()
                print(f"  {var} = {val}")
                self.vars[var.lower()] = val
            elif op == Action.GetVariable:
                stack.append(self.vars.get(stack.pop().lower(), ""))
            elif op in ops:
                arg_count, func = ops[op]
                args = [stack.pop() for i in range(arg_count)]
                stack.append(_str(func(*reversed(args))))
            elif op == Action.Jump:
                npc = pc+payload+1 if payload >= 0 else pc+payload
            elif op == Action.If:
                cond = int(float(stack.pop()))
                if cond:
                    npc = pc+payload+1 if payload >= 0 else pc+payload
            elif op == Action.Pop:
                stack.pop()
            elif op == Action.Stop:
                self.emu.stop(target)
            elif op == Action.Play:
                self.emu.play(target)
            elif op == Action.StopSounds:
                self.emu.stop_sounds(target)
            elif op == Action.NextFrame:
                self.emu.goto_frame(target, self.emu.get_frame(target) + 1)
            elif op == Action.PreviousFrame:
                self.emu.goto_frame(target, self.emu.get_frame(target) - 1)
            elif op == Action.GotoFrame:
                self.emu.goto_frame(target, int(payload) + 1)
            elif op == Action.SetTarget:
                target = payload
            elif op == Action.GotoFrame2:
                self.emu.goto_frame(target, int(float(stack.pop())))
            elif op == Action.SetTarget2:
                target = stack.pop()
            elif op == Action.SetProperty:
                o3 = stack.pop()
                o2 = stack.pop()
                o1 = stack.pop()
                print(f"   SetProperty({o1}, {ActionProp(int(o2)).name}, {o3})")
                self.emu.set_property(o1, ActionProp(int(o2)), o3)
            elif op == Action.GetProperty:
                o2 = stack.pop()
                o1 = stack.pop()
                result = _str(self.emu.get_property(o1, ActionProp(int(o2))))
                print(f"   GetProperty({o1}, {ActionProp(int(o2)).name}) -> {result}")
                stack.append(result)
            elif op == Action.CloneSprite:
                o3 = stack.pop()
                o2 = stack.pop()
                o1 = stack.pop()
                self.emu.clone_sprite(o1, o2, int(o3))
            elif op == Action.RemoveSprite:
                self.emu.remove_sprite(stack.pop())
            elif op == Action.Call:
                self.emu.call(int(stack.pop()))
            elif op == Action.End:
                break
            elif op == Action.RandomNumber:
                stack.append(_str(self.rand.randrange(int(stack.pop()))))
            elif op == Action.GetTime:
                stack.append(_str(self.emu.get_time()))
            else:
                assert False, (pc, op, payload)
            pc = npc
