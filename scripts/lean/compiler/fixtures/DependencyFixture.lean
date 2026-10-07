import Lean
namespace DifferentNamespace
class Evidence where
  proof : True
instance actualInstance : Evidence := ⟨True.intro⟩
theorem helper [Evidence] : True := Evidence.proof
macro "through_macro" : tactic => `(tactic| exact helper)
theorem target : True := by through_macro
theorem unused : True := True.intro
end DifferentNamespace
