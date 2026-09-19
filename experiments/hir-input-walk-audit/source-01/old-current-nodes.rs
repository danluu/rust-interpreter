pub(super) fn current_nodes<'tcx>(tcx: TyCtxt<'tcx>, resolver: &ResolverAstLowering<'tcx>,
    owner: ast::NodeId, span: Span, f: &ast::Fn, probe: &Probe)
    -> Outcome<Vec<(ast::NodeId, bool)>> {
    let mut w = Walk { tcx, resolver, owner, base: span, atoms: Vec::new(),
        nodes: NodeMap::default(), ordered: Vec::new(), trait_entries: 0,
        trait_candidates: 0, external_resolutions: 0, depth: 0 };
    w.tag(POLICY); w.count(f.sig.decl.inputs.len());
    for p in &f.sig.decl.inputs {
        if p.is_placeholder { return Err("placeholder-parameter"); }
        w.node(p.id, false)?; w.span(p.span)?; w.span(p.ty.span)?; w.pattern(&p.pat, false)?;
    }
    w.block(f.body.as_deref().ok_or("no-body")?)?; w.resolved()?;
    let repeated = Input { owner: probe.input.owner, file: probe.input.file,
        role: probe.input.role, owner_source: probe.input.owner_source.clone(), atoms: w.atoms };
    let mut first = MemEncoder::new(); probe.input.encode(&mut first);
    let mut second = MemEncoder::new(); repeated.encode(&mut second);
    if first.finish() != second.finish() { return Err("qualified-walker-disagreement"); }
    Ok(w.ordered)
}
