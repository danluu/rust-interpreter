//! Guest frames with initialized backing and a separate active prefix.
//!
//! Generated Calls will use these descriptors instead of growing the host
//! stack. Preparing spare descriptors must not increase guest call depth. No
//! allocation or safe borrow of this storage may overlap native execution.
use std::ops::{Deref, DerefMut};

/// Host-only state. This layout is not part of the bytecode file format, and
/// none of its addresses or fields are addressable through guest memory.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Frame {
    pub function: usize,
    pub pc: usize,
    pub base: usize,
    pub register_base: usize,
    /// Address, or caller register index when return_value is true.
    pub return_address: usize,
    pub tls_callback: bool,
    pub return_value: bool,
}

// Keep native host-layout offsets beside the checked VM backing.
pub(crate) mod layout {
    use super::Frame;

    pub const FUNCTION: usize = std::mem::offset_of!(Frame, function);
    pub const PC: usize = std::mem::offset_of!(Frame, pc);
    pub const BASE: usize = std::mem::offset_of!(Frame, base);
    pub const REGISTER_BASE: usize = std::mem::offset_of!(Frame, register_base);
    pub const RETURN_ADDRESS: usize = std::mem::offset_of!(Frame, return_address);
    pub const TLS_CALLBACK: usize = std::mem::offset_of!(Frame, tls_callback);
    pub const RETURN_VALUE: usize = std::mem::offset_of!(Frame, return_value);
    pub const SIZE: usize = std::mem::size_of::<Frame>();
    pub const ALIGN: usize = std::mem::align_of::<Frame>();

    #[cfg(all(target_arch = "aarch64", target_os = "macos"))]
    const _: () = {
        assert!(FUNCTION == 0 && PC == 8 && BASE == 16);
        assert!(REGISTER_BASE == 24 && RETURN_ADDRESS == 32 && TLS_CALLBACK == 40);
        assert!(RETURN_VALUE == 41 && SIZE == 48 && ALIGN == 8);
    };
}

pub(crate) struct Frames {
    initialized: Vec<Frame>,
    // All initialized elements are valid Frames, including inactive slots.
    // Only this module may change active, always <= initialized.len().
    active: usize,
}

impl From<Frame> for Frames {
    fn from(entry: Frame) -> Self {
        Self {
            initialized: vec![entry],
            active: 1,
        }
    }
}

impl Deref for Frames {
    type Target = [Frame];

    #[inline(always)]
    fn deref(&self) -> &[Frame] {
        // SAFETY: every mutator preserves the private active-prefix bound.
        // Native access is exclusive and synchronous, as documented below.
        unsafe { self.initialized.get_unchecked(..self.active) }
    }
}

impl DerefMut for Frames {
    #[inline(always)]
    fn deref_mut(&mut self) -> &mut [Frame] {
        // SAFETY: same bound as Deref; the borrow exclusively owns the storage.
        unsafe { self.initialized.get_unchecked_mut(..self.active) }
    }
}

impl Frames {
    pub fn push(&mut self, frame: Frame) {
        if self.active == self.initialized.len() {
            self.initialized.push(frame);
        } else {
            self.initialized[self.active] = frame;
        }
        self.active += 1;
    }

    pub fn pop(&mut self) -> Option<Frame> {
        let last = self.active.checked_sub(1)?;
        self.active = last;
        Some(self.initialized[last])
    }
}

impl Frames {
    /// Prepare initialized descriptors outside generated execution. The caller
    /// bounds speculative storage and treats allocation failure as a decline.
    /// This changes neither the active prefix nor the guest call-depth budget.
    pub fn prepare(&mut self, end: usize) -> Result<(), std::collections::TryReserveError> {
        if end > self.initialized.len() {
            self.initialized.try_reserve(end - self.initialized.len())?;
            self.initialized.resize(end, Frame::default());
        }
        Ok(())
    }

    pub fn initialized_len(&self) -> usize {
        self.initialized.len()
    }

    /// Inspect a prepared descriptor without publishing its active prefix.
    /// Native execution must have returned before taking this safe borrow.
    pub fn prepared_frame(&self, index: usize) -> Option<&Frame> {
        self.initialized.get(index)
    }

    /// Access to initialized backing, including inactive descriptors.
    ///
    /// Dereferencing the result requires exclusive ownership for a synchronous
    /// native entry: no borrowed frame/slice may overlap writes, and no storage
    /// mutation or allocation may occur until it returns. Writes must remain
    /// inside initialized_len(), preserve valid Rust field values (in particular
    /// a bool is only 0 or 1), and must not read the struct's padding. Native
    /// pushes overwrite every field; a normal callee has tls_callback = false.
    pub fn prepared_mut_ptr(&mut self) -> *mut Frame {
        self.initialized.as_mut_ptr()
    }

    /// Publish a native entry's active prefix after checking its cursor.
    /// This verifies the storage bound only. The native boundary must separately
    /// verify guest limits, the current function/PC and memory/register extents.
    pub fn commit_native_len(&mut self, end: usize) -> Result<(), String> {
        if end > self.initialized.len() {
            return Err("native call returned an invalid guest frame count".into());
        }
        self.active = end;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(id: usize, callback: bool) -> Frame {
        Frame {
            function: id,
            pc: id + 3,
            base: 32 + 64 * id,
            register_base: 7 * id,
            return_address: 16 + id,
            return_value: false, tls_callback: callback,
        }
    }

    #[test]
    fn retained_backing_matches_nested_vm_and_tls_stack_lifecycles() {
        let entry = frame(0, false);
        let mut actual = Frames::from(entry);
        let mut reference = vec![entry];
        actual.prepare(32).unwrap();
        let pointer = actual.prepared_mut_ptr();
        // Repeatedly reuse a deep slot for a normal callee and a TLS callback.
        // The active prefix, descriptor fields and empty-stack transition must
        // match a Vec, regardless of which stale descriptors remain behind it.
        for depth in [15, 2, 23, 1, 0, 19, 0] {
            while reference.len() > depth {
                assert_eq!(actual.pop(), reference.pop());
            }
            while reference.len() < depth {
                let next = frame(reference.len(), depth % 2 == 1);
                actual.push(next);
                reference.push(next);
            }
            if let Some(top) = reference.last_mut() {
                top.pc += 100;
                actual.last_mut().unwrap().pc += 100;
            }
            assert_eq!(&*actual, reference);
            assert_eq!(actual.prepared_mut_ptr(), pointer);
        }
        assert_eq!(actual.pop(), None);
        actual.push(entry);
        assert_eq!(&*actual, &[entry]);
    }

    #[test]
    fn native_descendant_exit_and_vm_resume_share_the_actual_top_frame() {
        let root = frame(1, true);
        let child = frame(2, false);
        let grandchild = frame(3, false);
        let mut frames = Frames::from(root);
        frames.prepare(4).unwrap();
        assert_eq!(&*frames, &[root]); // spare frames are not guest calls
        let pointer = frames.prepared_mut_ptr();
        // SAFETY: initialized and exclusive backing of four valid Frames;
        // complete typed writes model native push operations without aliases.
        unsafe {
            pointer.add(1).write(child);
            pointer.add(2).write(grandchild);
        }
        assert_eq!(frames.len(), 1);
        frames.commit_native_len(3).unwrap();
        assert_eq!(frames.last().copied(), Some(grandchild));
        frames.last_mut().unwrap().pc += 1; // one interpreted descendant op
        let resumed_pc = grandchild.pc + 1;
        assert_eq!(frames.pop().unwrap().pc, resumed_pc);
        assert_eq!(frames.last().copied(), Some(child));
        frames.commit_native_len(1).unwrap(); // native child Return
        assert_eq!(frames.last().copied(), Some(root));
        assert!(frames.last().unwrap().tls_callback);
        frames.push(frame(4, false)); // must overwrite all stale child fields
        assert_eq!(frames.pop(), Some(frame(4, false)));
        assert_eq!(frames.prepared_mut_ptr(), pointer);
    }

    #[test]
    fn failed_preparation_or_publication_preserves_the_live_stack() {
        let root = frame(9, false);
        let mut frames = Frames::from(root);
        let pointer = frames.prepared_mut_ptr();
        assert!(frames.prepare(usize::MAX).is_err());
        assert_eq!(frames.prepared_mut_ptr(), pointer);
        assert_eq!(frames.initialized_len(), 1);
        assert!(frames.commit_native_len(2).is_err());
        assert!(frames.commit_native_len(usize::MAX).is_err());
        assert_eq!(&*frames, &[root]);
        frames.prepare(8).unwrap();
        assert_eq!(frames.len(), 1);
        assert!(frames.commit_native_len(9).is_err());
        assert_eq!(&*frames, &[root]);
        frames.commit_native_len(0).unwrap();
        assert!(frames.is_empty());
        frames.push(root);
        assert_eq!(frames.last().copied(), Some(root));
    }
}
