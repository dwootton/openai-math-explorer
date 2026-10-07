import Lean
import Lean.Util.FoldConsts
import Lean.DeclarationRange
import Lean.Util.CollectAxioms
open Lean

structure Request where
  moduleName : String
  targets : Array String
  localModules : Array String := #["OAI"]
  deriving FromJson

structure SourceRange where
  startLine : Nat
  startColumn : Nat
  endLine : Nat
  endColumn : Nat
  deriving ToJson

structure DeclRecord where
  name : String
  moduleName : String
  kind : String
  typeDependencies : Array String
  proofDependencies : Array String
  dependencies : Array String
  sourceRange : Option SourceRange
  unsafeCode : Bool
  canonicalText : Option String
  deriving ToJson

structure Extraction where
  moduleName : String
  targets : Array String
  declarations : Array DeclRecord
  externalDependencies : Array (String × String)
  missingDeclarations : Array String
  containsSorry : Bool
  axioms : Array String
  deriving ToJson

def moduleOf (env : Environment) (name : Name) : String :=
  match env.getModuleIdxFor? name with
  | some idx => env.header.moduleNames[idx]!.toString
  | none => env.mainModule.toString

def sortedNames (names : Array Name) : Array String :=
  (names.map Name.toString).qsort (· < ·)

def sourceRange (n : Name) : CoreM (Option SourceRange) := do
  let r ← findDeclarationRanges? n
  return r.map fun r => {
    startLine := r.range.pos.line, startColumn := r.range.pos.column,
    endLine := r.range.endPos.line, endColumn := r.range.endPos.column }

def collect (req : Request) : CoreM Extraction := do
  let env ← getEnv
  let mut pending := req.targets.map String.toName
  let mut seen : NameSet := {}
  let mut declarations := #[]
  let mut externalDependencies := #[]
  let mut missingDeclarations := #[]
  let mut containsSorry := false
  while !pending.isEmpty do
    let name := pending.back!
    pending := pending.pop
    if seen.contains name then continue
    seen := seen.insert name
    if name == ``sorryAx then containsSorry := true
    let some info := env.find? name | missingDeclarations := missingDeclarations.push name.toString; continue
    let origin := moduleOf env name
    if !req.localModules.any (fun p => origin == p || origin.startsWith (p ++ ".")) then
      externalDependencies := externalDependencies.push (name.toString, origin)
      continue
    let deps := info.getUsedConstantsAsSet.toArray
    let typeDeps := info.type.getUsedConstants
    let proofDeps := (info.value? (allowOpaque := true)).map Expr.getUsedConstants |>.getD #[]
    let range ← sourceRange name
    let canonicalText ← if range.isSome then pure none else
      (do
        let ty ← Meta.ppExpr info.type
        let value ← match info.value? (allowOpaque := true) with
          | some v => pure ((← Meta.ppExpr v).pretty)
          | none => pure "<primitive declaration>"
        pure (some (name.toString ++ " : " ++ ty.pretty ++ " := " ++ value))
      ).run'
    declarations := declarations.push {
      name := name.toString, moduleName := origin,
      kind := toString (repr (ConstantKind.ofConstantInfo info)),
      typeDependencies := sortedNames typeDeps,
      proofDependencies := sortedNames proofDeps,
      dependencies := sortedNames deps,
      sourceRange := range,
      canonicalText := canonicalText,
      unsafeCode := info.isUnsafe }
    pending := pending ++ deps
  let mut axioms : NameSet := {}
  for target in req.targets do
    if env.contains target.toName then
      for ax in (← collectAxioms target.toName) do axioms := axioms.insert ax
  containsSorry := containsSorry || axioms.contains ``sorryAx
  return {
    moduleName := req.moduleName
    targets := req.targets
    declarations := declarations.qsort (fun a b => a.name < b.name),
    externalDependencies := externalDependencies.qsort (fun a b => a.1 < b.1),
    missingDeclarations := missingDeclarations.qsort (· < ·), containsSorry := containsSorry, axioms := sortedNames axioms.toArray}

unsafe def main (args : List String) : IO UInt32 := do
  let [input, output] := args | throw <| IO.userError "usage: Extract request.json output.json"
  let raw ← IO.FS.readFile input
  let req : Request ← IO.ofExcept (Json.parse raw >>= fromJson?)
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let env ← importModules #[{module := req.moduleName.toName}] {} (loadExts := true) (level := .private)
  let result ← (collect req).toIO' {fileName := "<dependency-extractor>", fileMap := FileMap.ofString "", options := ({} : Options).setBool `pp.proofs true |>.setBool `pp.fullNames true |>.setBool `pp.deepTerms true |>.set `pp.maxSteps (10000000 : Nat)} {env}
  IO.FS.writeFile output ((toJson result).compress ++ "\n")
  return if result.missingDeclarations.isEmpty && !result.containsSorry then 0 else 2
