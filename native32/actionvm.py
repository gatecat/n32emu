from actions import Action
from enum import IntEnum

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


ops = {
    Action.Not: (1, lambda a: int(a) ^ 1),
    Action.Add: (2, lambda a, b: float(a) + float(b)),
    Action.Subtract: (2, lambda a, b: float(a) - float(b)),
    Action.Multiply: (2, lambda a, b: float(a) * float(b)),
    Action.Divide: (2, lambda a, b: float(a) / float(b)),
    Action.Equals: (2, lambda a, b: int(float(a) == float(b))),
    Action.Less: (2, lambda a, b: int(float(a) < float(b))),
    Action.And: (2, lambda a, b: int(a) & int(b)),
    Action.Or: (2, lambda a, b: int(a) | int(b)),
    Action.StringEquals: (2, lambda a, b: a == b),
    Action.StringAdd: (2, lambda a, b: a + b),
    Action.StringLess: (2, lambda a, b: a < b),
    Action.StringExtract: (3, lambda a, b, c: a[b:int(b)+int(c)]),
    Action.ToInteger: (1, lambda a: int(float(a))),
    Action.CharToAscii: (1, lambda a: ord(a)),
    Action.AsciiToChar: (1, lambda a: chr(int(float(a)))),
    Action.StringLength: (1, lambda a: len(a)),
}

class ActionVM:
    def __init__(self, emu):
        self.emu = emu
        self.vars = {}
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
                self.vars[var] = val
            elif op == Action.GetVariable:
                stack.append(self.vars[stack.pop()])
            elif op in ops:
                arg_count, func = ops[op]
                args = [stack.pop() for i in range(arg_count)]
                stack.append(str(func(*reversed(args))))
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
                self.emu.goto_frame(target, int(payload))
            elif op == Action.SetTarget:
                target = payload
            elif op == Action.GotoFrame2:
                self.emu.goto_frame(target, int(stack.pop()))
            elif op == Action.SetTarget2:
                target = stack.pop()
            elif op == Action.SetProperty:
                o3 = stack.pop()
                o2 = stack.pop()
                o1 = stack.pop()
                self.emu.set_property(o1, ActionProp(int(o2)), o3)
            elif op == Action.GetProperty:
                o2 = stack.pop()
                o1 = stack.pop()
                stack.append(str(emu.get_property(o1, ActionProp(int(o2)))))
            elif op == Action.RemoveSprite:
                self.emu.remove_sprite(stack.pop())
            elif op == Action.Call:
                self.emu.call(int(stack.pop()))
            elif op == Action.End:
                break
            else:
                assert False, (pc, op, payload)
            pc = npc
