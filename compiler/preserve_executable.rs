//! Opt-in preservation of identical local executables during Cargo publication.
//! Keep ordinary copy semantics for symlinks, non-executables, differing
//! permissions/ownership, extended attributes, mismatches, and I/O errors.
use std::fs::{self, File, Metadata};
use std::io::{self, Read};
use std::os::fd::AsRawFd;
use std::os::macos::fs::MetadataExt as MacMetadataExt;
use std::os::unix::fs::MetadataExt;
use std::path::Path;

fn stamp(m: &Metadata) -> (u64, u64, u64, i64, i64, i64, i64, u32, u32, u32, u32) {
    (
        m.dev(),
        m.ino(),
        m.len(),
        m.mtime(),
        m.mtime_nsec(),
        m.ctime(),
        m.ctime_nsec(),
        m.mode(),
        m.uid(),
        m.gid(),
        m.st_flags(),
    )
}

fn no_extended_attributes(file: &File) -> bool {
    // A zero-length query only inspects the attribute names. Any attribute or
    // query failure conservatively retains Cargo's existing copy behavior.
    unsafe { libc::flistxattr(file.as_raw_fd(), std::ptr::null_mut(), 0, 0) == 0 }
}

pub(super) fn identical_executables(src: &Path, dst: &Path) -> io::Result<bool> {
    let sm = fs::symlink_metadata(src)?;
    let dm = fs::symlink_metadata(dst)?;
    if !sm.is_file()
        || !dm.is_file()
        || sm.mode() & 0o111 == 0
        || sm.mode() != dm.mode()
        || sm.uid() != dm.uid()
        || sm.gid() != dm.gid()
        || sm.st_flags() != dm.st_flags()
        || sm.len() != dm.len()
    {
        return Ok(false);
    }
    let mut source = File::open(src)?;
    let mut destination = File::open(dst)?;
    if stamp(&source.metadata()?) != stamp(&sm)
        || stamp(&destination.metadata()?) != stamp(&dm)
        || !no_extended_attributes(&source)
        || !no_extended_attributes(&destination)
    {
        return Ok(false);
    }
    let mut a = vec![0; 256 * 1024];
    let mut b = vec![0; 256 * 1024];
    loop {
        let n = source.read(&mut a)?;
        if n == 0 {
            if destination.read(&mut b)? != 0 {
                return Ok(false);
            }
            break;
        }
        destination.read_exact(&mut b[..n])?;
        if a[..n] != b[..n] {
            return Ok(false);
        }
    }
    // Reject changes during comparison. Cargo's normal target lock still owns
    // publication; this is not a cache for concurrently modified external files.
    Ok(stamp(&fs::symlink_metadata(src)?) == stamp(&sm)
        && stamp(&fs::symlink_metadata(dst)?) == stamp(&dm))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::{PermissionsExt, symlink};

    #[test]
    fn preserve_executable_requires_complete_bytes_and_metadata() {
        let temp = tempfile::tempdir().unwrap();
        let a = temp.path().join("source");
        let b = temp.path().join("destination");
        let data = vec![7; 600_000];
        fs::write(&a, &data).unwrap();
        fs::write(&b, &data).unwrap();
        assert!(!identical_executables(&a, &b).unwrap());
        for p in [&a, &b] {
            fs::set_permissions(p, fs::Permissions::from_mode(0o755)).unwrap();
        }
        let before = stamp(&fs::metadata(&b).unwrap());
        assert!(identical_executables(&a, &b).unwrap());
        assert_eq!(stamp(&fs::metadata(&b).unwrap()), before);
        let mut changed = data.clone();
        changed[550_000] ^= 1;
        fs::write(&b, changed).unwrap();
        assert!(!identical_executables(&a, &b).unwrap());
        fs::write(&b, &data[..100]).unwrap();
        assert!(!identical_executables(&a, &b).unwrap());
        fs::write(&b, &data).unwrap();
        fs::set_permissions(&b, fs::Permissions::from_mode(0o700)).unwrap();
        assert!(!identical_executables(&a, &b).unwrap());
        fs::remove_file(&b).unwrap();
        symlink(&a, &b).unwrap();
        assert!(!identical_executables(&a, &b).unwrap());
        fs::remove_file(&b).unwrap();
        assert!(identical_executables(&a, &b).is_err());
    }
}
