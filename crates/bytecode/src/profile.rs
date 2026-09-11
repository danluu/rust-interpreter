use crate::Program;
use serde::Serialize;

/// Per-PC counts retain enough information to distinguish emitted operations
/// from interpreter transitions, and to inspect frequently called tiny bodies.
/// This optional diagnostic storage is outside the guest working-memory budget.
#[derive(Debug, Serialize)]
pub struct ExecutionProfile {
    pub functions: Vec<FunctionProfile>,
}

#[derive(Debug, Serialize)]
pub struct FunctionProfile {
    pub name: String,
    pub frame_size: usize,
    pub registers: usize,
    pub operations: Vec<String>,
    pub interpreted: Vec<u64>,
    pub jit_blocks: Vec<u64>,
    /// Exclusive end PC for each compiled block; zero where no block starts.
    pub jit_block_ends: Vec<usize>,
    /// Complete native trees have different block boundaries from VM regions.
    pub jit_tree_blocks: Vec<u64>,
    pub jit_tree_block_ends: Vec<usize>,
}

impl ExecutionProfile {
    pub(crate) fn new(program: &Program) -> Self {
        Self {
            functions: program.functions.iter().map(|f| FunctionProfile {
                name: f.name.clone(),
                frame_size: f.frame_size,
                registers: f.registers,
                operations: f.code.iter().map(|op| format!("{op:?}")).collect(),
                interpreted: vec![0; f.code.len()],
                jit_blocks: vec![0; f.code.len()],
                jit_block_ends: vec![0; f.code.len()],
                jit_tree_blocks: vec![0; f.code.len()],
                jit_tree_block_ends: vec![0; f.code.len()],
            }).collect(),
        }
    }
}
