//! Diagnostic-only elapsed phases. No admission or emitted-word decisions.
use super::{CompiledFunction,EmitError,CodegenLimit};
use serde::Serialize;

#[derive(Clone,Copy,Serialize)]
pub(super) struct Site {
    pub kind:&'static str,pub pc:usize,pub emitted_words:usize,pub next_words:usize,
}
#[derive(Serialize)]
struct Decline {
    function:usize,operations:usize,word_budget:usize,scalar_ns:u128,ordinary_ns:u128,
    publication_ns:u128,outcome:&'static str,site:Option<Site>,
}
#[derive(Default,Serialize)]
pub(super) struct Observation {
    preparations:usize,scalar_ns:u128,ordinary_ns:u128,publication_ns:u128,
    declined:usize,declines_truncated:usize,declines:Vec<Decline>,
}
pub(super) fn outcome(staged:&Result<Option<CompiledFunction<'_>>,EmitError>)->&'static str {
    match staged {
        Ok(Some(_))=>"staged",Ok(None)=>"no-staging",
        Err(EmitError::Limit(CodegenLimit::ConditionalBranch))=>"conditional-branch-limit",
        Err(EmitError::Limit(CodegenLimit::Jump))=>"jump-limit",
        Err(EmitError::Limit(CodegenLimit::Assertions))=>"assertion-limit",
        Err(EmitError::Limit(CodegenLimit::OperationMap))=>"operation-map-limit",
        Err(EmitError::InvalidRelocation(_))=>"invalid-relocation",
    }
}
impl Observation {
    #[allow(clippy::too_many_arguments)]
    pub(super) fn record(&mut self,function:usize,operations:usize,word_budget:usize,
        scalar_ns:u128,ordinary_ns:u128,publication_ns:u128,outcome:&'static str,site:Option<Site>) {
        self.preparations+=1;self.scalar_ns+=scalar_ns;self.ordinary_ns+=ordinary_ns;self.publication_ns+=publication_ns;
        if outcome!="staged" {
            self.declined+=1;
            if self.declines.len()<64 {
                self.declines.push(Decline{function,operations,word_budget,scalar_ns,ordinary_ns,publication_ns,outcome,site});
            } else {self.declines_truncated+=1;}
        }
    }
}
