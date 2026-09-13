use std::fs::{self, File, OpenOptions};
use std::hash::{Hash, Hasher};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::sync::atomic::{AtomicU64, Ordering};

use rustc_ast as ast;
use rustc_data_structures::fingerprint::Fingerprint;
use rustc_data_structures::stable_hash::StableHasher;
use rustc_hir as hir;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_serialize::Encodable;
use rustc_serialize::opaque::mem_encoder::MemEncoder;
use serde::{Deserialize, Serialize};

use crate::LoweringContext;

mod capture;
mod input;
mod materialize;
mod validate;
mod wire;

const FORMAT: &str = "hir-owner-reuse-v1";
const MAX_RECORD: u64 = 2 * 1024 * 1024;
static NEXT_TEMP: AtomicU64 = AtomicU64::new(0);

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record {
    format: String,
    key: Vec<u8>,
    payload: wire::OwnerTree,
    checksum: String,
}

pub(super) struct Candidate {
    probe: input::Probe,
    key: Vec<u8>,
    path: PathBuf,
    checked: Option<validate::CheckedTree>,
}

fn digest(bytes: &[u8]) -> String {
    let mut h = StableHasher::new();
    h.write(bytes);
    let fingerprint: Fingerprint = h.finish();
    hex(fingerprint)
}

fn hex(fingerprint: Fingerprint) -> String {
    let (first, second) = fingerprint.split();
    format!("{:016x}{:016x}", first.as_u64(), second.as_u64())
}

fn codec_identity() -> &'static str {
    static ID: OnceLock<String> = OnceLock::new();
    ID.get_or_init(|| digest(concat!(include_str!("mod.rs"), include_str!("input.rs"),
        include_str!("wire.rs"), include_str!("validate.rs"), include_str!("capture.rs"),
        include_str!("materialize.rs")).as_bytes()))
}

fn checksum(key: &[u8], tree: &wire::OwnerTree) -> Option<String> {
    let tree = serde_json::to_vec(tree).ok()?;
    if tree.len() as u64 > MAX_RECORD { return None; }
    let mut h = StableHasher::new();
    key.hash(&mut h);
    tree.hash(&mut h);
    let fingerprint: Fingerprint = h.finish();
    Some(hex(fingerprint))
}

fn read(path: &Path, key: &[u8], source: &str) -> Option<validate::CheckedTree> {
    if !fs::symlink_metadata(path).ok()?.is_file() { return None; }
    let file = File::open(path).ok()?;
    if !file.metadata().ok()?.is_file() || file.metadata().ok()?.len() > MAX_RECORD { return None; }
    let mut bytes = Vec::new();
    file.take(MAX_RECORD + 1).read_to_end(&mut bytes).ok()?;
    if bytes.len() as u64 > MAX_RECORD { return None; }
    // serde_json retains its default recursion limit; no panic-catching decoder is used.
    let record: Record = serde_json::from_slice(&bytes).ok()?;
    if record.format != FORMAT || record.key != key
        || record.checksum != checksum(key, &record.payload)? { return None; }
    validate::check(record.payload, source)
}

fn write(path: &Path, key: &[u8], tree: wire::OwnerTree) -> Option<()> {
    let checksum = checksum(key, &tree)?;
    let bytes = serde_json::to_vec(&Record { format: FORMAT.to_owned(), key: key.to_vec(), payload: tree, checksum }).ok()?;
    if bytes.len() as u64 > MAX_RECORD { return None; }
    let tmp = path.with_extension(format!("part-{}-{}", std::process::id(), NEXT_TEMP.fetch_add(1, Ordering::Relaxed)));
    let mut file = OpenOptions::new().write(true).create_new(true).open(&tmp).ok()?;
    let written = file.write_all(&bytes);
    drop(file);
    let result = written.and_then(|()| fs::rename(&tmp, path));
    if result.is_err() { let _ = fs::remove_file(&tmp); }
    result.ok()
}

fn report(tcx: TyCtxt<'_>, item: &ast::Item, kind: &str) {
    if tcx.sess.opts.unstable_opts.incremental_info {
        let name = match &item.kind { ast::ItemKind::Fn(f) => f.ident.name.as_str(), _ => "" };
        eprintln!("[hir-owner-reuse] {kind} {} {name}", item.kind.descr());
    }
}

pub(super) fn prepare<'tcx>(
    tcx: TyCtxt<'tcx>, resolver: &ResolverAstLowering<'tcx>, item: &ast::Item,
) -> Option<Candidate> {
    if !tcx.sess.opts.unstable_opts.reuse_hir_owners { return None; }
    let Some(session) = tcx.incr_comp_session else { return None; };
    if std::env::var_os("RUSTC_FORCE_RUSTC_VERSION").is_some() { return None; }
    let Some(probe) = input::probe(tcx, resolver, item) else {
        report(tcx, item, "rejected-input");
        return None;
    };
    let mut encoder = MemEncoder::new();
    FORMAT.encode(&mut encoder);
    codec_identity().encode(&mut encoder);
    tcx.sess.cfg_version.encode(&mut encoder);
    tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);
    probe.input.encode(&mut encoder);
    let key = encoder.finish();
    if key.len() as u64 > MAX_RECORD / 4 { return None; }
    // Flat sidecars follow rustc's own locked COW session copy/finalization/GC protocol.
    let path = session.session_directory.join(format!("{FORMAT}-{}.bin", hex(probe.input.owner.0)));
    let checked = read(&path, &key, &probe.input.source);
    report(tcx, item, if checked.is_some() { "hit" } else { "miss" });
    Some(Candidate { probe, key, path, checked })
}

pub(super) fn restore<'hir>(candidate: &Candidate, lctx: &mut LoweringContext<'_, 'hir>) -> Option<hir::OwnerNode<'hir>> {
    // Parsing, bounded validation and ID-reference checking all preceded creation of this lctx.
    candidate.checked.as_ref().map(|tree| materialize::materialize(lctx, &candidate.probe, tree))
}

pub(super) fn save(candidate: &Candidate, lctx: &LoweringContext<'_, '_>, node: hir::OwnerNode<'_>) {
    if candidate.checked.is_some() || lctx.tcx.dcx().has_errors().is_some() { return; }
    let state = &lctx.curr_owner;
    // create_def always inserts into node_id_to_def_id; this map is never cleared by an owner.
    if !lctx.node_id_to_def_id.is_empty() || lctx.next_node_id != lctx.resolver.next_node_id
        || !lctx.partial_res_overrides.is_empty() || !state.attrs.is_empty() || !state.children.is_empty()
        || !state.trait_map.is_empty() || !state.delayed_lints.is_empty() || state.define_opaque.is_some()
        || !state.impl_trait_defs.is_empty() || !state.impl_trait_bounds.is_empty() { return; }
    let Some(tree) = capture::capture(&candidate.probe, state, node) else { return; };
    let Some(checked) = validate::check(tree, &candidate.probe.input.source) else { return; };
    // Write only after a normal result was completely captured and validated. Failure is a miss.
    let tree = checked.into_inner();
    let _ = write(&candidate.path, &candidate.key, tree);
}

#[cfg(test)]
mod tests;
