//! Per-function pending branches with transactional metadata ownership.
use super::*;

pub(super) const MAX_METADATA_BYTES: usize = 16 * 1024 * 1024;
const NONE: usize = usize::MAX;

struct Node {
    pc: usize,
    internal: Option<usize>, // arena-relative word offset
    head: usize,
}

#[derive(Clone, Copy)]
struct Pending {
    at: usize, // arena-relative byte offset
    expected: u32,
    next: usize,
}

pub(super) struct Links {
    function: usize,
    nodes: Vec<Node>,
    edges: Vec<Pending>,
    arena: Option<usize>,
}

// The exclusive borrow prevents metadata changes between preparation and code
// commit. Dropping an uncommitted Prepared leaves the original owner unchanged.
pub(super) struct Prepared<'a> {
    owner: &'a mut Links,
    source: usize,
    word_base: usize,
    internal: usize,
    words: Vec<u32>,
    patches: Vec<CodePatch>,
    outgoing: Vec<(usize, Pending)>,
    replacement_edges: Option<Vec<Pending>>,
    additional_charge: usize,
}

fn jump(at: usize, target: usize) -> Result<u32, String> {
    branch_displacement(at, target, 26, CodegenLimit::Jump)
        .map(|delta| 0x14000000 | delta).map_err(|_| "demand branch displacement exceeds range".into())
}

impl Links {
    pub fn new(function: usize, pcs: &[usize], available: usize) -> Result<Self, String> {
        if available > MAX_METADATA_BYTES || pcs.windows(2).any(|p| p[0] >= p[1]) {
            return Err("invalid demand metadata admission".into());
        }
        let requested = pcs.len().checked_mul(std::mem::size_of::<Node>())
            .and_then(|bytes| bytes.checked_add(std::mem::size_of::<Self>()))
            .ok_or("demand metadata size overflow")?;
        if requested > available { return Err("demand metadata budget exhausted".into()); }
        let mut nodes = vec![];
        nodes.try_reserve_exact(pcs.len()).map_err(|_| "demand metadata allocation failed")?;
        for &pc in pcs { nodes.push(Node { pc, internal: None, head: NONE }); }
        let result = Self { function, nodes, edges: vec![], arena: None };
        if result.charge() > available { return Err("demand metadata capacity exceeds budget".into()); }
        Ok(result)
    }

    pub fn charge(&self) -> usize {
        std::mem::size_of::<Self>() + self.nodes.capacity() * std::mem::size_of::<Node>()
            + self.edges.capacity() * std::mem::size_of::<Pending>()
    }

    fn index(&self, pc: usize) -> Option<usize> { self.nodes.binary_search_by_key(&pc, |n| n.pc).ok() }

    pub fn internal(&self, pc: usize) -> Option<usize> { self.nodes.get(self.index(pc)?)?.internal }

    // available is the caller's remaining aggregate metadata charge, not a
    // new per-function allowance. Existing payload remains owned until commit.
    pub fn prepare(&mut self, function: usize, pc: usize, word_base: usize, internal: usize,
        mut words: Vec<u32>, declarations: &[(usize, usize, usize)], available: usize,
    ) -> Result<Prepared<'_>, String> {
        if function != self.function || available > MAX_METADATA_BYTES {
            return Err("demand fragment owner or budget mismatch".into());
        }
        let available = available.min(MAX_METADATA_BYTES - self.charge());
        let source = self.index(pc).ok_or("demand fragment is not a planned leader")?;
        if self.nodes[source].internal.is_some() || internal >= words.len()
            || word_base.checked_add(words.len()).is_none_or(|end| end > MAX_CODE_BYTES / 4) {
            return Err("invalid or already published demand fragment".into());
        }
        let target = word_base + internal;
        let mut patches = vec![];
        let mut edge = self.nodes[source].head;
        while edge != NONE {
            if patches.len() >= self.edges.len() { return Err("cyclic pending demand edges".into()); }
            let incoming = self.edges.get(edge).ok_or("invalid pending demand edge")?;
            if incoming.at % 4 != 0 || incoming.at / 4 >= word_base {
                return Err("pending demand edge outside old arena prefix".into());
            }
            patches.try_reserve(1).map_err(|_| "demand patch allocation failed")?;
            patches.push(CodePatch { offset: incoming.at, expected: incoming.expected, word: jump(incoming.at / 4, target)? });
            edge = incoming.next;
        }
        patches.sort_unstable_by_key(|p| p.offset);
        if patches.windows(2).any(|p| p[0].offset == p[1].offset) {
            return Err("duplicate pending demand branch site".into());
        }
        let mut outgoing = vec![];
        outgoing.try_reserve_exact(declarations.len()).map_err(|_| "demand edge staging allocation failed")?;
        let mut sites = vec![];
        sites.try_reserve_exact(declarations.len()).map_err(|_| "demand site staging allocation failed")?;
        for &(at, successor, fallback) in declarations {
            if at >= words.len() || fallback >= words.len() {
                return Err("demand branch or fallback outside fragment".into());
            }
            let local = if successor == pc { internal } else { fallback };
            if words[at] != jump(at, local)? { return Err("demand fragment branch does not match declared fallback".into()); }
            sites.push(at);
            let destination = self.index(successor);
            let ready = if successor == pc { Some(target) }
                else { destination.and_then(|i| self.nodes[i].internal) };
            if let Some(ready) = ready {
                if successor != pc && ready >= word_base { return Err("demand target outside old arena prefix".into()); }
                words[at] = jump(word_base + at, ready)?;
            } else if let Some(destination) = destination {
                outgoing.push((destination, Pending { at: (word_base + at) * 4, expected: words[at], next: NONE }));
            }
        }
        sites.sort_unstable();
        if sites.windows(2).any(|p| p[0] == p[1]) { return Err("duplicate declared demand branch site".into()); }
        let required = self.edges.len().checked_add(outgoing.len()).ok_or("demand edge count overflow")?;
        let mut replacement_edges = None;
        let mut additional_charge = 0;
        if required > self.edges.capacity() {
            let size = std::mem::size_of::<Pending>();
            let max_capacity = self.edges.capacity().checked_add(available / size).ok_or("demand edge capacity overflow")?;
            if required > max_capacity { return Err("pending demand edge budget exhausted".into()); }
            let requested = required.max(self.edges.capacity().saturating_mul(2).min(max_capacity));
            let mut replacement = vec![];
            replacement.try_reserve_exact(requested).map_err(|_| "pending demand edge allocation failed")?;
            if replacement.capacity() > max_capacity { return Err("pending demand edge capacity exceeds budget".into()); }
            additional_charge = (replacement.capacity() - self.edges.capacity()) * size;
            replacement.extend_from_slice(&self.edges);
            replacement_edges = Some(replacement);
        }
        Ok(Prepared { owner: self, source, word_base, internal, words, patches, outgoing,
            replacement_edges, additional_charge })
    }
}

impl Prepared<'_> {
    pub fn additional_charge(&self) -> usize { self.additional_charge }

    // The caller reserves its assertion/table/publication payload before this
    // call. After code succeeds, all changes here are infallible owned moves.
    pub fn publish(self, code: &mut platform::Code) -> Result<usize, String> {
        let (arena, bytes) = code.published();
        if bytes.len() / 4 != self.word_base || self.owner.arena.is_some_and(|old| old != arena) {
            return Err("demand transaction arena changed".into());
        }
        let offset = code.append_and_patch(&self.words, &self.patches)?;
        if let Some(replacement) = self.replacement_edges { self.owner.edges = replacement; }
        for (destination, mut edge) in self.outgoing {
            edge.next = self.owner.nodes[destination].head;
            self.owner.nodes[destination].head = self.owner.edges.len();
            self.owner.edges.push(edge); // sufficient capacity reserved before code commit
        }
        self.owner.nodes[self.source].head = NONE;
        self.owner.nodes[self.source].internal = Some(self.word_base + self.internal);
        self.owner.arena = Some(arena);
        Ok(offset)
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod tests;
