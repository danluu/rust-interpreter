use super::*;
use crate::{Function, Op, Slot};

fn program() -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions: vec![Function { name:"mixed".into(),frame_size:32,frame_align:16,registers:3,
            args:vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],result:Slot{offset:16,size:8},code:vec![Op::Return] }],
        data:vec![],statics:vec![],thread_locals:vec![] }
}
fn abi() -> Vec<FunctionAbi> { vec![FunctionAbi{arguments:vec![Some(0),None],result:Some(2)}] }

#[test]
fn legacy_serialization_is_byte_identical_including_partial_flag() {
    for flag in [0,PARTIAL_VALIDATION] {
        let mut p=program();p.version|=flag;
        let original=bincode::serialize(&p).unwrap();
        let artifact=Artifact::decode(&original).unwrap();
        assert!(artifact.scalar_abi.is_empty());assert_eq!(artifact.encode().unwrap(),original);
        assert_eq!(Artifact::legacy(p).unwrap().encode().unwrap(),original);
    }
}

#[test]
fn scalar_roundtrip_has_explicit_version_and_metadata() {
    let artifact=Artifact::scalar(program(),abi()).unwrap();let bytes=artifact.encode().unwrap();
    assert_eq!(&bytes[..4],&SCALAR_VERSION.to_le_bytes());
    let decoded=Artifact::decode(&bytes).unwrap();assert_eq!(decoded.scalar_abi,abi());
    assert_eq!(decoded.encode().unwrap(),bytes);
    assert_eq!(crate::validate(&decoded.program).unwrap_err(),"invalid bytecode header");
}

#[test]
fn incomplete_trailing_and_unknown_artifacts_are_rejected() {
    let a=Artifact::scalar(program(),abi()).unwrap();let bytes=a.encode().unwrap();
    assert!(Artifact::decode(&bytes[..bytes.len()-1]).is_err());
    let mut trailing=bytes.clone();trailing.push(0);assert!(Artifact::decode(&trailing).is_err());
    let mut unknown=bytes.clone();unknown[..4].copy_from_slice(&99u32.to_le_bytes());assert!(Artifact::decode(&unknown).is_err());
    let mut p=program();p.version=SCALAR_VERSION;
    assert!(Artifact::decode(&bincode::serialize(&p).unwrap()).is_err());
    assert!(Artifact::decode(&[5,0,0]).is_err());
}

#[test]
fn metadata_cannot_be_attached_to_legacy_or_partial_scalar_bodies() {
    let mut a=Artifact{program:program(),scalar_abi:abi()};assert!(a.validate().is_err());
    a.program.version=SCALAR_VERSION|PARTIAL_VALIDATION;assert!(a.validate().is_err());
    let mut p=program();p.version|=PARTIAL_VALIDATION;assert!(Artifact::scalar(p,abi()).is_err());
}

#[test]
fn arity_and_register_aliases_are_checked() {
    assert!(Artifact::scalar(program(),vec![]).is_err());
    let mut a=abi();a[0].arguments.pop();assert!(Artifact::scalar(program(),a).is_err());
    let mut a=abi();a[0].arguments[1]=Some(0);assert!(Artifact::scalar(program(),a).is_err());
    let mut a=abi();a[0].arguments[0]=Some(3);assert!(Artifact::scalar(program(),a).is_err());
    let mut a=abi();a[0].result=Some(3);assert!(Artifact::scalar(program(),a).is_err());
    let mut a=abi();a[0].result=Some(0);assert!(Artifact::scalar(program(),a).is_ok());
}

#[test]
fn supported_widths_are_explicit_and_preserve_low_bits() {
    for size in [1,2,4,8,16] {
        let mut p=program();p.functions[0].args[0].size=size;p.functions[0].result.size=size;
        assert!(Artifact::scalar(p,abi()).is_ok());
        let want=if size==16 {u128::MAX} else {(1u128<<(size*8))-1};
        assert_eq!(truncate(u128::MAX,size),want);
    }
    for size in [0,3,5,15] {
        let mut p=program();p.functions[0].args[0].size=size;assert!(Artifact::scalar(p,abi()).is_err());
        let mut p=program();p.functions[0].result.size=size;assert!(Artifact::scalar(p,abi()).is_err());
    }
}

#[test]
fn ordinary_structural_checks_still_cover_scalar_artifacts() {
    let mut p=program();p.functions[0].code=vec![Op::Load{dst:8,address:0,size:8},Op::Return];
    assert!(Artifact::scalar(p,abi()).is_err());
    let mut p=program();p.functions[0].frame_align=3;assert!(Artifact::scalar(p,abi()).is_err());
    let mut p=program();p.entry=1;assert!(Artifact::scalar(p,abi()).is_err());
}

#[test]
fn scalar_metadata_resource_bounds_are_checked() {
    let mut p=program();p.functions=vec![p.functions[0].clone();MAX_FUNCTIONS+1];
    assert!(Artifact::scalar(p,vec![abi()[0].clone();MAX_FUNCTIONS+1]).is_err());
    let mut p=program();p.functions[0].args=vec![Slot{offset:0,size:8};MAX_ARGUMENT_FIELDS+1];
    let a=vec![FunctionAbi{arguments:vec![None;MAX_ARGUMENT_FIELDS+1],result:None}];
    assert!(Artifact::scalar(p,a).is_err());
}
