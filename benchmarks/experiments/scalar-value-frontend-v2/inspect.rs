use rust_interp_bytecode::{CallArgument, CallDestination, Op, scalar_abi::Artifact};
fn main() {
    let path = std::env::args_os().nth(1).expect("artifact path");
    let bytes = std::fs::read(path).unwrap();
    let artifact = Artifact::decode(&bytes).unwrap();
    assert_eq!(artifact.encode().unwrap(), bytes);
    let functions: Vec<_> = artifact.program.functions.iter().enumerate().map(|(id, f)| {
        let abi = artifact.scalar_abi.get(id);
        let calls: Vec<_> = f.code.iter().enumerate().filter_map(|(pc, op)| {
            if let Op::CallValue { function, args, destination } = op {
                Some(serde_json::json!({"pc":pc,"callee":function,
                    "values":args.iter().filter(|a|matches!(a,CallArgument::Value(_))).count(),
                    "addresses":args.iter().filter(|a|matches!(a,CallArgument::Address(_))).count(),
                    "value_result":matches!(destination,CallDestination::Value(_))}))
            } else {None}
        }).collect();
        serde_json::json!({"id":id,"name":f.name,"frame_bytes":f.frame_size,
            "args":f.args,"result":f.result,"abi":abi,"calls":calls})
    }).collect();
    println!("{}",serde_json::json!({"version":artifact.program.version,"functions":functions}));
}
