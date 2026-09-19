"""Pure complete timing-stack classification, with a source-bound route callback.

The callback must prove that its exact Cargo argv is printed before the common
dry-run stream guard from a specific Step::run. It must validate a real top Step
when supplied, and reject unknown routes. Empty stack is not sufficient alone.
Nonproducer timing frames are retained structurally; they do not prove a Cargo
route. No Finished-boundary or cross-stream timestamp inference is performed.
"""
import hashlib
import re

MAX_RAW = 32 * 2**20
MAX_LINES = 100000
MAX_EVENTS = 10000
MAX_STEP = 16384
MAX_DEPTH = 128


def require(value, message):
    if not value: raise ValueError(message)


def configured(configuration, command, allowed_commands):
    require(configuration.get('build', {}).get('print-step-timings') is True,
            'complete real step timings are required')
    require(command in allowed_commands and command[:1] == ['./x'] and command[-1:] == ['-vv'],
            'unproved bootstrap command/configuration override')


def step_name(text):
    require(0 < len(text) <= MAX_STEP and all(32 <= ord(c) < 127 for c in text),
            'bounded printable timing Step required')
    match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_][A-Za-z_0-9]*)+)(?: (\{.*\})|\((.*)\))?', text)
    require(match is not None, 'unrecognized timing Step representation')
    # Validate the entire nested Debug representation without normalizing it.
    brackets, quoted, escape = [], False, False
    pairs = {'}': '{', ']': '[', ')': '('}
    for char in text:
        if quoted:
            if escape: escape = False
            elif char == '\\': escape = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '{[(': brackets.append(char)
        elif char in '}])':
            require(brackets and brackets.pop() == pairs[char], 'malformed timing Step delimiters')
    require(not brackets and not quoted and not escape, 'unfinished timing Step representation')
    return match[1]


def classify(raw, entries, approve_route):
    """Keep every provided printed context, marking source-proved real vs dry.

    Caller separately derives the *complete* Cargo catalog from the retained
    stream. Each entry must contain command.line/line_sha256 and parsed argv/env.
    All timing records in the stream are parsed, including records after the
    last relevant command and setup steps before the dry self-check.
    """
    require(isinstance(raw, bytes) and len(raw) <= MAX_RAW, 'timing stdout exceeds bound')
    wanted = {}
    for entry in entries:
        line = entry['command']['line']
        require(type(line) is int and line > 0 and line not in wanted, 'duplicate/invalid printed-command coordinate')
        wanted[line] = entry
    stack, events, contexts = [], [], {}
    offset = 0
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        require(number <= MAX_LINES, 'timing stdout line bound exceeded')
        text = line.decode('utf-8', errors='strict').rstrip('\r\n')
        start = re.fullmatch(r'\[TIMING:start\] (.+)', text)
        end = re.fullmatch(r'\[TIMING:end\] (.+) -- ([0-9]+\.[0-9]{3})', text)
        if '[TIMING' in text:
            require(start or end, 'unknown or malformed timing event')
        if start or end:
            step = start[1] if start else end[1]
            name = step_name(step)
            if start:
                require(len(stack) < MAX_DEPTH, 'timing stack depth exceeded')
                stack.append(step)
            else:
                require(stack and stack[-1] == step, 'out-of-order/mismatched timing end')
            events.append(dict(line=number, offset=offset, size=len(line), line_sha256=hashlib.sha256(line).hexdigest(),
                               event='start' if start else 'end', step=step, step_name=name, depth=len(stack)))
            require(len(events) <= MAX_EVENTS, 'timing event bound exceeded')
            if end: stack.pop()
        if number in wanted:
            entry = wanted[number]
            require(hashlib.sha256(line).hexdigest() == entry['command']['line_sha256']
                    and text.startswith('running: ') and not (start or end), 'printed command raw coordinate differs')
            route = approve_route(entry['parsed'], stack[-1] if stack else None)
            require(isinstance(route, str) and route, 'source-bound emitting route required')
            contexts[number] = dict(execution='real' if stack else 'self-check-print', timing_stack=list(stack), source_route=route)
        offset += len(line)
    require(not stack, 'unclosed timing stack')
    require(set(contexts) == set(wanted) and events, 'missing printed contexts or complete timing events')
    return dict(stdout_sha256=hashlib.sha256(raw).hexdigest(), events=events,
                commands=[dict(entry, **contexts[entry['command']['line']]) for entry in entries])
