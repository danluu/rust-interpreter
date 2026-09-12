//! Explicit caller value operands. No guest address bits encode ABI metadata.
use crate::{Function, Program, Reg};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub enum CallArgument {
    Address(Reg),
    Value(Reg),
}
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub enum CallDestination {
    Address(Reg),
    Value(Reg),
}
impl CallArgument {
    pub(crate) fn register(self) -> Reg {
        match self {
            Self::Address(r) | Self::Value(r) => r,
        }
    }
}
impl CallDestination {
    pub(crate) fn register(self) -> Reg {
        match self {
            Self::Address(r) | Self::Value(r) => r,
        }
    }
}

#[derive(Clone, Copy)]
pub(crate) enum Arguments<'a> {
    Addresses(&'a [Reg]),
    Mixed(&'a [CallArgument]),
}
impl<'a> Arguments<'a> {
    pub fn at(self, index: usize) -> CallArgument {
        match self {
            Self::Addresses(r) => CallArgument::Address(r[index]),
            Self::Mixed(r) => r[index],
        }
    }
    pub fn addresses(self) -> &'a [Reg] {
        match self {
            Self::Addresses(r) => r,
            Self::Mixed(_) => unreachable!("value operands in legacy execution"),
        }
    }
}

pub(crate) fn scalar_width(size: usize) -> bool {
    matches!(size, 1 | 2 | 4 | 8 | 16)
}

pub(crate) fn validate_call(
    program: &Program,
    caller: &Function,
    callee: usize,
    args: &[CallArgument],
    destination: CallDestination,
) -> Result<(), String> {
    if program.version != crate::scalar_abi::SCALAR_VERSION {
        return Err("value calls require scalar artifact version 6".into());
    }
    let callee = program.functions.get(callee).ok_or("invalid callee")?;
    if args.len() != callee.args.len() || args.len() > 65_536 {
        return Err("invalid value call arity".into());
    }
    if destination.register() as usize >= caller.registers {
        return Err("invalid value call destination register".into());
    }
    if matches!(destination, CallDestination::Value(_)) && !scalar_width(callee.result.size) {
        return Err("invalid value call result width".into());
    }
    for (arg, slot) in args.iter().zip(&callee.args) {
        if arg.register() as usize >= caller.registers {
            return Err("invalid value call argument register".into());
        }
        if matches!(arg, CallArgument::Value(_)) && !scalar_width(slot.size) {
            return Err("invalid value call argument width".into());
        }
    }
    Ok(())
}
