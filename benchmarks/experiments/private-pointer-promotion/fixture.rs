#[inline(never)]
pub fn address_choice(base: usize, step: usize, choose: bool) -> usize {
    let candidate = base.wrapping_add(step) as *const u8;
    let fallback = base as *const u8;
    let selected = if choose { candidate } else { fallback };
    (selected as usize).wrapping_sub(base)
}

#[inline(never)]
pub fn boundary_pointer(pointer: *const u8) -> usize { pointer as usize }

#[inline(never)]
fn replace_pointer(slot: &mut *const u64, replacement: *const u64) { *slot = replacement; }

#[inline(never)]
unsafe fn update_choice(a: *mut u64, b: *mut u64, choose: bool) -> u64 {
    let selected = if choose { a } else { b };
    unsafe { *selected = 7; *a + *b }
}

#[inline(never)]
fn fat_pointer_length(values: &[u8]) -> usize {
    let pointer = values as *const [u8];
    unsafe { (&*pointer).len() }
}

#[inline(never)]
fn plus_three(value: u64) -> u64 { value + 3 }

#[inline(never)]
fn function_pointer_call(function: fn(u64) -> u64, value: u64) -> u64 { function(value) }

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pointer_values_across_branches_and_wrapping_arithmetic() {
        for base in [0, 1, 17, usize::MAX - 9] {
            for step in [0, 1, 8, 31] {
                for choose in [false, true] {
                    assert_eq!(address_choice(base, step, choose), if choose { step } else { 0 });
                }
            }
        }
    }
    #[test]
    fn call_arguments_and_exposed_pointer_storage_keep_identity() {
        let (first, second) = (11u64, 29u64);
        let mut pointer = &first as *const u64;
        assert_eq!(boundary_pointer(pointer.cast()), &first as *const u64 as usize);
        replace_pointer(&mut pointer, &second);
        assert_eq!(unsafe { *pointer }, 29);
        assert_eq!(boundary_pointer(pointer.cast()), &second as *const u64 as usize);
    }
    #[test]
    fn pointee_aliases_and_nonaliases_observe_every_write() {
        let (mut first, mut second) = (3u64, 5u64);
        assert_eq!(unsafe { update_choice(&mut first, &mut second, true) }, 12);
        first = 3;
        assert_eq!(unsafe { update_choice(&mut first, &mut second, false) }, 10);
        let same = &mut first as *mut u64;
        assert_eq!(unsafe { update_choice(same, same, true) }, 14);
        first = 1;
        assert_eq!(unsafe { update_choice(same, same, false) }, 14);
        assert_eq!(first, 7);
    }
    #[test]
    fn pointer_dereferences_in_loops_keep_memory_updates() {
        let mut values = [1u64, 3, 5];
        for index in 0..values.len() {
            let pointer = unsafe { values.as_mut_ptr().add(index) };
            unsafe { *pointer += index as u64; }
        }
        assert_eq!(values, [1, 4, 7]);
    }
    #[test]
    fn fat_pointer_metadata_remains_intact() {
        assert_eq!(fat_pointer_length(&[]), 0);
        assert_eq!(fat_pointer_length(&[1, 2, 3, 4]), 4);
    }
    #[test]
    fn function_pointer_calls_remain_valid() {
        assert_eq!(function_pointer_call(plus_three, 17), 20);
    }
}
