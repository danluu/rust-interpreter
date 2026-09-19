"""Fixed-path reservation and explicit early-exit refund model, not native code."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Region:
    cost: int
    successors: tuple
    guarded: bool = False


def plan(nodes, cap=4096):
    if not 1 <= len(nodes) <= 65536 or type(cap) is not int or cap < 1:
        raise ValueError('invalid shape/cap')
    edges=0
    for pc,node in nodes.items():
        if type(pc) is not int or pc<0 or type(node.cost) is not int or not 1<=node.cost<=min(1024,cap):
            raise ValueError('invalid PC/cost')
        if type(node.guarded) is not bool or not isinstance(node.successors,tuple):
            raise ValueError('invalid fields')
        edges+=len(node.successors)
        if edges>262144 or any(type(t) is not int or t<0 for t in node.successors) or len(set(node.successors))!=len(node.successors):
            raise ValueError('invalid edges')
    credit,fast={},{}
    for pc in sorted(nodes,reverse=True):
        node=nodes[pc];target=node.successors[0] if len(node.successors)==1 else None
        eligible=target is not None and target>pc and target in nodes and not nodes[target].guarded
        if eligible and node.cost+credit[target]<=cap:
            fast[pc]=(target,);credit[pc]=node.cost+credit[target]
        else:fast[pc]=();credit[pc]=node.cost
    incoming={t for targets in fast.values() for t in targets}
    for pc,targets in fast.items():
        for target in targets:
            assert credit[pc]-nodes[pc].cost==credit[target]
    return dict(credit=credit,fast=fast,incoming=incoming,extra_immediate=set())


def oracle(nodes,path,budget,fault=None):
    events=[]
    for visit,pc in enumerate(path):
        for op in range(nodes[pc].cost):
            if budget==0:return events,'budget',0
            budget-=1;events.append((visit,pc,op))
            if fault==(visit,op):return events,'fault',budget
    return events,'end',budget


def simulate(nodes,path,budget,fault=None,external=()):
    p=plan(nodes);cursor=budget;semantic=budget;pending=0;events=[];publications=[];reservations=0;refunds=0
    for visit,pc in enumerate(path):
        if visit and pc not in nodes[path[visit-1]].successors:raise ValueError('non-CFG path')
        if visit in external:
            cursor+=pending;refunds+=bool(pending);pending=0
        assert cursor+pending==semantic
        before=semantic
        fast=pending!=0
        if fast:
            assert pending==p['credit'][pc]
            native=True
        else:
            native=cursor>=p['credit'][pc]
            if native:
                cursor-=p['credit'][pc];pending=p['credit'][pc];reservations+=1
        if native:
            pending-=nodes[pc].cost
            assert pending==p['credit'][pc]-nodes[pc].cost
        for op in range(nodes[pc].cost):
            if not native and cursor==0:
                return dict(outcome=(events,'budget',0),publications=publications,reservations=reservations,refunds=refunds)
            semantic-=1;events.append((visit,pc,op))
            if not native:cursor-=1
            if fault==(visit,op):
                cursor+=pending;refunds+=bool(pending);pending=0
                # Native accounting retains the entire current-region debit,
                # exactly as the original native fault path; tail faults debit
                # only operations actually stepped. Neither charges a suffix.
                expected=before-(nodes[pc].cost if native else op+1)
                assert cursor==expected and 0<=cursor<=semantic
                publications.append(dict(visit=visit,kind='native_fault' if native else 'tail_fault',remaining=cursor,expected=expected))
                return dict(outcome=(events,'fault',semantic),publications=publications,reservations=reservations,refunds=refunds)
        assert cursor+pending==semantic
        # A boundary may expose the complete original state after refunding.
        publications.append(dict(visit=visit,kind='boundary',remaining=cursor+pending,expected=semantic))
        target=path[visit+1] if visit+1<len(path) else None
        if not native or target not in p['fast'][pc]:
            cursor+=pending;refunds+=bool(pending);pending=0
        if pending:
            assert len(nodes[pc].successors)==1 and pending==p['credit'][target]
    assert pending==0 and cursor==semantic
    return dict(outcome=(events,'end',semantic),publications=publications,reservations=reservations,refunds=refunds)
